/* UART provisioning REPL: write Wi-Fi / controller / meeting / token into NVS. */
#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Start a UART REPL with the `provision` command. Does not return until reboot. */
esp_err_t provision_start(void);

#ifdef __cplusplus
}
#endif
