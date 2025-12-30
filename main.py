#!/usr/bin/env python3
"""
PengyStream - Automated video conversion for tablet-friendly formats.

Monitors folders for video files and converts them to H.264/AAC format
with configurable resolution limits and selective stream copying.
"""
import logging
import signal
import sys
import time
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from config import Config
from file_scanner import FileScanner
from video_converter import VideoConverter
from performance_monitor import PerformanceMonitor
from cleanup import Cleanup


# Global flag for graceful shutdown
shutdown_flag = threading.Event()


class VideoFileHandler(FileSystemEventHandler):
    """Handle filesystem events for video files."""
    
    def __init__(self, file_queue: Queue, scanner: FileScanner):
        """
        Initialize event handler.
        
        Args:
            file_queue: Queue to add files to
            scanner: FileScanner instance
        """
        super().__init__()
        self.file_queue = file_queue
        self.scanner = scanner
        self.logger = logging.getLogger(__name__)
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        self._handle_file(event.src_path)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        self._handle_file(event.src_path)
    
    def _handle_file(self, file_path_str: str):
        """
        Process a file event.
        
        Args:
            file_path_str: Path to the file as string
        """
        try:
            file_path = Path(file_path_str)
            
            # Check if we should process this file
            if self.scanner.should_process(file_path):
                self.logger.info(f"New file detected: {file_path}")
                
                # Check if file is stable (not being written)
                if self.scanner.is_file_stable(file_path):
                    self.file_queue.put(file_path)
                    self.logger.info(f"Added to queue: {file_path.name}")
                else:
                    self.logger.info(f"File not stable, skipping: {file_path.name}")
        
        except Exception as e:
            self.logger.error(f"Error handling file event for {file_path_str}: {e}")


class EncodingWorker(threading.Thread):
    """Worker thread for encoding videos."""
    
    def __init__(self, worker_id: int, file_queue: Queue, 
                 converter: VideoConverter, scanner: FileScanner,
                 perf_monitor: PerformanceMonitor):
        """
        Initialize encoding worker.
        
        Args:
            worker_id: Unique worker identifier
            file_queue: Queue of files to process
            converter: VideoConverter instance
            scanner: FileScanner instance
            perf_monitor: PerformanceMonitor instance
        """
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.file_queue = file_queue
        self.converter = converter
        self.scanner = scanner
        self.perf_monitor = perf_monitor
        self.logger = logging.getLogger(f"{__name__}.Worker{worker_id}")
    
    def run(self):
        """Main worker loop."""
        self.logger.info(f"Worker {self.worker_id} started")
        
        while not shutdown_flag.is_set():
            try:
                # Get file from queue with timeout
                try:
                    file_path = self.file_queue.get(timeout=1)
                except Empty:
                    continue
                
                # Check if we should still process this file
                if not self.scanner.should_process(file_path):
                    self.logger.info(f"Skipping {file_path.name} - no longer needs processing")
                    self.file_queue.task_done()
                    continue
                
                # Check system resources
                can_encode, reason = self.perf_monitor.can_encode()
                if not can_encode:
                    self.logger.info(f"Cannot encode yet: {reason}")
                    # Put file back in queue and wait
                    self.file_queue.put(file_path)
                    self.file_queue.task_done()
                    time.sleep(10)
                    continue
                
                # Process the file
                output_path = self.scanner.get_output_path(file_path)
                self.logger.info(f"Worker {self.worker_id} processing: {file_path.name}")
                
                success = self.converter.convert_video(file_path, output_path)
                
                if success:
                    self.logger.info(f"Worker {self.worker_id} completed: {file_path.name}")
                else:
                    self.logger.warning(f"Worker {self.worker_id} failed: {file_path.name}")
                
                self.file_queue.task_done()
            
            except Exception as e:
                self.logger.error(f"Worker {self.worker_id} error: {e}")
                try:
                    self.file_queue.task_done()
                except:
                    pass
        
        self.logger.info(f"Worker {self.worker_id} stopped")


def setup_logging(log_file: str):
    """
    Configure logging.
    
    Args:
        log_file: Path to log file
    """
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = logging.getLogger(__name__)
    logger.info("Shutdown signal received, stopping...")
    shutdown_flag.set()


def initial_scan(folders: list, scanner: FileScanner, file_queue: Queue):
    """
    Perform initial scan of folders.
    
    Args:
        folders: List of folders to scan
        scanner: FileScanner instance
        file_queue: Queue to add files to
    """
    logger = logging.getLogger(__name__)
    logger.info("Performing initial scan...")
    
    for folder in folders:
        logger.info(f"Scanning: {folder}")
        files = scanner.scan_folder(folder)
        
        for file_path in files:
            if scanner.is_file_stable(file_path):
                file_queue.put(file_path)
                logger.info(f"Queued: {file_path.name}")
            else:
                logger.info(f"File not stable: {file_path.name}")
    
    logger.info(f"Initial scan complete. {file_queue.qsize()} files queued.")


def main():
    """Main application entry point."""
    # Load configuration
    try:
        config = Config()
        config.validate()
        print(config)
    except Exception as e:
        print(f"Configuration error: {e}")
        print("\nPlease create a .env file based on .env.example")
        return 1
    
    # Setup logging
    setup_logging(config.log_file)
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("PengyStream starting...")
    logger.info("=" * 60)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize components
    scanner = FileScanner(config.video_extensions, config.suffix, config.output_format)
    converter = VideoConverter(
        config.video_codec,
        config.audio_codec,
        config.max_resolution,
        config.copy_if_compatible
    )
    perf_monitor = PerformanceMonitor(config.cpu_threshold, config.gpu_threshold)
    cleanup_handler = Cleanup(config.video_extensions, config.suffix)
    
    # File queue
    file_queue = Queue()
    
    # Perform initial scan
    initial_scan(config.movie_folders, scanner, file_queue)
    
    # Start encoding workers
    workers = []
    for i in range(config.max_encodes):
        worker = EncodingWorker(i + 1, file_queue, converter, scanner, perf_monitor)
        worker.start()
        workers.append(worker)
    
    # Setup filesystem watchers
    observer = Observer()
    event_handler = VideoFileHandler(file_queue, scanner)
    
    for folder in config.movie_folders:
        observer.schedule(event_handler, str(folder), recursive=True)
        logger.info(f"Watching: {folder}")
    
    observer.start()
    logger.info("Filesystem monitoring started")
    
    # Periodic cleanup timer
    last_cleanup = time.time()
    cleanup_interval = 3600  # 1 hour
    
    try:
        # Main loop
        while not shutdown_flag.is_set():
            # Check if it's time for cleanup
            if time.time() - last_cleanup > cleanup_interval:
                logger.info("Running periodic cleanup...")
                cleanup_handler.cleanup_orphaned_files(config.movie_folders)
                last_cleanup = time.time()
            
            # Log status
            queue_size = file_queue.qsize()
            if queue_size > 0:
                logger.info(f"Queue size: {queue_size}")
                perf_monitor.log_current_usage()
            
            # Sleep
            time.sleep(config.poll_interval)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_flag.set()
    
    finally:
        # Cleanup
        logger.info("Shutting down...")
        
        # Stop observer
        observer.stop()
        observer.join()
        
        # Wait for workers
        logger.info("Waiting for encoding workers to finish...")
        for worker in workers:
            worker.join(timeout=5)
        
        # Final cleanup
        logger.info("Running final cleanup...")
        cleanup_handler.cleanup_orphaned_files(config.movie_folders)
        
        logger.info("PengyStream stopped")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
