"""Room configuration for The Long Take pre-compute.

Copy this file to `rooms.py` (gitignored) and edit the ROOMS list to
match your own LD2450 entity naming in Home Assistant.

Each tuple is:
  (
    room_id,         # short identifier — appears in URL `?r=<room_id>`
                     # and is the JSON filename
    entity_prefix,   # the LD2450 entity name MINUS the
                     # `_target_<n>_<x|y|speed>` suffix
                     # (the precompute script appends those automatically)
    friendly_label,  # human-readable label, shown in the renderer's
                     # status strip
    room_dims_mm,    # [width, depth, height] in millimetres
                     # used to scale the cube view; rough is fine
  )

Example LD2450 entity names produced by ESPHome:

  sensor.living_room_radar_target_1_x
  sensor.living_room_radar_target_1_y
  sensor.living_room_radar_target_1_speed
  sensor.living_room_radar_target_2_x
  ...

In that case, `entity_prefix` is "sensor.living_room_radar".

You can configure as many rooms as you have radars.
"""

ROOMS = [
    ("office",      "sensor.office_radar",      "Office",      [3380, 2830, 2400]),
    ("living_room", "sensor.living_room_radar", "Living Room", [5000, 4000, 2700]),
    # ("library",   "sensor.library_radar",     "Library",     [4000, 3500, 2700]),
    # ("kitchen",   "sensor.kitchen_radar",     "Kitchen",     [5000, 3000, 2400]),
]
