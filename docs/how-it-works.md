# How it works

The architectural deep-dive. The visual journey across 22 iterations and the specific design decisions live on [haroldathome.com/the-long-take](https://haroldathome.com/the-long-take); this doc covers the *implementation* — what each layer does and why.

## The pipeline

```
LD2450 radar (8 readings/sec, per-target X/Y/speed)
    ↓ ESPHome → MQTT → HA recorder
HA MariaDB recorder (states + states_meta)
    ↓ pymysql SELECT, paired by closest timestamp
exposure_precompute.py
    ↓ decimate, write JSON, ssh-cat to HA
/config/www/the-long-take/data/<room>.json
    ↓ fetch over HTTP
ghost-cloud.js (Three.js renderer)
    ↓ WebGL2 + Web Audio
your screen + speakers
```

## The data contract

The JSON shape was designed to be flat, small, and renderer-driven:

```json
{
  "room": "office",
  "label": "Office",
  "n": 28456,
  "n_original": 57858,
  "decimation": 2,
  "window_hours": 24.0,
  "window_start_ts": 1714510800,
  "window_end_ts":   1714597200,
  "room_dims_mm":    [3380, 2830, 2400],
  "ts": [...],
  "x":  [...],
  "y":  [...],
  "s":  [...],
  "tg": [...]
}
```

Four parallel arrays (`ts`, `x`, `y`, `s`, `tg`) of length `n`. Coordinates in millimetres, time in seconds since `window_start_ts`. `tg` is the LD2450 target ID (1–3) so multi-body rooms can be rendered with per-body colour or trail separation.

## The pre-compute

### Why pair by closest timestamp?

LD2450 reports X, Y, and speed as three separate HA entities, each with its own `last_updated` timestamp. They're emitted nearly simultaneously but not identically. Naive `JOIN ON last_updated_ts` would find almost no exact matches. We pair each X reading with the closest-by-time Y reading within a 300ms window (and speed within 2s), giving us coherent (X, Y, speed) tuples.

### Why decimate?

24 hours × ~30 events/sec/room = ~2.5M raw events. The renderer's frame budget (and the JSON download size) wants closer to 30k. Stride-based decimation throws away most points, **except** where speed ≥ 200 mm/s — those get kept regardless. This preserves transit peaks (someone walking through the room) while thinning the long quiet stretches (someone sitting at a desk).

The "transit-preservation rule" is what makes the worm read clearly. Without it, walking would smooth out into a faint blur; with it, walks remain visible as taut bulges.

### Why ssh-cat instead of sftp?

Home Assistant OS doesn't ship `sftp-server`. Standard `scp` and `sftp` won't work. The workaround is to pipe through `ssh ... cat > path` — same authentication, slower for many small files, fine for the handful we ship every five minutes.

### Why a separate read-only MySQL user?

Defence in depth. If the precompute host is ever compromised, the leaked credentials grant `SELECT` only on the `homeassistant` database. No write, no other databases.

## The renderer

### Why a single continuous tube along the time axis?

Time was the candidate axis for the visualisation because the question being asked is "what did this room look like, all day?" A tube's circumferential position naturally encodes presence intensity, so each time slice gets a wedge — bulging where someone was, thin where empty. The horizontal time axis lets the cursor sweep linearly through the day; the audio synth has a clear cue (the bin-centre crossing).

### Why a water-membrane PBR shader, not flat colour?

Iteration v1–v6 used additive blending and self-emissive colour. The result looked like a glowing cloud, not a *thing*. Switching to standard `NormalBlending` with `depthWrite: false`, plus water-correct PBR (Schlick Fresnel `F0=0.020`, GGX-ish specular, environment-reflection-dominant), made the membrane read as an OBJECT — translucent, reflective, materially present. This was the breakthrough.

### Why fbm-perturbed normals?

A perfectly smooth surface looks plastic. Animated fbm noise on the normal vector gives the surface a constantly-shifting micro-shimmer — same trick as a water-shader, here applied to the membrane.

### Why the seam normal break?

The tube's circumference is a closed loop, but the geometry duplicates the seam vertex (vertex 36 = vertex 0 in UV space). When computing per-vertex normals, you must look up neighbouring vertices via `index % TUBE_RADIAL_SEGMENTS`, NOT `index % ringSize`. Otherwise the seam shows as a visible discontinuity. This was pitfall #4 of v22.

### Why frontier discard for the future-half?

The cursor sweeps left-to-right, "drawing" the day as time passes. Past the cursor (the unwritten future), the membrane should be invisible. We do this in the fragment shader: `if (worldPos.x > cursorX) discard;` — with a soft fade-in band over the next ~50 pixels so the leading edge isn't a hard line.

### Why audio on bin centres, not bin entries?

A note feels "right" when it lands at the *peak* of the corresponding visual event. If the cursor passes through a bin from left to right, the leading edge is at the bin's start; the visual peak (max bulge) is at the bin's centre. Triggering audio on bin entry means the chime sounds 15 seconds before the visual culminates. Triggering on bin centre means the chime and the visual peak coincide — which is what your perceptual system expects. This was pitfall #6.

### Why a 12ms attack on the bell synth → 2ms attack on a water-drop synth?

Same problem as bin centres but at the per-note level. Bell-style synths have a slow attack — by the time the note's audible, the cursor has moved past the trigger point. Replacing with a water-drop synth (sine + 2nd harmonic, downward pitch glide, 2ms attack, exponential decay) gives a sharp onset that aligns audibly with the visual.

### Why visibility-aware mute?

Each room's renderer in an iframe has its own AudioContext. Without mute when the iframe isn't visible, you'd hear all four rooms layered when no tab is focused. The Page Visibility API + IntersectionObserver let us pause both the animation loop AND the AudioContext when the renderer isn't being looked at.

### Why per-room `localStorage` for mute preference?

If you mute the kitchen and don't unmute it, you don't want it to come back loud the next time you open the page. `localStorage['ghost-cloud:<room>:muted']` persists per-room.

## Pitfalls captured during v22 lock

The full list of eight is on [haroldathome.com/the-long-take](https://haroldathome.com/the-long-take). The ones implemented in this code:

1. **Inside-the-tube camera was a wrong turn.** v1 put the camera inside the worm. The shape only reads as an object from outside.
2. **Additive blending hid 3D form.** Switched to NormalBlending + depthWrite:false.
3. **Self-emission ≠ water.** Env reflection 1.5×, halo 0.10, iridescent 0.12. The membrane reflects, doesn't glow.
4. **Seam normal break.** `% TUBE_RADIAL_SEGMENTS` not `% ringSize`. Snap seam vertex position bit-equal.
5. **`depthWrite:true + transparent + DoubleSide`** produces black squares. Standard Three.js footgun.
6. **Audio onset felt late.** Dropped to 2ms attack water-drop synth + bin-centre trigger alignment.
7. **HA dashboard z-index trap.** Push UI elements to `top:80px` to clear HA's app-header. Don't `z-index: 999` the iframe (hides HA nav).
8. **MariaDB credential model.** Dedicated read-only user, generic env-var pattern.

## File map

| Path | What it does |
|---|---|
| `renderer/ghost-cloud.js` | The Three.js renderer + Web Audio synth. ~1100 LOC, single file, no external deps beyond Three.js. |
| `renderer/index.html` | HTML wrapper with UI (status, scrubber, audio toggle, mode toggle). Fetches `./data/<room>.json`. |
| `precompute/exposure_precompute.py` | Pulls per-room data from MariaDB, decimates, ships JSON. |
| `precompute/rooms.example.py` | Template for entity-mapping config. |
| `precompute/systemd/*.{service,timer}` | 5-minute systemd timer + service unit. |
| `examples/index.html` | Standalone preview that runs against the bundled sample without HA. |
| `examples/data/office.json` | One anonymous day of an office for demo. |
