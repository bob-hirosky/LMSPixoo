# AGENTS.md

## What this is

Single-service Python project: polls Lyrion Media Server (LMS) and pushes album art to a Divoom Pixoo64 LED display. No package, no build, no CI, no lint/typecheck config — plain scripts run directly.

## Layout

- `lms_pixoo_service.py` — the entire service (Config, PixooClient, LMSMonitor, AlbumArtService, CLI `main`). All real code lives here; other scripts import from it.
- `test_*.py` — **manual hardware-integration scripts, not a test suite** (no pytest/unittest). They require a live LMS server and/or Pixoo64 on the network and will fail/hang without them. Don't run them to "verify" code changes.
- `find_pixoo.py` — network scanner that probes the local /24 for Pixoo devices via `GET http://<ip>:80/get`. Safe to run (read-only probe).
- `reset_pixoo.py` — restores the Pixoo64 to its default time/weather face (`Draw/ResetHttpGifId` + `Channel/SetIndex` 0). Uses `Config().pixoo_host` by default, `--ip` to override.
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

- **Configuration is hardcoded in source.** Defaults live in the `Config` dataclass (top of `lms_pixoo_service.py`) and as constants near the bottom of each `test_*.py` script. The IPs currently committed (`192.168.2.78` LMS, `192.168.2.206` Pixoo, player MAC `aa:aa:cd:8f:38:b0`) are the author's LAN devices — do not "fix" or parameterize them unless asked. CLI flags override Config but there is no config file (see "Future Enhancements" in README).
- **Pixoo64 protocol quirks:**
  - Sending an image is a 4-step POST sequence to `http://<ip>:80/post` (`Channel/SetIndex` → `Draw/ResetHttpGifId` → `Draw/SendHttpGif` → `Draw/SendHttpItemList`). Despite the name `SendHttpGif`, the payload is raw 64x64 RGB bytes (base64), not a GIF. Image must be exactly 64x64 RGB; alpha is composited onto black.
  - During an upload the device briefly flashes its built-in color-chart test pattern. `PixooClient.send_image` skips the push entirely if the pixel data is identical to what it last sent.
- **LMS protocol:** JSON-RPC at `http://<host>:9000/jsonrpc.js`, method `slim.request`, params `[player_id, [command, ...]]` (empty player_id for server-level commands). Track changes detected by polling `status - 1 tags:alcu` and comparing track `id`. Cover art URL: `artwork_url` field, else `/music/{coverid}/cover.jpg`.
- `LMSMonitor` reuses one `aiohttp.ClientSession`; `PixooClient` creates a new session per call. Follow the existing per-class pattern if touching networking code.
- **The Pixoo64 replies to POSTs with JSON but a `text/html` content-type.** If you parse the response body (e.g. to check `error_code`), use `await response.json(content_type=None)` — see `reset_pixoo.py`. The service doesn't parse responses, which is why it never hits this.
- `select_player_interactive2` is unused duplicate code; `main()` calls `select_player_interactive`.
