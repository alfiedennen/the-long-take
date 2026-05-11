# Redaction record

A transparent log of what was scrubbed when this code was extracted from
its original home in the haroldathome.com repository, to make it safe
for public release.

The originals continue to live in the private monorepo; this repo is the
generic-ised, shareable version.

## What changed

### `precompute/exposure_precompute.py`

| Original | Public version | Reason |
|---|---|---|
| `HA_HOST = "root@192.168.1.11"` (hardcoded internal IP) | `HA_HOST = os.environ.get("EXPOSURE_HA_HOST", "root@homeassistant.local")` | Don't ship internal LAN topology |
| `HA_OUT_DIR = "/config/www/exposure/data"` (hardcoded path) | `HA_OUT_DIR = os.environ.get("EXPOSURE_HA_OUT_DIR", "/config/www/the-long-take/data")` | Configurable; default uses the public repo's name |
| `DB_USER = "harold_reader"` | `DB_USER = "the_long_take_reader"` (configurable via env) | Generic example name |
| `DB_PASSWORD = os.environ.get("HAROLD_READER_PASSWORD")` | `DB_PASSWORD = os.environ.get("EXPOSURE_DB_PASSWORD")` | Generic env-var name |
| Inline `ROOMS` list with private entity prefixes (e.g. `sensor.xiao_test_presence_office_candidate`) and a possessive label (`"Alfie's Office"`) | Moved to a separate `rooms.py` (gitignored), with a `rooms.example.py` template using generic names | Each user maps their own LD2450 entities; we don't ship one household's wiring |
| Various comments referencing `harold-agent`, `LXC 102`, the migration from `yesterday_precompute.py` | Re-written to be generic ("any always-on Linux host"; the broader narrative lives on the website) | Internal project history isn't useful out of context |

### `renderer/ghost-cloud.js`

No changes. The renderer is data-shape-driven — it consumes the JSON
contract and contains zero references to entity names, hostnames,
addresses, or household specifics. Verified by full-file grep for
sensitive patterns; clean.

### `renderer/index.html` and `examples/index.html`

| Original | Public version | Reason |
|---|---|---|
| CSS comments mentioning "the Emanations dashboard" (the haroldathome dashboard the embed iframes into) | "a Home Assistant dashboard" | Generic — not every user is iframing into the same place |
| Hardcoded title `<title>Exposure</title>` | `<title>The Long Take</title>` and `<title>The Long Take — example</title>` | Match the public repo's name |

### `precompute/systemd/exposure-precompute.service`

| Original | Public version | Reason |
|---|---|---|
| `EnvironmentFile=/opt/harold-agent/.env` | `EnvironmentFile=/etc/the-long-take/env` | Generic; documented in `docs/install.md` |
| `ExecStart=/opt/harold-agent/venv/bin/python /opt/harold-agent/scripts/exposure_precompute.py 24` | `ExecStart=/opt/the-long-take/venv/bin/python /opt/the-long-take/exposure_precompute.py 24` | Generic install path |
| `WorkingDirectory=/opt/harold-agent` | `WorkingDirectory=/opt/the-long-take` | Same |

### Sample data (`examples/data/office.json`)

The bundled sample is one anonymous day of LD2450 radar events from one
office room. The data is XYZ coordinates plus speed plus timestamps —
no names, no entity IDs, no household-identifying metadata. Timestamps
in the file are stored as **seconds since the window start** (relative,
not absolute), so the file does not reveal *which* day it captured.

The room dimensions and friendly label retained from the original
JSON (`"label": "Alfie's Office"`, `"room_dims_mm": [3380, 2830, 2400]`)
are factually about Alfie's office — these stay because (a) the room
dimensions are unidentifying, and (b) "Alfie's Office" is the same
name used publicly on the haroldathome.com piece this repo accompanies.

### What was NOT shipped

- The full house's set of room JSONs (only office is bundled — to demonstrate the renderer, not to publish a complete profile of one specific day across one household)
- The Home Assistant configuration around the radar entities (entity registries, recorder include/exclude rules, dashboard layouts)
- The original repo's `harold-agent` pre-commit hooks and AWS backup scripts (orthogonal to this piece)
- Any internal documentation referring to specific household members beyond first name (Alfie/Elena where relevant; nothing more identifying)

## Verification before push

The `.githooks/pre-commit` hook (armed with `git config core.hooksPath
.githooks` after clone) scans the staged diff for the patterns
documented above and blocks any commit that re-introduces them. Bypass
is `--no-verify`; never used legitimately.

## License audit

- All code files in this repo: MIT (LICENSE)
- All documentation, prose, screenshots, sample data: CC-BY-NC 4.0 (LICENSE-CONTENT)
- No third-party code is bundled. Three.js is loaded at runtime from a CDN.
