# Adapt to your setup

The defaults work for a four-room house with LD2450 radars on a 24-hour window. This doc covers how to fit the renderer to your own situation.

## Mapping LD2450 entity names

In `precompute/rooms.py` (which you copied from `rooms.example.py`), each room is a tuple:

```py
(room_id, entity_prefix, friendly_label, room_dims_mm)
```

- `room_id` — short, lowercase, no spaces. Appears in the URL (`?r=<room_id>`) and as the JSON filename.
- `entity_prefix` — your radar's HA entity name, **without** the `_target_<n>_<x|y|speed>` suffix. So if HA shows `sensor.upstairs_office_radar_target_1_x`, your prefix is `sensor.upstairs_office_radar`.
- `friendly_label` — appears in the renderer's status strip.
- `room_dims_mm` — `[width, depth, height]` in millimetres. Approximate is fine; this is used to scale the cube view, not for any geometric correctness.

Example for one room:

```py
ROOMS = [
    ("office", "sensor.upstairs_office_radar", "Office", [3380, 2830, 2400]),
]
```

You can configure as many rooms as you have radars.

## Adjusting room dimensions

The `room_dims_mm` tuple is `[width, depth, height]` — i.e. the radar's X span, Y span, and the room's vertical Z. Get the W and D approximately right (within ~500mm) and the cube renders nicely. Z is mostly cosmetic — the renderer doesn't currently use vertical position from the radar (LD2450 is 2D).

If your radar is corner-mounted at one end of the room, the X axis runs left-right across the room and Y runs forward away from the radar.

## Sub-day windows — rendering one hour, an evening, a week

The window is the first command-line argument to `exposure_precompute.py`:

```sh
# Last hour
python exposure_precompute.py 1

# Last twelve hours (an evening)
python exposure_precompute.py 12

# Last week (warning — see decimation note below)
python exposure_precompute.py 168
```

For windows much shorter than 24 hours, you may want to lower `TARGET_POINTS` (top of the script) so the membrane doesn't get over-decimated.

For windows much longer than 24 hours (a week, a month), the existing decimation will keep ~30k points and you'll lose detail. Bump `TARGET_POINTS` to e.g. `100_000` for week-views, but be aware the JSON gets correspondingly larger and the renderer's memory + frame budget eventually breaks somewhere around 200k points.

## Single-room vs multi-room

The renderer renders one room per page-load. To compare rooms side-by-side, the cleanest approach is a small Lovelace dashboard with multiple iframes:

```yaml
type: vertical-stack
cards:
  - type: iframe
    url: /local/the-long-take/?r=office
    aspect_ratio: 16:9
  - type: iframe
    url: /local/the-long-take/?r=living_room
    aspect_ratio: 16:9
```

Each iframe runs its own copy of the renderer with its own audio context. Audio is muted by default; visibility-aware mute (Page Visibility API + IntersectionObserver) means non-visible iframes don't waste CPU/audio.

## Changing the visual lock

The shader and audio defaults are tuned through 22 iterations to a particular look — see [haroldathome.com/the-long-take](https://haroldathome.com/the-long-take) for the journey. If you want to deviate:

| What | Where in `renderer/ghost-cloud.js` |
|---|---|
| Membrane base colour | The PBR `baseColor` uniform in the membrane material |
| Membrane opacity | `material.opacity` and the alpha mix in the fragment shader |
| FBM shimmer amplitude | `NORMAL_FBM_AMPLITUDE` near the top of the shader source |
| Bloom intensity | The `UnrealBloomPass(...)` constructor args |
| Audio throttle (notes/sec ceiling) | `AUDIO_THROTTLE_HZ` in the audio synth section |
| Pentatonic root + scale degrees | `PENTATONIC_HZ` array |

Each of these is one or two-line tweaks; iterate freely.

## Multi-radar rooms

If you have two LD2450s pointed at the same large room (e.g. a double-aspect living room), the precompute can fuse them by treating each as a separate target stream. Adjust the `MAX_TARGETS` constant and add a second prefix tuple for the same `room_id`. Some manual fan-in code is required — happy to PR if useful.

## Other presence sensors

The Long Take needs **per-target X/Y position over time**. PIR sensors and binary mmWave (e.g. Aqara FP300) only report on/off — no position — and won't work for this rendering. The pattern *could* be adapted to render binary presence as a different visual (a glowing tube that pulses rather than bulges), but that's a different piece. PRs welcome.
