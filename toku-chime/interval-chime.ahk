#Requires AutoHotkey v2.0
#SingleInstance Force

; Toku Chime — Windows background interval chime
; F8: Start / Pause
; F9: Cycle 30 / 45 / 60 seconds
; F10: Test chime
; Esc: Hide window (script keeps running in the tray)

global intervals := [30000, 45000, 60000]
global intervalIndex := 1
global running := false
global chimes := 0

global app := Gui(, "Toku Chime")
app.SetFont("s10", "Segoe UI")
app.MarginX := 18
app.MarginY := 16
app.AddText("w300", "Toku Chime — interval cue")
global statusText := app.AddText("w300 y+8", "30 sec · stopped")
global countText := app.AddText("w300 y+4", "Chimes: 0")

startButton := app.AddButton("w92 y+14", "Start / Pause")
cycleButton := app.AddButton("x+8 w92", "30 / 45 / 60")
testButton := app.AddButton("x+8 w92", "Test")

startButton.OnEvent("Click", Toggle)
cycleButton.OnEvent("Click", CycleInterval)
testButton.OnEvent("Click", TestChime)
app.OnEvent("Close", (*) => app.Hide())

app.AddText("xm w300 y+14 cGray", "F8 Start/Pause · F9 Interval · F10 Test")
app.Show("AutoSize")

F8::Toggle()
F9::CycleInterval()
F10::TestChime()
Esc::app.Hide()

Toggle(*) {
    global running, intervals, intervalIndex
    running := !running
    if running {
        SetTimer(Chime, intervals[intervalIndex])
    } else {
        SetTimer(Chime, 0)
    }
    UpdateStatus()
}

CycleInterval(*) {
    global intervalIndex, intervals, running
    intervalIndex := Mod(intervalIndex, intervals.Length) + 1
    if running {
        SetTimer(Chime, 0)
        SetTimer(Chime, intervals[intervalIndex])
    }
    UpdateStatus()
}

TestChime(*) {
    Ring()
}

Chime() {
    global chimes
    chimes += 1
    Ring()
    UpdateStatus()
}

Ring() {
    ; A short two-tone cue. Uses only Windows/AutoHotkey built-ins.
    SoundBeep(880, 85)
    Sleep(30)
    SoundBeep(1320, 170)
}

UpdateStatus() {
    global running, intervals, intervalIndex, chimes, statusText, countText
    seconds := Round(intervals[intervalIndex] / 1000)
    statusText.Text := seconds " sec · " (running ? "running" : "stopped")
    countText.Text := "Chimes: " chimes
}
