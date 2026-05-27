 # LMS to Pixoo64 Album Art Display
 
 Standalone Python service that monitors Lyrion Media Server (LMS) for song changes and displays album art on a Divoom Pixoo64 LED display.
 
 ## Features
 
 - Real-time monitoring of LMS playback
 - Automatic album art extraction and resizing
 - Network-based communication with Pixoo64
 - Async I/O for efficient performance
 - Modular, extensible design
 
 ## Prerequisites
 
 - Python 3.8 or higher
 - Lyrion Media Server (v9.1.0 or compatible)
 - Divoom Pixoo64 LED display on the same network
 - Network connectivity between the service, LMS, and Pixoo64
 
 ## Installation
 
 1. Install Python dependencies:
 ```bash
 pip install -r requirements.txt
 ```
 
 2. Find your Pixoo64's IP address:
    - Open the Divoom app on your phone
    - Go to Settings → Device Info
    - Note the IP address
 
 3. Update configuration in `lms_pixoo_service.py`:
    - Set `pixoo_host` to your Pixoo64's IP address
    - Set `lms_host` if LMS is not on localhost
    - Adjust `lms_port` if using non-default port
 
 ## Testing
 
 Before running the full service, test your Pixoo64 connection:
 
 ```bash
 # Edit test_pixoo.py and set PIXOO_IP to your device's IP
 python test_pixoo.py
 ```
 
 You should see test patterns appear on your Pixoo64 display.
 
 ## Usage
 
 Run the service:
 
 ```bash
 python lms_pixoo_service.py
 ```
 
 The service will:
 1. Connect to your LMS server
 2. Auto-detect the first available player (or use configured player ID)
 3. Monitor for song changes
 4. Download album art when a new song starts
 5. Resize and send the image to your Pixoo64
 
 Press `Ctrl+C` to stop the service.
 
 ## Configuration
 
 Edit the `Config` class in `lms_pixoo_service.py`:
 
 ```python
 config = Config(
     lms_host="localhost",       # LMS server IP/hostname
     lms_port=9000,              # LMS JSON-RPC port
     lms_player_id="",           # MAC address or empty for auto-detect
     pixoo_host="192.168.2.206", # Your Pixoo64 IP
     pixoo_port=80,              # Pixoo64 HTTP port
     poll_interval=1.0,          # Check interval in seconds
 )
 ```
 
 ## Architecture
 
 ```
 ┌─────────────────┐
 │ Lyrion Media    │
 │ Server (LMS)    │◄─── JSON-RPC API
 └────────┬────────┘
          │
          │ Song change events
          │ Album art download
          ▼
 ┌─────────────────┐
 │  Python Service │
 │  - LMS Monitor  │
 │  - Image Proc   │
 │  - Pixoo Client │
 └────────┬────────┘
          │
          │ HTTP POST
          │ (Base64 image data)
          ▼
 ┌─────────────────┐
 │ Divoom Pixoo64  │
 │ LED Display     │
 └─────────────────┘
 ```
 
 ## API Details
 
 ### LMS JSON-RPC
 - Endpoint: `http://lms-host:9000/jsonrpc.js`
 - Uses `status` command with `tags:alcu` for album art URLs
 - Downloads cover art via `/music/{coverid}/cover.jpg`
 
 ### Pixoo64 HTTP API
 - Endpoint: `http://pixoo-ip:80/post`
 - Command: `Device/SetStaticImage`
 - Image format: Base64-encoded RGB pixel array (64x64x3 bytes)
 
 ## Troubleshooting
 
 **"Cannot connect to Pixoo64"**
 - Verify the IP address is correct
 - Ensure Pixoo64 is powered on and connected to WiFi
 - Check that both devices are on the same network
 - Try pinging the Pixoo64 IP
 
 **"No LMS player found"**
 - Ensure LMS is running
 - Check that at least one player is connected
 - Verify LMS host/port settings
 - Try accessing `http://lms-host:9000` in a browser
 
 **"No album art URL available"**
 - Some tracks may not have embedded album art
 - Check that album art is visible in LMS web interface
 - Verify the track has proper metadata
 
 ## Future Enhancements
 
 - [ ] Configuration file (YAML/JSON)
 - [ ] Multiple player support
 - [ ] Fallback images for tracks without album art
 - [ ] WebSocket subscription instead of polling
 - [ ] systemd service file for autostart
 - [ ] Web UI for monitoring and configuration
 - [ ] Brightness control based on time of day
 
 ## License
 
 MIT License - feel free to modify and extend!
