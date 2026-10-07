# Toku Chime

A tiny local-first interval chime by Tokumaru Labs.

Designed for study sessions where you want a gentle cue every 30, 45, or 60 seconds without a full pomodoro workflow getting in the way.

## Features

- 30 / 45 / 60 second presets
- Custom interval from 5 to 3600 seconds
- Synthesized bell sound; no audio file or network request required
- Bell / soft / click sound modes
- Volume control
- Countdown, elapsed time, and chime count
- Keyboard shortcuts
- Optional Screen Wake Lock when supported
- Settings stored only in `localStorage`
- No accounts, analytics, tracking, cookies, or ads
- No dependencies

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| Space | Start / pause |
| 1 | 30 seconds |
| 2 | 45 seconds |
| 3 | 60 seconds |
| R | Reset |
| T | Test chime |

## Windows / background use

Browsers may throttle timers in background tabs. If you need a cue that keeps running reliably while another app is in front, use the included `interval-chime.ahk` script with AutoHotkey v2.

## Run locally

Open `index.html` in a modern browser, or serve this directory with any static web server.

## License

MIT. See `LICENSE`.
