"""Configuration loader for PengyStream."""
import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration management for PengyStream."""
    
    def __init__(self):
        """Load configuration from .env file."""
        load_dotenv()
        
        # Load and validate movie folders
        folders_str = os.getenv('MOVIE_FOLDERS', '')
        if not folders_str:
            raise ValueError("MOVIE_FOLDERS must be set in .env file")
        
        self.movie_folders = [
            Path(folder.strip()) 
            for folder in folders_str.split(',') 
            if folder.strip()
        ]
        
        # Encoding settings
        self.max_encodes = int(os.getenv('MAX_ENCODES', '2'))
        self.video_codec = os.getenv('VIDEO_CODEC', 'h264')
        self.audio_codec = os.getenv('AUDIO_CODEC', 'aac')
        
        # Parse resolution (e.g., "1440p" -> 1440)
        max_res_str = os.getenv('MAX_RESOLUTION', '1440p')
        self.max_resolution = int(max_res_str.replace('p', ''))
        
        # Performance thresholds
        self.cpu_threshold = float(os.getenv('CPU_THRESHOLD', '80'))
        self.gpu_threshold = float(os.getenv('GPU_THRESHOLD', '80'))
        
        # Timing
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '60'))
        
        # Stream copy behavior
        copy_str = os.getenv('COPY_IF_COMPATIBLE', 'true').lower()
        self.copy_if_compatible = copy_str in ('true', '1', 'yes')
        
        # Logging
        self.log_file = os.getenv('LOG_FILE', 'pengystream.log')
        
        # PengyStream suffix
        self.suffix = '-PengyStream'
        
        # Supported video extensions
        self.video_extensions = {
            '.mp4', '.mkv', '.avi', '.mov', '.m4v', 
            '.wmv', '.flv', '.webm', '.ts', '.m2ts'
        }
    
    def validate(self):
        """Validate configuration settings."""
        # Check that folders exist
        for folder in self.movie_folders:
            if not folder.exists():
                raise ValueError(f"Folder does not exist: {folder}")
            if not folder.is_dir():
                raise ValueError(f"Not a directory: {folder}")
        
        # Validate thresholds
        if not 0 <= self.cpu_threshold <= 100:
            raise ValueError("CPU_THRESHOLD must be between 0 and 100")
        if not 0 <= self.gpu_threshold <= 100:
            raise ValueError("GPU_THRESHOLD must be between 0 and 100")
        
        # Validate max encodes
        if self.max_encodes < 1:
            raise ValueError("MAX_ENCODES must be at least 1")
        
        return True
    
    def __str__(self):
        """String representation of config."""
        return (
            f"PengyStream Config:\n"
            f"  Folders: {', '.join(str(f) for f in self.movie_folders)}\n"
            f"  Max Encodes: {self.max_encodes}\n"
            f"  Video: {self.video_codec} @ {self.max_resolution}p\n"
            f"  Audio: {self.audio_codec}\n"
            f"  CPU Threshold: {self.cpu_threshold}%\n"
            f"  GPU Threshold: {self.gpu_threshold}%\n"
            f"  Copy Compatible: {self.copy_if_compatible}\n"
        )
