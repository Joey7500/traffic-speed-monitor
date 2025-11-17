# modules/motion_detector.py

import cv2
import numpy as np

class SimpleMotionDetector:
    def __init__(self, coordinate_system):
        """Motion detector optimalizovaný pro 45° úhel a auta do 60 km/h"""
        self.coord_system = coordinate_system
        
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200,
            varThreshold=30,
            detectShadows=True
        )
        
        # NOVÉ NASTAVENÍ
        self.min_contour_area = 3000
        self.max_contour_area = 40000
        
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        
    def detect_motion(self, frame):
        """Detekuje pohyb optimalizovaný pro auta do 60 km/h"""
        # Background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Morfologické operace
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.morph_kernel)
        closing_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (12, 12))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, closing_kernel)
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.dilate(fg_mask, dilate_kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filtr velikosti
            if self.min_contour_area < area < self.max_contour_area:
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
                
                # Filtr aspect ratio
                aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
                if aspect_ratio > 5:
                    continue
                
                # 🎯 KONTROLA PRE-DETECTION POLYGONŮ
                if self.coord_system.is_in_predetection_area(center_x, center_y):
                    world_pos = self.coord_system.pixel_to_world(center_x, center_y)
                    
                    detections.append({
                        'bbox': (x, y, w, h),
                        'center': (center_x, center_y),
                        'world_pos': world_pos,
                        'area': area,
                        'aspect_ratio': aspect_ratio
                    })
        
        return detections, fg_mask
