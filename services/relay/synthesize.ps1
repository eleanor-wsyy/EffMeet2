$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $synth.SetOutputToWaveFile($env:EFFMEET_TTS_OUTPUT, $format)
    $synth.Speak($env:EFFMEET_TTS_TEXT)
    $synth.SetOutputToNull()
} finally {
    $synth.Dispose()
}
