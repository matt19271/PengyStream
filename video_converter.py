"""Video conversion using FFmpeg with selective stream copying."""
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple


logger = logging.getLogger(__name__)


class VideoInfo:
    """Information about a video file's streams."""
    
    def __init__(self, video_codec: str, video_height: int, 
                 audio_codec: str, has_video: bool, has_audio: bool):
        self.video_codec = video_codec
        self.video_height = video_height
        self.audio_codec = audio_codec
        self.has_video = has_video
        self.has_audio = has_audio


class VideoConverter:
    """Handle video conversion with FFmpeg."""
    
    def __init__(self, video_codec: str, audio_codec: str, 
                 max_resolution: int, copy_if_compatible: bool):
        """
        Initialize video converter.
        
        Args:
            video_codec: Target video codec (e.g., 'h264')
            audio_codec: Target audio codec (e.g., 'aac')
            max_resolution: Maximum height in pixels (e.g., 1440)
            copy_if_compatible: Whether to copy compatible streams
        """
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.max_resolution = max_resolution
        self.copy_if_compatible = copy_if_compatible
    
    def get_video_info(self, file_path: Path) -> Optional[VideoInfo]:
        """
        Get video file information using ffprobe.
        
        Args:
            file_path: Path to video file
            
        Returns:
            VideoInfo object or None if probe fails
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"ffprobe failed for {file_path}: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            
            video_codec = None
            video_height = 0
            audio_codec = None
            has_video = False
            has_audio = False
            
            for stream in streams:
                codec_type = stream.get('codec_type')
                
                if codec_type == 'video' and not has_video:
                    has_video = True
                    video_codec = stream.get('codec_name', '').lower()
                    video_height = int(stream.get('height', 0))
                
                elif codec_type == 'audio' and not has_audio:
                    has_audio = True
                    audio_codec = stream.get('codec_name', '').lower()
            
            return VideoInfo(
                video_codec=video_codec or '',
                video_height=video_height,
                audio_codec=audio_codec or '',
                has_video=has_video,
                has_audio=has_audio
            )
        
        except Exception as e:
            logger.error(f"Error probing {file_path}: {e}")
            return None
    
    def is_compatible(self, info: VideoInfo) -> Tuple[bool, bool]:
        """
        Check if video and audio streams are already compatible.
        
        Args:
            info: VideoInfo object
            
        Returns:
            Tuple of (video_compatible, audio_compatible)
        """
        # Check video compatibility
        video_compat = (
            info.has_video and
            info.video_codec in ('h264', 'avc') and
            info.video_height <= self.max_resolution
        )
        
        # Check audio compatibility
        audio_compat = (
            info.has_audio and
            info.audio_codec == self.audio_codec
        )
        
        return video_compat, audio_compat
    
    def convert_video(self, input_path: Path, output_path: Path) -> bool:
        """
        Convert video file with selective stream copying.
        
        Args:
            input_path: Source video file
            output_path: Destination video file
            
        Returns:
            True if successful, False otherwise
        """
        # Get video information
        info = self.get_video_info(input_path)
        if not info:
            logger.error(f"Cannot get video info for {input_path}")
            return False
        
        # Check compatibility
        video_compat, audio_compat = self.is_compatible(info)
        
        # Skip if both are compatible
        if self.copy_if_compatible and video_compat and audio_compat:
            logger.info(f"Skipping {input_path.name} - already compatible")
            return False
        
        # Build ffmpeg command
        cmd = ['ffmpeg', '-i', str(input_path), '-y']
        
        # Video handling
        if video_compat and self.copy_if_compatible:
            logger.info(f"Copying video stream for {input_path.name}")
            cmd.extend(['-c:v', 'copy'])
        else:
            # Transcode video
            logger.info(f"Transcoding video stream for {input_path.name}")
            cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '23'])
            
            # Scale if needed
            if info.video_height > self.max_resolution:
                scale_filter = f"scale=-2:{self.max_resolution}"
                cmd.extend(['-vf', scale_filter])
                logger.info(f"Scaling from {info.video_height}p to {self.max_resolution}p")
        
        # Audio handling
        if audio_compat and self.copy_if_compatible:
            logger.info(f"Copying audio stream for {input_path.name}")
            cmd.extend(['-c:a', 'copy'])
        else:
            # Transcode audio
            logger.info(f"Transcoding audio stream for {input_path.name}")
            cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
        
        # Output file
        cmd.append(str(output_path))
        
        try:
            logger.info(f"Starting conversion: {input_path.name}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=None  # No timeout - let encode finish
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg failed for {input_path}: {result.stderr}")
                # Clean up partial output
                if output_path.exists():
                    output_path.unlink()
                return False
            
            logger.info(f"Successfully converted: {input_path.name} -> {output_path.name}")
            return True
        
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout for {input_path}")
            if output_path.exists():
                output_path.unlink()
            return False
        
        except Exception as e:
            logger.error(f"Error converting {input_path}: {e}")
            if output_path.exists():
                output_path.unlink()
            return False
