#!/usr/bin/env python3
"""The Long Take — radar event pre-compute.

Pulls the last N hours of LD2450 target data per room from a Home
Assistant MariaDB recorder, pairs (x, y) by closest timestamp, joins
the speed channel, decimates to a manageable point count, and writes
one JSON per room into the renderer's data directory on the HA host.

Designed to run every 5 minutes via a systemd timer (see
./systemd/exposure-precompute.timer). The default window is 24 hours.

ENVIRONMENT
  EXPOSURE_DB_PASSWORD   MariaDB password for the read-only user
  EXPOSURE_HA_HOST       SSH target for the HA OS host that serves the
                         renderer (e.g. root@homeassistant.local)
  EXPOSURE_HA_OUT_DIR    Path on the HA host where JSONs land
                         (default: /config/www/the-long-take/data)

REQUIREMENTS
  Home Assistant 2024.6+ with MariaDB recorder backend (NOT SQLite —
  the default backend hits performance cliffs at this scan rate).
  pymysql + numpy.
  Hi-Link LD2450 mmWave radar per room (other presence sensors that
  don't report per-target X/Y position will not work).

JSON SHAPE (the renderer's data contract)
  {
    "room":            "office",
    "label":           "Office",
    "n":               28456,           # decimated point count
    "n_original":      57858,
    "decimation":      2,               # 1 of every N kept
    "window_hours":    24.0,
    "window_start_ts": 1714510800,      # unix seconds
    "window_end_ts":   1714597200,
    "room_dims_mm":    [3380, 2830, 2400],
    "ts": [...],   # seconds since window_start, length n
    "x":  [...],   # mm, radar local frame, length n
    "y":  [...],   # mm, radar local frame, length n
    "s":  [...],   # mm/s absolute speed, length n
    "tg": [...]    # target id (1, 2, 3), length n — for multi-body rooms
  }

CONFIGURE YOUR ROOMS
  Edit `rooms.py` (copy from rooms.example.py). Each entry maps a
  per-room `entity_prefix` to the LD2450 entity naming you've used in
  Home Assistant. Targets are addressed as
  `{prefix}_target_{n}_{x|y|speed}`.

LICENCE
  MIT — see LICENSE in the repo root.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pymysql

# Local config — see rooms.example.py
try:
    from rooms import ROOMS
except ImportError:
    sys.exit(
        "rooms.py not found. Copy rooms.example.py to rooms.py and edit "
        "the ROOMS list to match your own LD2450 entity names."
    )


# ─── Config ────────────────────────────────────────────────────────────────

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
TARGET_POINTS = 30_000     # decimate to roughly this many per room
MAX_TARGETS = 3            # LD2450 reports up to 3 bodies

HA_HOST = os.environ.get("EXPOSURE_HA_HOST", "root@homeassistant.local")
HA_OUT_DIR = os.environ.get(
    "EXPOSURE_HA_OUT_DIR", "/config/www/the-long-take/data"
)

WORK = Path(os.environ.get("EXPOSURE_WORK_DIR", "/tmp/exposure"))
WORK.mkdir(exist_ok=True)

DB_HOST = os.environ.get("EXPOSURE_DB_HOST", "localhost")
DB_USER = os.environ.get("EXPOSURE_DB_USER", "the_long_take_reader")
DB_PASSWORD = os.environ.get("EXPOSURE_DB_PASSWORD")
DB_NAME = os.environ.get("EXPOSURE_DB_NAME", "homeassistant")


# ─── DB layer ──────────────────────────────────────────────────────────────


def fetch_one(cur, eid: str, since_ts: int) -> list[tuple[float, float]]:
    """Pull `(last_updated_ts, state)` rows for one entity since `since_ts`.
    Returns empty list if no rows. Skips rows where state is non-numeric."""
    cur.execute(
        """
        SELECT s.last_updated_ts, s.state
        FROM states s
        JOIN states_meta m ON s.metadata_id = m.metadata_id
        WHERE m.entity_id = %s AND s.last_updated_ts >= %s
        ORDER BY s.last_updated_ts
        """,
        (eid, since_ts),
    )
    out = []
    for ts, val in cur.fetchall():
        try:
            out.append((float(ts), float(val)))
        except (TypeError, ValueError):
            continue
    return out


# ─── Pairing + assembly ────────────────────────────────────────────────────


def pair_by_ts(a, b, max_gap_s: float = 0.3):
    """Pair entries from `a` with the closest-timestamp entry from `b`
    within max_gap_s. Returns list of (ts, val_a, val_b)."""
    if not a or not b:
        return []
    b_ts = np.array([r[0] for r in b])
    b_v = np.array([r[1] for r in b])
    out = []
    for ts, va in a:
        idx = np.searchsorted(b_ts, ts)
        cands = []
        if idx > 0:
            cands.append(idx - 1)
        if idx < len(b_ts):
            cands.append(idx)
        if not cands:
            continue
        best = min(cands, key=lambda i: abs(b_ts[i] - ts))
        if abs(b_ts[best] - ts) <= max_gap_s:
            out.append((ts, va, float(b_v[best])))
    return out


def collect_target(cur, prefix: str, target_id: int, since_ts: int):
    """Return list of (ts, x, y, speed) for one target (1/2/3) of one radar."""
    xs = fetch_one(cur, f"{prefix}_target_{target_id}_x", since_ts)
    ys = fetch_one(cur, f"{prefix}_target_{target_id}_y", since_ts)
    ss = fetch_one(cur, f"{prefix}_target_{target_id}_speed", since_ts)
    if not xs or not ys:
        return []
    xy = pair_by_ts(xs, ys)
    sp_pairs = pair_by_ts([(t, x) for t, x, _ in xy], ss, max_gap_s=2.0)
    sp_by_ts = {t: abs(s) for t, _, s in sp_pairs}
    return [(t, x, y, sp_by_ts.get(t, 0.0)) for t, x, y in xy]


def collect_room(cur, prefix: str, since_ts: int):
    """Collect all targets for a room. Returns list of
    (ts, x, y, speed, target_id) sorted by ts."""
    out = []
    for tgt in range(1, MAX_TARGETS + 1):
        for ts, x, y, sp in collect_target(cur, prefix, tgt, since_ts):
            # Skip the (0, 0) "no target" sentinel that LD2450 emits when a
            # target slot is empty — it pollutes the cloud at the origin.
            if x == 0 and y == 0:
                continue
            out.append((ts, x, y, sp, tgt))
    out.sort(key=lambda r: r[0])
    return out


def decimate(points: list, target_n: int):
    """Keep every Nth point. Preserve transit-speed peaks by ALSO keeping
    points where speed >= 200 mm/s within the kept stride."""
    n = len(points)
    if n <= target_n:
        return points, 1
    stride = max(1, n // target_n)
    decimated = []
    for i, p in enumerate(points):
        keep = (i % stride == 0) or (p[3] >= 200)
        if keep:
            decimated.append(p)
    return decimated, stride


def write_room(room_id: str, label: str, points: list, dims: list[int],
               stride: int, n_orig: int, since_ts: int) -> tuple[Path, int]:
    if not points:
        payload = {
            "room": room_id, "label": label, "n": 0,
            "n_original": 0, "decimation": 1,
            "window_hours": HOURS,
            "window_start_ts": since_ts,
            "window_end_ts": int(time.time()),
            "room_dims_mm": dims,
            "ts": [], "x": [], "y": [], "s": [], "tg": [],
        }
    else:
        t0 = points[0][0]
        payload = {
            "room": room_id,
            "label": label,
            "n": len(points),
            "n_original": n_orig,
            "decimation": stride,
            "window_hours": HOURS,
            "window_start_ts": int(t0),
            "window_end_ts": int(points[-1][0]),
            "room_dims_mm": dims,
            "ts": [round(p[0] - t0, 2) for p in points],
            "x":  [int(p[1]) for p in points],
            "y":  [int(p[2]) for p in points],
            "s":  [int(p[3]) for p in points],
            "tg": [int(p[4]) for p in points],
        }
    out_local = WORK / f"{room_id}.json"
    out_local.write_text(json.dumps(payload, separators=(",", ":")))
    return out_local, payload["n"]


# ─── Main ──────────────────────────────────────────────────────────────────


def main():
    if not DB_PASSWORD:
        sys.exit(
            "EXPOSURE_DB_PASSWORD not in env. "
            "Set it in your environment or in the systemd EnvironmentFile."
        )

    print(f"The Long Take pre-compute — {HOURS}h window, "
          f"target ~{TARGET_POINTS} points/room")
    print("=" * 64)

    since_ts = int(time.time() - HOURS * 3600)
    summary = {"generated_at": int(time.time()), "rooms": {}}

    conn = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4", autocommit=True,
        connect_timeout=10,
    )
    try:
        cur = conn.cursor()
        for room_id, prefix, label, dims in ROOMS:
            pts = collect_room(cur, prefix, since_ts)
            n_orig = len(pts)
            decim, stride = decimate(pts, TARGET_POINTS)
            local, n_kept = write_room(
                room_id, label, decim, dims, stride, n_orig, since_ts
            )
            size_kb = local.stat().st_size // 1024
            print(
                f"  {label:18s} orig={n_orig:7d}  "
                f"kept={n_kept:6d}  stride={stride:2d}  {size_kb:5d}KB"
            )
            summary["rooms"][room_id] = {
                "label": label,
                "n_original": n_orig,
                "n_kept": n_kept,
                "size_kb": size_kb,
            }
    finally:
        conn.close()

    (WORK / "index.json").write_text(json.dumps(summary, indent=2))

    # Deploy to HA OS via ssh-cat (HA OS lacks sftp-server).
    subprocess.run(["ssh", HA_HOST, f"mkdir -p {HA_OUT_DIR}"], check=True)
    for room_id, *_ in ROOMS:
        local = WORK / f"{room_id}.json"
        with open(local, "rb") as f:
            subprocess.run(
                ["ssh", HA_HOST, f"cat > {HA_OUT_DIR}/{room_id}.json"],
                stdin=f, check=True,
            )
    with open(WORK / "index.json", "rb") as f:
        subprocess.run(
            ["ssh", HA_HOST, f"cat > {HA_OUT_DIR}/index.json"],
            stdin=f, check=True,
        )
    print(f"\nDeployed to {HA_HOST}:{HA_OUT_DIR}/")


if __name__ == "__main__":
    main()
