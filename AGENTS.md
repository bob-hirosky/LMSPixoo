# AGENTS.md

## What this is

Single-service Python project: polls Lyrion Media Server (LMS) and pushes album art to a Divoom Pixoo64 LED display. No package, no build, no CI, no lint/typecheck config — plain scripts run directly.

## Layout

- `lms_pixoo_service.py` — the service entry point: `Config` dataclass, `AlbumArtService` (poll loop), CLI `main`. `PixooClient` and `LMSMonitor` are re-exported here for backward compatibility.
- `pixoo.py` — Pixoo64 client and protocol: `PixooClient` (4-step upload, skip-unchanged), `post_command` (low-level POST helper used by diagnostic scripts), `reset_pixoo`, `to_pixel_data`, `make_title_frames` (scrolling title overlay), `PIXOO_SIZE`.
- `lms.py` — LMS client: `LMSMonitor` (single public `send_command` with `player_id=""` for server-level calls, player discovery/interactive selection, track status, album art download).
- `patterns.py` — 64x64 test pattern generators shared by the test/diagnostic scripts.
- `test_*.py`, `diagnose_pixoo.py`, `find_correct_format.py` — **manual hardware-integration scripts, not a test suite** (no pytest/unittest). They require a live LMS server and/or Pixoo64 on the network and will fail/hang without them. Don't run them to "verify" code changes. `test_lms.py` contains one self-contained `test_monitor_playback_returns_when_cancelled()` function (DummyClient, no hardware) that can be run manually. IPs are no longer hardcoded in these scripts — they take `--ip`/`--host` args defaulting to `Config` values.
- `find_pixoo.py` — network scanner that probes the local /24 for Pixoo devices via `GET http://<ip>:80/get`. Safe to run (read-only probe). Standalone (uses aiohttp directly, no shared module).
- `reset_pixoo.py` — thin CLI wrapper around `pixoo.reset_pixoo` (restores default time/weather face). Uses `Config().pixoo_host` by default, `--ip` to override. The service also does this automatically on exit (`AlbumArtService.start` finally-block calls `PixooClient.reset()`).
- `setup.sh` / `run.sh` — create venv + install deps / activate venv + run service (Linux/Mac only).
- `lms.diff` — leftover patch file, not source. Ignore unless asked.
- Deps: `aiohttp`, `Pillow` (`requirements.txt`), Python 3.8+.

## Commands

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
python lms_pixoo_service.py --list-players          # discover players (needs reachable LMS)
python lms_pixoo_service.py --host X --pixoo-ip Y --player-id Z   # or -s for interactive select
```

## Conventions and gotchas

- **Configuration is hardcoded in source.** Defaults live in the `Config` dataclass (top of `lms_pixoo_service.py`). The IPs currently committed (`192.168.2.78` LMS, `192.168.2.206` Pixoo, player MAC `aa:aa:cd:8f:38:b0`) are the author's LAN devices — do not "fix" or parameterize them unless asked. CLI flags override Config but there is no config file (see "Future Enhancements" in README).
- **Pixoo64 protocol quirks:**
  - Sending an image is a 4-step POST sequence to `http://<ip>:80/post` (`Channel/SetIndex` → `Draw/ResetHttpGifId` → `Draw/SendHttpGif` → `Draw/SendHttpItemList`). Despite the name `SendHttpGif`, the payload is raw 64x64 RGB bytes (base64), not a GIF. Image must be exactly 64x64 RGB; alpha is composited onto black.
  - During an upload the device briefly flashes its built-in color-chart test pattern. `PixooClient.send_image` skips the push entirely if the pixel data is identical to what it last sent.
  - Multi-frame animation: POST one `Draw/SendHttpGif` per frame, all sharing the same `PicID`, with `PicNum` = total frames, `PicOffset` = frame index, `PicSpeed` = ms per frame. The device loops the frames. `PixooClient.send_image(title=...)` uses this to scroll long song titles in a bottom bar (`make_title_frames`). Uploading many frames (~140+) takes ~20s and the device can occasionally reset the connection mid-upload — retrying works.
  - Title overlay is opt-in: `--show-title` CLI flag / `Config.show_title` (default off = plain full-screen album art).
- **LMS protocol:** JSON-RPC at `http://<host>:9000/jsonrpc.js`, method `slim.request`, params `[player_id, [command, ...]]` (empty player_id for server-level commands). Track changes detected by polling `status - 1 tags:alcu` and comparing track `id`. Cover art URL: `artwork_url` field, else `/music/{coverid}/cover.jpg`.
- `LMSMonitor` reuses one `aiohttp.ClientSession`; `PixooClient` creates a new session per call. Follow the existing per-class pattern if touching networking code.
- **The Pixoo64 replies to POSTs with JSON but a `text/html` content-type.** `pixoo.post_command` handles this with `await response.json(content_type=None)`; use `post_command(..., check_error=True)` if you need `error_code` validated.
