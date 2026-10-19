# Build the ESP32-S3 firmware with the local ESP-IDF checkout.
# No device or flash is touched. Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File scripts/build_firmware.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$idf = Join-Path $root ".local/esp-idf"
if (-not (Test-Path (Join-Path $idf "export.ps1"))) {
    throw "ESP-IDF not found at $idf. Clone it there first (see firmware/esp32/docs/FIRMWARE_STATUS.md)."
}
# Git Bash exports MSYSTEM, which makes ESP-IDF's install/export scripts refuse to run.
$env:MSYSTEM = $null
$env:IDF_PATH = $idf

# The system Python may be newer than the ESP-IDF venv (e.g. 3.14 vs 3.12).
# Pin export.ps1 to the venv that install-python-env actually created.
$espPython = Join-Path $env:USERPROFILE ".espressif\python_env\idf5.4_py3.12_env\Scripts"
if (-not (Test-Path (Join-Path $espPython "python.exe"))) {
    throw "ESP-IDF Python env not found at $espPython. Run install-python-env --features=+core first."
}
$env:IDF_PYTHON_ENV_PATH = Split-Path $espPython -Parent
$env:PATH = "$espPython;$env:PATH"

. (Join-Path $idf "export.ps1")
idf.py -C (Join-Path $root "firmware/esp32") set-target esp32s3 build
