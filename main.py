# main.py
import cv2
import time
import numpy as np
from modules.camera_manager import CameraManager
from modules.coordinate_system import CoordinateSystem  
from modules.optical_flow_detector import OpticalFlowDetector
from modules.speed_calculator import SpeedCalculator

class TrafficMonitor:
    def __init__(self):
        print("🚗 Initializing Traffic Monitor...")
        print("   Using Optical Flow detection (ignores parked cars)")
        
        self.coord_system = CoordinateSystem()
        self.camera = CameraManager(fps=30, buffer_size=450)
        self.motion_detector = OpticalFlowDetector(self.coord_system)
        self.speed_calculator = SpeedCalculator(self.coord_system)
        
        print("✅ Traffic Monitor initialized")
        print("📝 Single vehicle mode - optical flow tracking\n")
    
    def start_monitoring(self):
        """Spustí hlavní monitoring loop"""
        print("🔄 Starting traffic monitoring...")
        print("   Press 'q' to quit\n")
        
        self.camera.start()
        time.sleep(2)
        
        try:
            self._monitoring_loop()
        except KeyboardInterrupt:
            print("\n⚠️ Monitoring interrupted by user")
        finally:
            self.camera.stop()
            self._print_summary()
    
    def _monitoring_loop(self):
        """Monitoring loop s optical flow"""
        frame_count = 0
        
        while True:
            frame_data = self.camera.get_latest_frame()
            if not frame_data:
                time.sleep(0.01)
                continue
            
            frame = frame_data['frame']
            timestamp = frame_data['timestamp']
            frame_count += 1
            
            # Detekce POUZE pohybujících se vozidel
            detections, motion_mask = self.motion_detector.detect_moving_vehicles(frame)
            
            display_frame = frame.copy()
            
            # Zpracování - vezmi největší detekci
            if detections:
                detections.sort(key=lambda d: d['area'], reverse=True)
                detection = detections[0]
                
                # Aktualizuj speed calculator
                speed_data = self.speed_calculator.update_position(
                    detection['center'], timestamp
                )
                
                # Vykreslení
                self._draw_detection(display_frame, detection, speed_data)
            
            # Zobrazení
            self._display_frame(display_frame, motion_mask, frame_count)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    def _draw_detection(self, frame, detection, speed_data):
        """Vykreslí detekci na frame"""
        x, y, w, h = detection['bbox']
        center = detection['center']
        world_pos = detection['world_pos']
        motion_mag = detection['motion_magnitude']
        
        # Bounding box - barva podle stavu
        state = self.speed_calculator.get_state()
        if state == 'MEASURING':
            color = (0, 255, 0)  # Zelená - měří
        else:
            color = (255, 255, 0)  # Žlutá - čeká
        
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
        cv2.circle(frame, center, 8, (255, 0, 0), -1)
        
        # Info text
        state_text = f"State: {state}"
        cv2.putText(frame, state_text, (x, y-70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        vehicle_num = self.speed_calculator.get_vehicle_count()
        if state == 'MEASURING':
            vehicle_num += 1
        num_text = f"Vehicle #{vehicle_num}"
        cv2.putText(frame, num_text, (x, y-40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        motion_text = f"Motion: {motion_mag:.1f} px/frame"
        cv2.putText(frame, motion_text, (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        world_text = f"({world_pos[0]:.1f}, {world_pos[1]:.1f})m"
        cv2.putText(frame, world_text, (x, y+h+25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    def _draw_zones(self, frame):
        """Vykreslí všechny zóny"""
        trigger_lines = self.coord_system.get_trigger_line_coordinates()
        
        # START LINE - červená (TLUSTÁ)
        start_line = trigger_lines['start_line']
        cv2.line(frame, start_line['point1'], start_line['point2'], (0, 0, 255), 5)
        cv2.putText(frame, "START", 
                   (start_line['point1'][0]+20, start_line['point1'][1]-15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
        
        # END LINE - zelená (TLUSTÁ)
        end_line = trigger_lines['end_line']
        cv2.line(frame, end_line['point1'], end_line['point2'], (0, 255, 0), 5)
        cv2.putText(frame, "END", 
                   (end_line['point1'][0]+20, end_line['point1'][1]-15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)
        
        # 🎯 MEASUREMENT ZONE - žlutý polygon (mezi trigger lines)
        measurement_zone = self.coord_system.get_measurement_zone()
        cv2.polylines(frame, [measurement_zone], isClosed=True, color=(0, 255, 255), thickness=3)
        
        # Pre-detection polygony (modré - tenčí)
        polygons = self.coord_system.get_predetection_polygons()
        for poly in polygons:
            cv2.polylines(frame, [poly], isClosed=True, color=(255, 0, 0), thickness=2)
    
    def _display_frame(self, frame, motion_mask, frame_count):
        """Zobrazí framy"""
        self._draw_zones(frame)
        
        # Resize
        display_height = 540
        aspect_ratio = frame.shape[1] / frame.shape[0]
        display_width = int(display_height * aspect_ratio)
        
        frame_resized = cv2.resize(frame, (display_width, display_height))
        
        # Motion mask v barvě
        motion_colored = cv2.applyColorMap(motion_mask, cv2.COLORMAP_HOT)
        motion_resized = cv2.resize(motion_colored, (display_width//2, display_height//2))
        
        # Info overlay
        fps_text = f"FPS: {self.camera.actual_fps:.1f}"
        cv2.putText(frame_resized, fps_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        vehicle_count_text = f"Vehicles: {self.speed_calculator.get_vehicle_count()}"
        cv2.putText(frame_resized, vehicle_count_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        state_text = f"State: {self.speed_calculator.get_state()}"
        cv2.putText(frame_resized, state_text, (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.imshow("Traffic Monitor", frame_resized)
        cv2.imshow("Motion Detection (Optical Flow)", motion_resized)
    
    def _print_summary(self):
        """Vypíše souhrn na konci"""
        print(f"\n{'='*60}")
        print(f"📊 MONITORING SUMMARY")
        print(f"{'='*60}")
        print(f"Total vehicles measured: {self.speed_calculator.get_vehicle_count()}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    monitor = TrafficMonitor()
    monitor.start_monitoring()
