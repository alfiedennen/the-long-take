# Install

End-to-end setup, from a fresh Home Assistant install with no LD2450 to a working Long Take.

If you already have HA + MariaDB recorder + an LD2450 reporting target X/Y/speed, skip ahead to [the precompute setup](#3-install-the-precompute).

## 1. Switch HA's recorder to MariaDB

The default SQLite recorder won't sustain the LD2450 scan rate (~8 readings per second per radar across multiple targets). Switch to MariaDB.

If you don't already run MariaDB, the easiest path on HA OS is the official add-on:

1. **Settings → Add-ons → Add-on store → MariaDB** → install → start.
2. Note the database password the add-on generates (or set your own in the add-on config).
3. In your HA `configuration.yaml`:
   ```yaml
   recorder:
     db_url: mysql://homeassistant:<password>@core-mariadb/homeassistant?charset=utf8mb4
   ```
4. Restart HA. Watch the logs for `Recorder` errors. The first start migrates your existing SQLite history into MariaDB and can take several minutes on a busy install.

## 2. Set up the LD2450

The Hi-Link LD2450 is a 24 GHz mmWave radar that reports up to three target X/Y positions plus per-target speed. The cleanest deployment is via ESPHome on a small ESP32 board. The community has published a stable component:

- ESPHome custom integration for the LD2450 — see search results for "ESPHome LD2450". Several maintained variants exist; pick whichever is current.

The relevant ESPHome YAML produces entities of the shape:

```
sensor.<your_name>_target_1_x
sensor.<your_name>_target_1_y
sensor.<your_name>_target_1_speed
sensor.<your_name>_target_2_x
sensor.<your_name>_target_2_y
sensor.<your_name>_target_2_speed
sensor.<your_name>_target_3_x
sensor.<your_name>_target_3_y
sensor.<your_name>_target_3_speed
```

The precompute script expects exactly this naming, with a configurable prefix. So if you call the radar `living_room_radar`, your `entity_prefix` in `rooms.py` is `sensor.living_room_radar`.

**Mount the radar** somewhere with a clear view of the room — corner-mounted at ~1.5m height works well. Calibrate via the LD2450's serial config tool (Hi-Link ships one with the device, or you can do it via the ESPHome web UI).

Verify in HA Developer Tools → States: when you walk through the room, the X and Y values should change in real time.

## 3. Install the precompute

The pre-compute is a tiny Python script that runs on any always-on Linux machine reachable from your HA host. Could be the same box that runs HA, an LXC, a Pi, a NAS, anything.

```sh
sudo mkdir -p /opt/the-long-take
sudo git clone https://github.com/alfiedennen/the-long-take.git /opt/the-long-take/src
cd /opt/the-long-take

# Set up the venv
python3 -m venv venv
./venv/bin/pip install -r src/precompute/requirements.txt

# Stage the runnable script + config at the install root
cp src/precompute/exposure_precompute.py .
cp src/precompute/rooms.example.py rooms.py

# Edit rooms.py to map your LD2450 entities
${EDITOR:-nano} rooms.py
```

## 4. Create the read-only MariaDB user

On the MariaDB server (if you used the HA add-on, you can shell in via the add-on's shell):

```sql
CREATE USER 'the_long_take_reader'@'%' IDENTIFIED BY 'pick-a-strong-password-here';
GRANT SELECT ON homeassistant.* TO 'the_long_take_reader'@'%';
FLUSH PRIVILEGES;
```

Replace `'%'` with your precompute host's IP / hostname for tighter scope, e.g. `'the_long_take_reader'@'<your-precompute-host>'`.

The user is read-only — `SELECT` only — by design. The precompute does not write back to the recorder.

## 5. Configure the environment

Create `/etc/the-long-take/env`:

```sh
EXPOSURE_DB_PASSWORD=pick-a-strong-password-here
EXPOSURE_HA_HOST=root@homeassistant.local
EXPOSURE_DB_HOST=core-mariadb
# Optional overrides:
# EXPOSURE_HA_OUT_DIR=/config/www/the-long-take/data
# EXPOSURE_DB_USER=the_long_take_reader
# EXPOSURE_DB_NAME=homeassistant
```

`chmod 600 /etc/the-long-take/env`.

The precompute uses SSH to deploy JSONs to your HA host. Make sure the precompute host has its SSH key copied to the HA OS host:

```sh
ssh-copy-id root@homeassistant.local
```

If you've never SSH'd into HA OS, install and configure the SSH & Web Terminal add-on first.

## 6. First run

```sh
cd /opt/the-long-take
set -a && . /etc/the-long-take/env && set +a
./venv/bin/python exposure_precompute.py 24
```

Expected output:

```
The Long Take pre-compute — 24.0h window, target ~30000 points/room
================================================================
  Office             orig=  57858  kept= 28456  stride= 2    624KB
  Living Room        orig= 102310  kept= 30015  stride= 3    700KB

Deployed to root@homeassistant.local:/config/www/the-long-take/data/
```

If you see this, you're done.

## 7. Mount the renderer

```sh
ssh root@homeassistant.local "mkdir -p /config/www/the-long-take"
scp /opt/the-long-take/src/renderer/* root@homeassistant.local:/config/www/the-long-take/
```

Visit `http://homeassistant.local:8123/local/the-long-take/?r=office` (replace `office` with whatever `room_id` you used in `rooms.py`).

You should see your room's last 24 hours playing back.

## 8. Set up the 5-minute timer

```sh
sudo cp /opt/the-long-take/src/precompute/systemd/exposure-precompute.service /etc/systemd/system/
sudo cp /opt/the-long-take/src/precompute/systemd/exposure-precompute.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now exposure-precompute.timer
```

Verify:

```sh
systemctl status exposure-precompute.timer
journalctl -u exposure-precompute.service -n 50
```

Every five minutes, the JSONs get refreshed and the renderer (on next page load) shows the freshest 24 hours.

## 9. Embed it somewhere

Optional — a small Lovelace card iframe to surface The Long Take inside your HA dashboard:

```yaml
type: iframe
url: /local/the-long-take/?r=office
aspect_ratio: 16:9
```

That's the install.
