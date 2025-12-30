"""Performance monitoring for CPU and GPU usage."""
import psutil
import logging
import subprocess
import platform
from typing import Tuple


logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor CPU and GPU usage to control encoding workload."""
    
    def __init__(self, cpu_threshold: float, gpu_threshold: float):
        """
        Initialize performance monitor.
        
        Args:
            cpu_threshold: CPU usage percentage threshold (0-100)
            gpu_threshold: GPU usage percentage threshold (0-100)
        """
        self.cpu_threshold = cpu_threshold
        self.gpu_threshold = gpu_threshold
    
    def get_cpu_usage(self) -> float:
        """
        Get current CPU usage percentage.
        
        Returns:
            CPU usage as a percentage (0-100)
        """
        return psutil.cpu_percent(interval=1)
    
    def get_gpu_usage(self) -> float:
        """
        Get current GPU usage percentage.
        
        Supports NVIDIA GPUs on Windows/Linux via nvidia-smi.
        
        Returns:
            GPU usage as a percentage (0-100), or 0 if unavailable
        """
        try:
            # Try NVIDIA GPU monitoring via nvidia-smi
            if platform.system() in ('Windows', 'Linux'):
                try:
                    result = subprocess.run(
                        ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # Parse GPU usage (first GPU if multiple)
                        usage_str = result.stdout.strip().split('\n')[0]
                        return float(usage_str)
                except (subprocess.SubprocessError, FileNotFoundError, ValueError, IndexError):
                    pass  # nvidia-smi not available or failed
            
            # Fallback: return 0 to avoid blocking encodes
            # Users can set GPU_THRESHOLD to 100 to effectively disable GPU monitoring
            return 0.0
            
        except Exception as e:
            logger.warning(f"Unable to get GPU usage: {e}")
            return 0.0
    
    def can_encode(self) -> Tuple[bool, str]:
        """
        Check if system resources allow encoding.
        
        Returns:
            Tuple of (can_encode, reason)
        """
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()
        
        if cpu_usage > self.cpu_threshold:
            reason = f"CPU usage too high: {cpu_usage:.1f}% > {self.cpu_threshold}%"
            logger.debug(reason)
            return False, reason
        
        if gpu_usage > self.gpu_threshold:
            reason = f"GPU usage too high: {gpu_usage:.1f}% > {self.gpu_threshold}%"
            logger.debug(reason)
            return False, reason
        
        return True, "System resources available"
    
    def log_current_usage(self):
        """Log current CPU and GPU usage."""
        cpu = self.get_cpu_usage()
        gpu = self.get_gpu_usage()
        logger.info(f"System usage - CPU: {cpu:.1f}%, GPU: {gpu:.1f}%")
