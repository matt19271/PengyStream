"""Cleanup orphaned PengyStream files."""
import logging
import os
from pathlib import Path
from typing import List, Set


logger = logging.getLogger(__name__)


class Cleanup:
    """Handle cleanup of orphaned PengyStream files."""
    
    def __init__(self, video_extensions: Set[str], suffix: str):
        """
        Initialize cleanup handler.
        
        Args:
            video_extensions: Set of valid video file extensions
            suffix: PengyStream suffix (e.g., '-PengyStream')
        """
        self.video_extensions = video_extensions
        self.suffix = suffix
    
    def get_original_path(self, pengystream_path: Path) -> Path:
        """
        Get the original file path from a PengyStream file.
        
        Args:
            pengystream_path: Path to PengyStream file
            
        Returns:
            Path to the original file (may not exist)
        """
        stem = pengystream_path.stem
        ext = pengystream_path.suffix
        
        # Remove suffix
        if stem.endswith(self.suffix):
            original_stem = stem[:-len(self.suffix)]
            original_name = f"{original_stem}{ext}"
            return pengystream_path.parent / original_name
        
        return pengystream_path
    
    def is_pengystream_file(self, path: Path) -> bool:
        """
        Check if file is a PengyStream file.
        
        Args:
            path: File path to check
            
        Returns:
            True if file has PengyStream suffix
        """
        return (
            path.suffix.lower() in self.video_extensions and
            path.stem.endswith(self.suffix)
        )
    
    def find_orphaned_files(self, folder: Path) -> List[Path]:
        """
        Find PengyStream files without corresponding originals.
        
        Args:
            folder: Folder to scan
            
        Returns:
            List of orphaned PengyStream files
        """
        orphaned = []
        
        try:
            for root, dirs, files in os.walk(folder):
                root_path = Path(root)
                
                for file in files:
                    file_path = root_path / file
                    
                    # Check if it's a PengyStream file
                    if not self.is_pengystream_file(file_path):
                        continue
                    
                    # Check if original exists
                    original_path = self.get_original_path(file_path)
                    if not original_path.exists():
                        orphaned.append(file_path)
                        logger.info(f"Found orphaned file: {file_path}")
            
            return orphaned
        
        except Exception as e:
            logger.error(f"Error scanning for orphaned files in {folder}: {e}")
            return []
    
    def cleanup_orphaned_files(self, folders: List[Path], dry_run: bool = False) -> int:
        """
        Remove orphaned PengyStream files from all folders.
        
        Args:
            folders: List of folders to clean
            dry_run: If True, only log what would be deleted
            
        Returns:
            Number of files deleted (or would be deleted in dry_run)
        """
        total_deleted = 0
        
        for folder in folders:
            logger.info(f"Scanning for orphaned files in: {folder}")
            orphaned = self.find_orphaned_files(folder)
            
            for file_path in orphaned:
                try:
                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete: {file_path}")
                    else:
                        file_path.unlink()
                        logger.info(f"Deleted orphaned file: {file_path}")
                    
                    total_deleted += 1
                
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete {total_deleted} orphaned files")
        else:
            logger.info(f"Deleted {total_deleted} orphaned files")
        
        return total_deleted
