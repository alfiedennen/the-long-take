# Known limits

The piece is locked at v22; the boundaries below are deliberate and unlikely to change in this repo. PRs that work *within* them are welcome.

## Hard requirements

- **LD2450 only.** Other presence sensors (PIR, FP300, mmWave-without-position) cannot drive this rendering — it needs per-target X/Y position over time.
- **MariaDB recorder backend.** The default SQLite recorder hits performance cliffs at the LD2450 scan rate across multiple rooms.
- **WebGL2.** No fallback for older browsers. Modern Chromium/Firefox/Safari support is universal; ancient Android tablets may not.
- **Modern browser audio policy.** Audio is opt-in by user gesture. The first click anywhere enables sound.

## Render limits

- **Single-room per render.** Each iframe / browser tab renders one room. Multi-room composition is a Lovelace dashboard concern, not a renderer concern.
- **Up to 3 concurrent bodies.** LD2450's hard upper limit. If a fourth person enters the room, they're invisible to the radar (and so to the renderer).
- **2D radar.** The LD2450 reports X and Y but not Z (height). The "Y axis = TIME" decision works because the radar's Y can become Z (forward-back in room) and the time axis takes vertical.
- **~30k decimated points / room / 24h window.** This is the renderer's comfortable budget. Past ~200k the frame rate drops; past ~500k WebGL allocations start to fail on lower-end GPUs.

## Pre-compute limits

- **24-hour window default.** Tunable via the script's first argument (e.g. `python exposure_precompute.py 168` for a week), but the `TARGET_POINTS = 30_000` constant is calibrated for 24h. Longer windows need re-tuning.
- **Read-only against the recorder.** Never writes back. If your HA install corrupts its recorder for unrelated reasons, this script won't help recover it.
- **SSH-cat to HA OS.** HA OS lacks `sftp-server`, so we pipe through `ssh ... cat`. Slow for many small files (fine for our handful) but the first failure mode if HA OS's SSH config drifts.

## Audio limits

- **Pentatonic A minor only.** Hardcoded scale + root. Tuneable via `PENTATONIC_HZ` array in the renderer if you want a different mood.
- **14 notes/sec ceiling.** Audio throttle to prevent the synth blowing out during high-activity periods. Tuneable.
- **No microphone input.** This is playback of stored data, not live. The scrubber moves through history.

## What's NOT in this repo

- The Home Assistant dashboard composition (the Lovelace dashboard that surfaces multiple rooms side-by-side).
- The original `monthly_snapshot.py` companion that compresses raw radar history into long-term storage. (Lives in the haroldathome.com private repo; not coupled to this rendering.)
- The other rooms' sample datasets (only `office.json` is bundled — to demonstrate, not to publish a complete profile).
- Live-data variants. The renderer fetches a static JSON; "live" is via the 5-minute precompute refresh, not via WebSocket.

## Browser compatibility tested

| Browser | Status |
|---|---|
| Chromium 120+ (desktop) | ✓ tested |
| Firefox 120+ (desktop) | ✓ tested |
| Safari 17+ (desktop / iOS) | ✓ tested |
| Chromium on Android | ✓ tested |
| Older Android (Fire HD 10 with Fully Kiosk) | ⚠ functional but slow; mute audio for stability |
| IE / Edge Legacy | ✗ no WebGL2, won't run |
