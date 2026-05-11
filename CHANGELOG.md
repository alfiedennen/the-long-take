# Changelog

## 1.0.0 — 2026-05-11

Initial public release. Extracted from the haroldathome.com private
monorepo and generic-ised for public use.

### What's in 1.0.0

- **Renderer v22** (locked 10 May 2026): translucent water-membrane PBR shader, animated normal-perturbation fbm shimmer, UnrealBloom post-processing, IBL environment, scrubber, pentatonic water-drop synth with synthetic convolution reverb, visibility-aware mute, two playback modes (Reveal / See-all).
- **Pre-compute v1** (locked 8 May 2026): pymysql → MariaDB recorder, X/Y/speed pairing by closest timestamp, transit-peak-preserving decimation to ~30k points per room per 24h window, ssh-cat deploy to HA OS.
- **Systemd timer**: 5-minute refresh cadence, on-boot warm-up, persistent.
- **Bundled sample**: one office, one day, ~30k decimated points (~600KB).

See [haroldathome.com/the-long-take](https://haroldathome.com/the-long-take)
for the full visual journey across 22 iterations and the eight pitfalls
captured during the lock.
