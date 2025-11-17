# modules/camera_manager.py
from picamera2 import Picamera2
import cv2
import time
import threading
from collections import deque
import numpy as np

class CameraManager:
    def __init__(self, fps=30, buffer_size=450):  # 3 sekundy při 50 FPS
        """
        fps: Tvých 50 FPS
        buffer_size: Kolik framů držet v paměti
        """
        self.picam2 = Picamera2()
        self.fps = fps
        self.buffer_size = buffer_size
        
        # Kruhový buffer pro framy
        self.frame_buffer = deque(maxlen=buffer_size)
        self.buffer_lock = threading.Lock()
        
        # Thread pro snímání
        self.capture_thread = None
        self.running = False
        
        # FPS tracking
        self.frame_times = deque(maxlen=fps)
        self.actual_fps = 0.0
        
        self._setup_camera()
    
    def _setup_camera(self):
        """Nastaví kameru podle tvé konfigurace"""
        config = self.picam2.create_preview_configuration(
            main={"size": (2304, 1296), "format": "RGB888"},
            controls={"FrameRate": self.fps}
        )
        self.picam2.configure(config)
        print(f"✓ Camera configured: {2304}x{1296} @ {self.fps}FPS")
    
    def start(self):
        """Spustí kontinuální snímání do bufferu"""
        if not self.running:
            self.picam2.start()
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            print("✓ Camera streaming started")
    
    def stop(self):
        """Zastaví snímání"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        self.picam2.stop()
        print("✓ Camera streaming stopped")
    
    def _capture_loop(self):
        """Hlavní smyčka pro snímání do bufferu"""
        while self.running:
            try:
                frame = self.picam2.capture_array("main")
                current_time = time.time()
                
                # Aktualizace FPS
                self.frame_times.append(current_time)
                if len(self.frame_times) > 1:
                    time_span = self.frame_times[-1] - self.frame_times[0]
                    self.actual_fps = len(self.frame_times) / time_span if time_span > 0 else 0
                
                # Přidání do bufferu s timestampem
                with self.buffer_lock:
                    self.frame_buffer.append({
                        'frame': frame.copy(),
                        'timestamp': current_time,
                        'frame_id': len(self.frame_buffer)
                    })
                
                # Malá pauza pro stability
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Camera capture error: {e}")
                time.sleep(0.1)
    
    def get_latest_frame(self):
        """Vrátí nejnovější frame"""
        with self.buffer_lock:
            if self.frame_buffer:
                return self.frame_buffer[-1]
        return None
    
    def get_frame_history(self, seconds_back=2.0):
        """Vrátí historii framů za posledních X sekund"""
        current_time = time.time()
        cutoff_time = current_time - seconds_back
        
        with self.buffer_lock:
            history = [f for f in self.frame_buffer 
                      if f['timestamp'] >= cutoff_time]
        return history
    
    def save_detection_sequence(self, detection_time, seconds_before=1.0, seconds_after=1.0):
        """Uloží sekvenci framů kolem detekce vozidla"""
        start_time = detection_time - seconds_before  
        end_time = detection_time + seconds_after
        
        with self.buffer_lock:
            sequence = [f for f in self.frame_buffer 
                       if start_time <= f['timestamp'] <= end_time]
        
        return sequence
