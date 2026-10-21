#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

/* 2.8" ILI9341 SPI panel (240x320), pins per app_config.h.
 * Bench bring-up 2026-10-21: CS=10, DC=9, RST=14, MOSI=11, SCLK=12, BL=47. */
esp_err_t lcd_ili9341_init(void);

void lcd_fill(uint16_t color);
void lcd_fill_rect(int x, int y, int w, int h, uint16_t color);
void lcd_test_pattern(void);
void lcd_backlight(bool on);
