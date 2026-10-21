/* ILI9341 2.8" SPI LCD, 240x320, RGB565.
 *
 * Minimal polling-SPI driver for bench bring-up plus a color-bar self test.
 * No esp_lcd component dependency: commands go straight over spi_master so the
 * first light-up does not depend on managed-component downloads.
 */
#include "lcd_ili9341.h"

#include <string.h>

#include "app_config.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "lcd";

#define LCD_W 240
#define LCD_H 320

static spi_device_handle_t s_spi;
static bool s_ready;
static uint8_t s_line[LCD_W * 2];

typedef struct {
    uint8_t cmd;
    uint8_t len;
    uint8_t data[15];
} lcd_init_cmd_t;

/* Standard ILI9341 power/gamma init (Adafruit-derived, trimmed). */
static const lcd_init_cmd_t s_init[] = {
    {0xEF, 3, {0x03, 0x80, 0x02}},
    {0xCF, 3, {0x00, 0xC1, 0x30}},
    {0xED, 4, {0x64, 0x03, 0x12, 0x81}},
    {0xE8, 3, {0x85, 0x00, 0x78}},
    {0xCB, 5, {0x39, 0x2C, 0x00, 0x34, 0x02}},
    {0xF7, 1, {0x20}},
    {0xEA, 2, {0x00, 0x00}},
    {0xC0, 1, {0x23}},
    {0xC1, 1, {0x10}},
    {0xC5, 2, {0x3E, 0x28}},
    {0xC7, 1, {0x86}},
    {0x36, 1, {0x48}}, /* MADCTL: MX|BGR */
    {0x37, 1, {0x00}},
    {0x3A, 1, {0x55}}, /* 16 bit/pixel */
    {0xB1, 2, {0x00, 0x18}},
    {0xB6, 3, {0x08, 0x82, 0x27}},
    {0xF2, 1, {0x00}},
    {0x26, 1, {0x01}},
    {0xE0, 15, {0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E, 0xF1, 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00}},
    {0xE1, 15, {0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31, 0xC1, 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F}},
};

static void lcd_cmd(uint8_t cmd) {
    gpio_set_level(LCD_DC_GPIO, 0);
    spi_transaction_t t = {0};
    t.length = 8;
    t.tx_buffer = &cmd;
    spi_device_polling_transmit(s_spi, &t);
}

static void lcd_data(const uint8_t *buf, size_t len) {
    if (len == 0) {
        return;
    }
    gpio_set_level(LCD_DC_GPIO, 1);
    spi_transaction_t t = {0};
    t.length = len * 8;
    t.tx_buffer = buf;
    spi_device_polling_transmit(s_spi, &t);
}

static void lcd_cmd_data(uint8_t cmd, const uint8_t *data, size_t len) {
    lcd_cmd(cmd);
    lcd_data(data, len);
}

static void lcd_set_window(int x, int y, int w, int h) {
    uint8_t col[4] = {(uint8_t)(x >> 8), (uint8_t)x, (uint8_t)((x + w - 1) >> 8), (uint8_t)(x + w - 1)};
    uint8_t row[4] = {(uint8_t)(y >> 8), (uint8_t)y, (uint8_t)((y + h - 1) >> 8), (uint8_t)(y + h - 1)};
    lcd_cmd_data(0x2A, col, sizeof(col));
    lcd_cmd_data(0x2B, row, sizeof(row));
    lcd_cmd(0x2C);
}

esp_err_t lcd_ili9341_init(void) {
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << LCD_DC_GPIO) | (1ULL << LCD_RST_GPIO) | (1ULL << LCD_BL_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t rc = gpio_config(&io);
    if (rc != ESP_OK) {
        return rc;
    }
    gpio_set_level(LCD_BL_GPIO, 0);

    spi_bus_config_t bus = {
        .mosi_io_num = LCD_MOSI_GPIO,
        .miso_io_num = -1,
        .sclk_io_num = LCD_SCLK_GPIO,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = LCD_W * 2 * 2,
    };
    rc = spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO);
    if (rc != ESP_OK && rc != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "spi_bus_initialize failed: %s", esp_err_to_name(rc));
        return rc;
    }

    spi_device_interface_config_t dev = {
        .clock_speed_hz = 20 * 1000 * 1000,
        .mode = 0,
        .spics_io_num = LCD_CS_GPIO,
        .queue_size = 7,
    };
    rc = spi_bus_add_device(SPI2_HOST, &dev, &s_spi);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "spi_bus_add_device failed: %s", esp_err_to_name(rc));
        return rc;
    }

    /* Hardware reset: low 20 ms, high 120 ms. */
    gpio_set_level(LCD_RST_GPIO, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(LCD_RST_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(120));

    lcd_cmd(0x01); /* SWRESET */
    vTaskDelay(pdMS_TO_TICKS(150));

    for (size_t i = 0; i < sizeof(s_init) / sizeof(s_init[0]); i++) {
        lcd_cmd_data(s_init[i].cmd, s_init[i].data, s_init[i].len);
    }

    lcd_cmd(0x11); /* SLPOUT */
    vTaskDelay(pdMS_TO_TICKS(150));
    lcd_cmd(0x29); /* DISPON */
    vTaskDelay(pdMS_TO_TICKS(50));

    s_ready = true;
    lcd_backlight(true);
    ESP_LOGI(TAG, "ILI9341 up: %dx%d, cs=%d dc=%d rst=%d sclk=%d mosi=%d bl=%d", LCD_W, LCD_H,
             LCD_CS_GPIO, LCD_DC_GPIO, LCD_RST_GPIO, LCD_SCLK_GPIO, LCD_MOSI_GPIO, LCD_BL_GPIO);
    return ESP_OK;
}

void lcd_backlight(bool on) {
    gpio_set_level(LCD_BL_GPIO, on ? 1 : 0);
}

void lcd_fill_rect(int x, int y, int w, int h, uint16_t color) {
    if (!s_ready || w <= 0 || h <= 0) {
        return;
    }
    lcd_set_window(x, y, w, h);
    for (int i = 0; i < w; i++) {
        s_line[i * 2] = (uint8_t)(color >> 8);
        s_line[i * 2 + 1] = (uint8_t)(color & 0xFF);
    }
    for (int j = 0; j < h; j++) {
        lcd_data(s_line, (size_t)w * 2);
    }
}

void lcd_fill(uint16_t color) {
    lcd_fill_rect(0, 0, LCD_W, LCD_H, color);
}

void lcd_test_pattern(void) {
    static const uint16_t colors[] = {0xF800, 0x07E0, 0x001F, 0xFFE0, 0x07FF, 0xF81F, 0xFFFF};
    const int n = (int)(sizeof(colors) / sizeof(colors[0]));
    const int bar_w = LCD_W / n;
    if (!s_ready) {
        return;
    }
    for (int i = 0; i < n; i++) {
        lcd_fill_rect(i * bar_w, 0, bar_w, LCD_H, colors[i]);
    }
}
