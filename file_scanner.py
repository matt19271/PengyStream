"""File scanning and filtering for video files."""
import logging
import os
import time
from pathlib import Path
from typing import List, Set


logger = logging.getLogger(__name__)


class FileScanner:
    """Scan and filter video files for processing."""
    
    def __init__(self, video_extensions: Set[str], suffix: str, output_format: str = 'mp4'):
        """
        Initialize file scanner.
        
        Args:
            video_extensions: Set of valid video file extensions (e.g., {'.mp4', '.mkv'})
            suffix: Suffix to identify already-processed files (e.g., '-PengyStream')
            output_format: Output container format (e.g., 'mp4', 'mkv')
        """
        self.video_extensions = video_extensions
        self.suffix = suffix
        self.output_format = output_format if output_format.startswith('.') else f'.{output_format}'
    
    def is_video_file(self, path: Path) -> bool:
        """
        Check if file is a video file.
        
        Args:
            path: File path to check
            
        Returns:
            True if file is a video file
        """
        return path.suffix.lower() in self.video_extensions
    
    def is_already_processed(self, path: Path) -> bool:
        """
        Check if file has already been processed.
        
        Args:
            path: File path to check
            
        Returns:
            True if file has PengyStream suffix
        """
        stem = path.stem
        return stem.endswith(self.suffix)
    
    def get_output_path(self, input_path: Path) -> Path:
        """
        Generate output path for a video file.
        
        Args:
            input_path: Original video file path
            
        Returns:
            Path for the converted file with -PengyStream suffix
        """
        stem = input_path.stem
        new_name = f"{stem}{self.suffix}{self.output_format}"
        return input_path.parent / new_name
    
    def has_output_file(self, input_path: Path) -> bool:
        """
        Check if output file already exists.
        
        Checks for any file with -PengyStream suffix, regardless of extension.
        This allows for different output formats over time.
        
        Args:
            input_path: Original video file path
            
        Returns:
            True if any corresponding PengyStream file exists
        """
        stem = input_path.stem
        parent = input_path.parent
        pattern = f"{stem}{self.suffix}.*"
        
        # Check if any file matches the pattern
        matching_files = list(parent.glob(pattern))
        return len(matching_files) > 0
    
    def is_file_stable(self, path: Path, wait_time: int = 5) -> bool:
        """
        Check if file is stable (not being written to).
        
        This helps avoid processing files that are currently being
        downloaded or copied.
        
        Args:
            path: File path to check
            wait_time: Seconds to wait between size checks
            
        Returns:
            True if file size hasn't changed
        """
        try:
            if not path.exists():
                return False
            
            # Get initial size
            initial_size = path.stat().st_size
            
            # Wait
            time.sleep(wait_time)
            
            # Check if still exists and size unchanged
            if not path.exists():
                return False
            
            final_size = path.stat().st_size
            return initial_size == final_size
        
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot check file stability for {path}: {e}")
            return False
    
    def scan_folder(self, folder: Path) -> List[Path]:
        """
        Scan folder for video files that need processing.
        
        Args:
            folder: Folder to scan
            
        Returns:
            List of video files that need processing
        """
        candidates = []
        
        try:
            for root, dirs, files in os.walk(folder):
                root_path = Path(root)
                
                for file in files:
                    file_path = root_path / file
                    
                    # Check if it's a video file
                    if not self.is_video_file(file_path):
                        continue
                    
                    # Skip if already processed
                    if self.is_already_processed(file_path):
                        logger.debug(f"Skipping already processed: {file_path}")
                        continue
                    
                    # Skip if output already exists
                    if self.has_output_file(file_path):
                        logger.debug(f"Skipping - output exists: {file_path}")
                        continue
                    
                    candidates.append(file_path)
            
            logger.info(f"Found {len(candidates)} files to process in {folder}")
            return candidates
        
        except Exception as e:
            logger.error(f"Error scanning folder {folder}: {e}")
            return []
    
    def should_process(self, path: Path) -> bool:
        """
        Check if a file should be processed.
        
        Args:
            path: File path to check
            
        Returns:
            True if file should be processed
        """
        # Must be a video file
        if not self.is_video_file(path):
            return False
        
        # Must not already be processed
        if self.is_already_processed(path):
            return False
        
        # Must not have output file
        if self.has_output_file(path):
            return False
        
        # Must exist
        if not path.exists():
            return False
        
        return True
