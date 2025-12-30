# PengyStream

Automated video conversion tool that continuously monitors network-mounted folders and converts videos to tablet-friendly formats using H.264/AAC encoding with configurable resolution limits.

## Features

- 🎬 **Automatic Monitoring**: Uses filesystem watching (watchdog) to detect new video files
- 🔄 **Smart Stream Copying**: Selectively copies compatible streams to avoid unnecessary re-encoding
- ⚡ **Performance Control**: Monitors CPU/GPU usage to prevent system overload
- 🧹 **Auto Cleanup**: Removes orphaned converted files when originals are deleted
- 📊 **Comprehensive Logging**: Detailed logs of all operations
- ⚙️ **Highly Configurable**: All settings via `.env` file

## Requirements

- Python 3.7+
- FFmpeg (must be installed and available in PATH)
- FFprobe (usually comes with FFmpeg)
- **Windows only**: NVIDIA GPU drivers (if using GPU threshold monitoring)

## Installation

1. **Clone or download this project**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**:
   
   **Windows**:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use [Chocolatey](https://chocolatey.org/):
     ```bash
     choco install ffmpeg
     ```
   - Or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (recommended)
   - Extract and add the `bin` folder to your system PATH
   
   **macOS**:
   ```bash
   brew install ffmpeg
   ```
   
   **Ubuntu/Debian**:
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

4. **Verify FFmpeg installation**:
   ```bash
   ffmpeg -version
   ffprobe -version
   ```

## Configuration

1. **Copy the example configuration**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with your settings:
   ```env
   # Comma-separated paths to watch (use forward slashes or escaped backslashes on Windows)
   MOVIE_FOLDERS=C:/Users/YourName/Videos/Movies,D:/Media/TV Shows
   
   # Maximum simultaneous encodes
   MAX_ENCODES=2
   
   # Video codec (h264)
   VIDEO_CODEC=h264
   
   # Maximum resolution (1080p, 1440p, 2160p, etc.)
   MAX_RESOLUTION=1440p
   
   # Audio codec (aac)
   AUDIO_CODEC=aac
   
   # CPU threshold percentage (pause if exceeded)
   CPU_THRESHOLD=80
   
   # GPU threshold percentage (pause if exceeded, requires NVIDIA GPU + drivers)
   GPU_THRESHOLD=80
   
   # Poll interval in seconds
   POLL_INTERVAL=60
   
   # Copy streams if already compatible (true/false)
   COPY_IF_COMPATIBLE=true
   
   # Log file path
   LOG_FILE=pengystream.log
   ```

### Configuration Options Explained

- **MOVIE_FOLDERS**: Comma-separated list of folders to monitor. Can be network-mapped drives or local. On Windows, use forward slashes (e.g., `C:/Videos`) or escaped backslashes (e.g., `C:\\Videos`).
- **MAX_ENCODES**: Number of videos to encode simultaneously. Set based on your system's capabilities.
- **MAX_RESOLUTION**: Cap video resolution at this height. Videos higher than this will be downscaled.
- **CPU_THRESHOLD**: If CPU usage exceeds this %, pause starting new encodes.
- **GPU_THRESHOLD**: If GPU usage exceeds this %, pause starting new encodes (requires NVIDIA GPU with drivers on Windows/Linux).
- **COPY_IF_COMPATIBLE**: If `true`, compatible streams are copied instead of re-encoded.

## Usage

### Running PengyStream

```bash
python main.py
```

Or make it executable:
```bash
chmod +x main.py
./main.py
```

### Stopping PengyStream

Press `Ctrl+C` to gracefully stop. PengyStream will:
1. Finish any in-progress encoding jobs
2. Run a final cleanup
3. Save all logs

## How It Works

### File Processing Logic

1. **Detection**: Watches configured folders for video files
2. **Filtering**: Skips files that:
   - Already have `-PengyStream` suffix
   - Have a corresponding converted file
   - Are currently being written
3. **Compatibility Check**:
   - If video is H.264 ≤ MAX_RESOLUTION AND audio is AAC → Skip entirely
   - If only video is compatible → Copy video, transcode audio
   - If only audio is compatible → Transcode video, copy audio
   - If neither compatible → Transcode both
4. **Encoding**: Converts with FFmpeg using configured settings
5. **Output**: Saves as `originalname-PengyStream.ext`

### Selective Stream Copying

PengyStream intelligently avoids unnecessary transcoding:

- **Already compatible**: File is skipped entirely
- **Video OK, audio needs work**: Video stream is copied, only audio is transcoded
- **Audio OK, video too high-res**: Audio stream is copied, only video is transcoded
- **Both need work**: Both streams are transcoded

This saves significant time and preserves quality where possible.

### Performance Control

- Before starting each encode, checks CPU/GPU usage
- If thresholds are exceeded, waits before starting new jobs
- Already-running encodes continue to completion
- Prevents system from becoming overloaded

### Cleanup

- Runs periodically (every hour by default)
- Finds `-PengyStream` files without corresponding originals
- Removes orphaned files to save disk space

## File Naming

**Input**: `Movie Title (2023).mkv`  
**Output**: `Movie Title (2023)-PengyStream.mkv`

The converted file is saved in the same directory as the original.

## Logging

All operations are logged to `pengystream.log` (or your configured log file):

- Files detected and queued
- Conversion start/completion
- Skipped files (with reasons)
- Performance monitoring
- Cleanup operations
- Errors and warnings

## Troubleshooting

### FFmpeg not found
```
Error: ffmpeg/ffprobe not found in PATH
```
**Solution**: Install FFmpeg and ensure it's in your system PATH.

### Permission errors
```
Error: Permission denied
```
**Solution**: Ensure you have read/write permissions for the folders you're monitoring.

### No files being processed
- Check that `MOVIE_FOLDERS` paths are correct
- Verify files don't already have `-PengyStream` suffix
- Check logs for skip reasons

### High CPU/GPU usage preventing encodes
- Increase `CPU_THRESHOLD` and `GPU_THRESHOLD` values
- Reduce `MAX_ENCODES` to limit simultaneous jobs

### Files not being detected
- Ensure watchdog is working (check logs)
- Verify file extensions are in supported list
- Check that files are stable (not being written)

## Project Structure

```
PengyStream/
├── main.py                  # Main application entry point
├── config.py                # Configuration loading
├── file_scanner.py          # File detection and filtering
├── video_converter.py       # FFmpeg wrapper with stream logic
├── performance_monitor.py   # CPU/GPU monitoring
├── cleanup.py               # Orphaned file cleanup
├── requirements.txt         # Python dependencies
├── .env.example            # Example configuration
├── .env                    # Your configuration (not in git)
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Advanced Usage

### Running as a Service (Linux/systemd)

Create `/etc/systemd/system/pengystream.service`:

```ini
[Unit]
Description=PengyStream Video Converter
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/PengyStream
ExecStart=/usr/bin/python3 /path/to/PengyStream/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable pengystream
sudo systemctl start pengystream
sudo systemctl status pengystream
```

### Running as a Service (macOS/launchd)

Create `~/Library/LaunchAgents/com.pengystream.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pengystream</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/youruser/Documents/PengyStream/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/youruser/Documents/PengyStream</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then:
```bash
launchctl load ~/Library/LaunchAgents/com.pengystream.plist
```

### Running as a Service (Windows/Task Scheduler)

1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Basic Task**
3. Name: `PengyStream`
4. Trigger: **When the computer starts** (or **When I log on**)
5. Action: **Start a program**
   - Program: `C:\Python\python.exe` (or your Python path)
   - Arguments: `C:\Users\YourName\Documents\PengyStream\main.py`
   - Start in: `C:\Users\YourName\Documents\PengyStream`
6. Check **Open Properties when finished**
7. In Properties:
   - General tab: Check **Run whether user is logged on or not**
   - Conditions tab: Uncheck **Start only if on AC power**
   - Settings tab: Check **If the task is already running, do not start a new instance**

**Alternative - Using NSSM (Non-Sucking Service Manager)**:

1. Download [NSSM](https://nssm.cc/download)
2. Install as a service:
   ```cmd
   nssm install PengyStream "C:\Python\python.exe" "C:\Users\YourName\Documents\PengyStream\main.py"
   nssm set PengyStream AppDirectory "C:\Users\YourName\Documents\PengyStream"
   nssm start PengyStream
   ```

## License

This project is provided as-is for personal use.

## Contributing

Feel free to submit issues and enhancement requests!
