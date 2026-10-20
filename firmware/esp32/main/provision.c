/* UART provisioning REPL for the ESP32-S3 scaffold. The REPL is the offline
 * path for Wi-Fi/controller/pairing when the device has no network yet. */
#include "provision.h"

#include <stdio.h>
#include <string.h>

#include "device_session.h"
#include "esp_console.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"

static const char *TAG = "provision";

static int cmd_provision(int argc, char **argv) {
    if (argc != 6) {
        printf("usage: provision <ssid> <pass> <controller_url> <meeting_id> <media_token>\n");
        return ESP_ERR_INVALID_ARG;
    }
    nvs_handle_t h;
    esp_err_t rc = nvs_open(EFFMEET_NVS_NAMESPACE, NVS_READWRITE, &h);
    if (rc != ESP_OK) {
        return rc;
    }
    nvs_set_str(h, "wifi_ssid", argv[1]);
    nvs_set_str(h, "wifi_pass", argv[2]);
    nvs_set_str(h, "controller_url", argv[3]);
    nvs_set_str(h, "meeting_id", argv[4]);
    nvs_set_str(h, "media_token", argv[5]);
    rc = nvs_commit(h);
    nvs_close(h);
    if (rc != ESP_OK) {
        return rc;
    }
    printf("provisioned; rebooting\n");
    vTaskDelay(pdMS_TO_TICKS(200));
    esp_restart();
    return ESP_OK;
}

static int cmd_provision_status(int argc, char **argv) {
    (void)argc; (void)argv;
    nvs_handle_t h;
    if (nvs_open(EFFMEET_NVS_NAMESPACE, NVS_READONLY, &h) != ESP_OK) {
        printf("NVS namespace not found; nothing provisioned.\n");
        return ESP_OK;
    }
    char ssid[64] = {0}, controller[128] = {0}, meeting[37] = {0};
    size_t n;
    n = sizeof(ssid); nvs_get_str(h, "wifi_ssid", ssid, &n);
    n = sizeof(controller); nvs_get_str(h, "controller_url", controller, &n);
    n = sizeof(meeting); nvs_get_str(h, "meeting_id", meeting, &n);
    printf("wifi_ssid=%s\ncontroller_url=%s\nmeeting_id=%s\n", ssid, controller, meeting);
    nvs_close(h);
    return ESP_OK;
}

esp_err_t provision_start(void) {
    esp_console_repl_t *repl = NULL;
    esp_console_repl_config_t repl_config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_config.prompt = "effmeet> ";
    repl_config.task_stack_size = 4096;
    esp_console_dev_uart_config_t hw_config = ESP_CONSOLE_DEV_UART_CONFIG_DEFAULT();
    esp_err_t rc = esp_console_new_repl_uart(&hw_config, &repl_config, &repl);
    if (rc != ESP_OK) {
        return rc;
    }
    esp_console_register_help_command();
    static const esp_console_cmd_t provision_cmd = {
        .command = "provision",
        .help = "provision <ssid> <pass> <controller_url> <meeting_id> <media_token>",
        .func = &cmd_provision,
    };
    static const esp_console_cmd_t status_cmd = {
        .command = "provision_status",
        .help = "show provisioned fields (no secrets)",
        .func = &cmd_provision_status,
    };
    esp_console_cmd_register(&provision_cmd);
    esp_console_cmd_register(&status_cmd);
    rc = esp_console_start_repl(repl);
    if (rc != ESP_OK) {
        return rc;
    }
    ESP_LOGW(TAG, "provision REPL started; use 'provision' to write Wi-Fi/controller/token");
    return ESP_OK;
}
