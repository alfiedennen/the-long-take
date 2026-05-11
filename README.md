# the-long-take

> Twenty-four hours of one room, rendered as a single continuous translucent water-membrane you can listen to. Built for [haroldathome.com/the-long-take](https://haroldathome.com/the-long-take); released for anyone with a Home Assistant install and an mmWave radar.

A long take is a film term — Hitchcock made *Rope* (1948) as one apparent continuous shot. This is a long take of one room, fixed camera, twenty-four hours, no cuts. The room plays.

The radar reports body positions eight times a second. The pipeline pulls the day's positions from your Home Assistant database, decimates them, and writes a small JSON. The renderer reads the JSON and draws a translucent membrane that bulges where bodies were, thins where the room was empty, and grows along a horizontal time axis. A pentatonic synth chimes when the playback cursor crosses each thirty-second bin. Audio is opt-in.

---

## At a glance

- **Renderer**: Three.js + WebGL2, water-correct PBR, fbm-perturbed normals, UnrealBloom post-processing, Web Audio synth with synthetic convolution reverb. ~1100 LOC, single file.
- **Data pipeline**: Python + pymysql + numpy. Pulls LD2450 X/Y/speed columns from the HA MariaDB recorder, pairs by timestamp, decimates, ships JSON to the renderer host.
- **Schedule**: 5-minute systemd timer. The day on your wall is always within 5 minutes of live.
- **Format**: one JSON per room, ~200–700 KB after decimation.
- **Browser audience**: modern Chromium, Safari, Firefox. Requires WebGL2.

---

## Quick look — no install required

```sh
git clone https://github.com/alfiedennen/the-long-take.git
cd the-long-take

# Browsers block file:// fetches across directories, so a tiny local
# server is required to load the bundled sample.
python -m http.server 8000
```

Then open <http://localhost:8000/examples/?r=office>. You should see a translucent membrane, slowly orbiting, with a scrubber along the bottom. Tap **TAP TO ENABLE SOUND** in the top-right; press space to play; drag to orbit; scroll to zoom.

The bundled sample is one anonymous day in one office — about 30,000 radar events, decimated from ~58,000 originals.

---

## Run it on your own house

### What you need

- **Home Assistant 2024.6+**, with the **MariaDB** recorder backend (the default SQLite recorder hits performance cliffs at the LD2450 scan rate — switching to MariaDB is a [single-line config change](https://www.home-assistant.io/integrations/recorder/#custom-database-engines) but takes some setup).
- **One Hi-Link LD2450 mmWave radar** per room you want to render. Other presence sensors (PIR, FP300, mmWave-without-position) won't work — the long take needs per-target X/Y position over time.
- **Python 3.11+** with `pymysql` and `numpy`.
- **A small always-on Linux machine** that can SSH to your Home Assistant host (any LXC, Pi, or mini-PC). The pre-compute runs here, not on HA itself.

### Setup, in five steps

1. **Create a read-only MariaDB user** dedicated to this script. On your MariaDB host:
   ```sql
   CREATE USER 'the_long_take_reader'@'localhost' IDENTIFIED BY 'pick-a-strong-password';
   GRANT SELECT ON homeassistant.* TO 'the_long_take_reader'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. **Install the precompute on your Linux host**:
   ```sh
   git clone https://github.com/alfiedennen/the-long-take.git
   cd the-long-take/precompute
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp rooms.example.py rooms.py
   ```
   Edit `rooms.py` to map your LD2450 entity names. (See [`docs/adapt.md`](docs/adapt.md) for the entity-naming details.)

3. **Configure the environment**:
   ```sh
   export EXPOSURE_DB_PASSWORD='your-strong-password'
   export EXPOSURE_HA_HOST='root@homeassistant.local'
   ```

4. **Run it once manually** to verify everything works:
   ```sh
   python exposure_precompute.py 24
   ```
   You should see point counts per room printed, then `Deployed to root@homeassistant.local:/config/www/the-long-take/data/`.

5. **Install the systemd timer** for the 5-minute refresh. See [`docs/install.md`](docs/install.md) for the full systemd setup.

### Mount the renderer in Home Assistant

```sh
scp -r renderer/ root@homeassistant.local:/config/www/the-long-take
```

Visit `https://<your-ha>/local/the-long-take/?r=office` for one room. (Replace `office` with whatever `room_id` you used in `rooms.py`.)

---

## How it works

For the architectural deep-dive — the binning strategy, the membrane shader, the audio synth, the eight pitfalls captured during v22 — see [`docs/how-it-works.md`](docs/how-it-works.md).

---

## Adapt to your setup

For mapping LD2450 entity names, adjusting room dimensions, changing the visual lock, sub-day windows, single-room vs multi-room — see [`docs/adapt.md`](docs/adapt.md).

---

## Known limits

- **LD2450 only.** Requires per-target X/Y position. PIR, FP300 (Aqara), and other binary presence sensors won't work.
- **MariaDB only.** SQLite recorder won't scale to LD2450's 8 readings/sec across multiple rooms over a 24h window.
- **One day default.** Longer windows (a week, a month) need decimation re-tuning — the current `TARGET_POINTS = 30_000` is calibrated for 24h.
- **Audio requires user gesture.** Browser policy. The first click anywhere enables sound.
- **WebGL2 required.** No fallback for older browsers.
- **Single-room per render.** Each iframe / browser tab renders one room. The piece's grandeur is in viewing each room's tube alongside the others — but the renderer doesn't do this internally; it's a deployment / dashboard composition concern.

---

## Lock state

- Renderer: `v22` (10 May 2026)
- Pre-compute: `v1` (8 May 2026)
- Visual journey, design lock state, and the eight captured pitfalls live on [haroldathome.com/the-long-take](https://haroldathome.com/the-long-take).

See [`CHANGELOG.md`](CHANGELOG.md) for release notes.

---

## Credits

- Original work at [haroldathome.com](https://haroldathome.com) by Alfie Dennen, Hastings, England.
- Built with Three.js, pymysql, numpy.
- Inspired by Hitchcock's *Rope*, BERG, Holo, LIGO data viz, and the fixed-camera tradition.
- Thanks to the Home Assistant community for MariaDB recorder hardening notes and the LD2450 ESPHome integration.

---

## Licences

| Scope | Licence |
|---|---|
| Code (`renderer/`, `precompute/`, `examples/index.html`, `.githooks/`) | **MIT** — see [`LICENSE`](LICENSE) |
| Documentation, sample data, prose, screenshots | **CC-BY-NC 4.0** — see [`LICENSE-CONTENT`](LICENSE-CONTENT) |

---

## See also

For the architectural context this piece sits in — the wider house system, the AI agent named after the previous occupant, the wall display, the wake words, the painted axonometrics that change with who is home — see [haroldathome.com](https://haroldathome.com).
