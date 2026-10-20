# Flash the built ESP32-S3 firmware. No build is performed here.
#   powershell -ExecutionPolicy Bypass -File scripts/flash_firmware.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/flash_firmware.ps1 -Port COM6
# Requires a data-capable Type-C cable and the board's USB-UART port.
param([string]$Port = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$idf = Join-Path $root ".local/esp-idf"
$python = Join-Path $env:USERPROFILE ".espressif/python_env/idf5.4_py3.12_env/Scripts/python.exe"
$firmware = Join-Path $root "firmware/esp32/build/effmeet2_robot.bin"

if (-not (Test-Path $firmware)) {
    throw "Firmware not built. Run scripts/build_firmware.ps1 first."
}
if (-not (Test-Path $python)) {
    throw "ESP-IDF Python env not found. Run the ESP-IDF install steps first."
}

if (-not $Port) {
    $detected = & $python -c @"
from serial.tools import list_ports
for p in list_ports.comports():
    hwid = (p.hwid or '').upper()
    if any(v in hwid for v in ('VID_303A', 'VID_1A86', 'VID_10C4', 'VID_0403')):
        print(p.device)
"@
    $ports = @($detected | Where-Object { $_ -match '^COM\d+$' })
    if ($ports.Count -eq 0) {
        throw "No ESP32/CH340/CP210x serial port found. Check: data-capable Type-C cable, direct USB port (not hub), the board's USB-UART port, and the CH340/CP210x driver. Bluetooth COM ports are not the board."
    }
    if ($ports.Count -gt 1) {
        throw "Multiple candidate ports found: $($ports -join ', '). Re-run with -Port COMx."
    }
    $Port = $ports[0]
}

$env:MSYSTEM = $null
$env:IDF_PATH = $idf
$env:IDF_PYTHON_ENV_PATH = Split-Path (Split-Path $python -Parent) -Parent
$env:PATH = (Split-Path $python -Parent) + ";" + $env:PATH
. (Join-Path $idf "export.ps1")
Write-Host "Flashing $Port ..."
idf.py -C (Join-Path $root "firmware/esp32") -p $Port flash
Write-Host "Flash complete. Open serial logs with:"
Write-Host "  idf.py -C firmware/esp32 -p $Port monitor"
