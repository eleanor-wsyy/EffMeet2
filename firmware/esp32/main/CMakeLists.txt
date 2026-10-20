# main component. Hardware-facing modules are compiled but their peripheral
# init paths return ESP_ERR_NOT_SUPPORTED until bench bring-up (NOT-VERIFIED).
# efma_codec.c is pure C (no ESP headers) so it is also host-testable; see
# ../test/test_efma_host.c.
idf_component_register(
    SRCS
        "main.c"
        "efma_codec.c"
        "ws_transport.c"
        "device_session.c"
        "audio_capture.c"
        "audio_playback.c"
        "aec_afe.c"
        "servo_yaw.c"
        "status_led.c"
        "camera_capture.c"
        "provision.c"
    INCLUDE_DIRS "."
    REQUIRES
        console
        nvs_flash
        esp_wifi
        esp_netif
        esp_event
        esp_websocket_client
        esp_http_client
        esp_timer
        driver
        json
)
