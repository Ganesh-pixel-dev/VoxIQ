# Makes two spoken demo answers with the Windows text-to-speech voice (no real person's voice).
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = 0
$first = "Um, so basically, last year in my final year at college, I was, uh, working with my team. Actually, my job was to build a photo checker called Drishti. So basically I, um, wrote the analysis code in Python, you know, and it was kind of slow. Literally nobody on the team had tried it before. Matlab, I just kept testing it, na? In the end it worked okay."
$second = "Last year, in my final year at college, our team needed a way to check whether photos had been edited. My job was to build the checker, which I called Drishti. I wrote the error level analysis code in Python and Django, and tested it on forty photos. As a result, it caught 38 of the 40 edited ones, and my guide approved it for the department demo."
foreach ($pair in @(@("attempt1", $first), @("attempt2", $second))) {
  $s.SetOutputToWaveFile((Join-Path $PSScriptRoot ($pair[0] + ".wav")))
  $s.Speak($pair[1])
  $s.SetOutputToNull()
}
