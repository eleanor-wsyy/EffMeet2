/* app_main — boot sequence for the EffMeet2 robot scaffold.
 *
 * Order: NVS -> Wi-Fi station -> load paired identity -> init peripherals ->
 * start the device session task. status LED, yaw servo, I2S mic and I2S amp are
 * real drivers; AFE/AEC and the camera are still stubs (NOT-VERIFIED).
 */
#include <string.h>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"

#include "aec_afe.h"
#include "app_config.h"
#include "audio_capture.h"
#include "audio_playback.h"
#include "camera_capture.h"
#include "device_session.h"
#include "lcd_ili9341.h"
#include "provision.h"
#include "servo_yaw.h"
#include "status_led.h"

static const char *TAG = "app_main";

static void wifi_init_sta(const device_identity_t *ident) {
    if (!ident->wifi_ssid[0]) {
        ESP_LOGW(TAG, "no Wi-Fi SSID provisioned; skipping station start");
        return;
    }
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    wifi_config_t wc = {0};
    strncpy((char *)wc.sta.ssid, ident->wifi_ssid, sizeof(wc.sta.ssid) - 1);
    strncpy((char *)wc.sta.password, ident->wifi_pass, sizeof(wc.sta.password) - 1);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wc);
    esp_wifi_start();
    esp_wifi_connect();
    ESP_LOGW(TAG, "Wi-Fi STA start requested (SSID=%s)", ident->wifi_ssid);

    /* Wait for DHCP before opening sockets; the first WS attempt otherwise
     * races the link and fails with "host unreachable". */
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    for (int i = 0; i < 40; i++) {
        esp_netif_ip_info_t ip;
        if (netif && esp_netif_get_ip_info(netif, &ip) == ESP_OK && ip.ip.addr != 0) {
            ESP_LOGW(TAG, "Wi-Fi up, ip=" IPSTR, IP2STR(&ip.ip));
            return;
        }
        vTaskDelay(pdMS_TO_TICKS(250));
    }
    ESP_LOGE(TAG, "Wi-Fi connect timeout (10 s); continuing anyway");
}

static void session_task(void *arg) {
    device_identity_t *ident = (device_identity_t *)arg;
    device_session_t *s = device_session_create(ident);
    if (!s) {
        ESP_LOGE(TAG, "could not create device session");
        vTaskDelete(NULL);
        return;
    }
    char hello[256];
    if (device_session_hello_json(s, hello, sizeof(hello)) == ESP_OK) {
        ESP_LOGI(TAG, "DeviceHello: %s", hello);
    }
    device_session_subscribe_commands(s);
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void app_main(void) {
    esp_err_t rc = nvs_flash_init();
    if (rc == ESP_ERR_NVS_NO_FREE_PAGES || rc == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    static device_identity_t ident;
    device_session_load_identity(&ident);

    /* Peripheral init: AFE and camera remain stubs; the rest are real drivers. */
    status_led_init();
    status_led_set_pattern(LED_PATTERN_IDLE);
    servo_yaw_init();
    audio_playback_init();
    audio_capture_init();
    aec_afe_init();
    camera_capture_init();
    if (lcd_ili9341_init() == ESP_OK) {
        lcd_test_pattern();
    }

    /* The REPL runs in both modes so re-provisioning never needs an NVS erase. */
    provision_start();

    if (!ident.paired) {
        ESP_LOGW(TAG, "device not paired; use 'provision' to write Wi-Fi/controller/token");
        return;
    }

    wifi_init_sta(&ident);
    xTaskCreatePinnedToCore(session_task, "session", 8192, &ident, 5, NULL, 1);
    ESP_LOGW(TAG, "EffMeet2 robot booted (paired; AFE/camera still stubs)");
}
