/* app_main — boot sequence for the EffMeet2 robot scaffold.
 *
 * Order: NVS -> Wi-Fi station -> load paired identity -> init peripherals ->
 * start the device session task. Every peripheral init currently returns
 * ESP_ERR_NOT_SUPPORTED (NOT-VERIFIED stubs), so this boots to "connected but
 * idle" without driving hardware.
 *
 * NOT-VERIFIED: never compiled or flashed in the scaffold environment.
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
#include "servo_yaw.h"
#include "status_led.h"

static const char *TAG = "app_main";

static void wifi_init_sta(void) {
    /* TODO(bring-up): real Wi-Fi provisioning (softAP/blufi/NVS) instead of
     * compile-time SSID/pass. Blocks until connected; retries on disconnect. */
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    wifi_config_t wc = {0};
    strncpy((char *)wc.sta.ssid, CONFIG_EFFMEET_WIFI_SSID, sizeof(wc.sta.ssid) - 1);
    strncpy((char *)wc.sta.password, CONFIG_EFFMEET_WIFI_PASS, sizeof(wc.sta.password) - 1);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wc);
    esp_wifi_start();
    esp_wifi_connect();
    ESP_LOGW(TAG, "Wi-Fi STA start requested (SSID from Kconfig; provisioning TBD)");
}

/* Session task: waits for a paired identity, then idles until a command-delivery
 * channel feeds RobotCommands to device_session_on_command(). The delivery
 * transport is an OPEN INTEGRATION POINT (see device_session.h). */
static void session_task(void *arg) {
    (void)arg;
    device_identity_t ident;
    for (;;) {
        if (device_session_load_identity(&ident) == ESP_OK) {
            break;
        }
        ESP_LOGW(TAG, "not paired yet; retrying in 5s (operator must pair device)");
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
    device_session_t *s = device_session_create(&ident);
    if (!s) {
        ESP_LOGE(TAG, "could not create device session");
        vTaskDelete(NULL);
        return;
    }
    char hello[256];
    if (device_session_hello_json(s, hello, sizeof(hello)) == ESP_OK) {
        ESP_LOGI(TAG, "DeviceHello: %s", hello);
    }
    ESP_LOGW(TAG, "session ready; command-delivery channel not wired (NOT-VERIFIED)");
    /* TODO(bring-up): subscribe to the controller events WS, filter robot
     * command.queued for this device_id, then call device_session_on_command(). */
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

    wifi_init_sta();

    /* Peripheral init: all stubs return ESP_ERR_NOT_SUPPORTED for now. */
    status_led_init();
    status_led_set_pattern(LED_PATTERN_IDLE);
    servo_yaw_init();
    audio_playback_init();
    audio_capture_init();
    aec_afe_init();
    camera_capture_init();

    xTaskCreatePinnedToCore(session_task, "session", 8192, NULL, 5, NULL, 1);
    ESP_LOGW(TAG, "EffMeet2 robot scaffold booted (NOT-VERIFIED; no hardware driven)");
}
