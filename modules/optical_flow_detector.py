# modules/optical_flow_detector.py

import cv2
import numpy as np

class OpticalFlowDetector:
    def __init__(self, coordinate_system):
        """Optical flow based vehicle detector - ignoruje statické objekty"""
        self.coord_system = coordinate_system
        
        # Optical flow parameters
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        # Feature detection parameters
        self.feature_params = dict(
            maxCorners=200,
            qualityLevel=0.01,
            minDistance=10,
            blockSize=7
        )
        
        # Tracking state
        self.prev_gray = None
        self.prev_points = None
        
        # Motion threshold (pixels/frame)
        self.motion_threshold = 2.0
        
        # Detection area
        self.min_area = 3000
        self.max_area = 40000
        
        print("✓ Optical Flow Detector initialized")
    
    def detect_moving_vehicles(self, frame):
        """Detekuje pouze POHYBUJÍCÍ SE vozidla pomocí optical flow"""
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # První frame - inicializace
        if self.prev_gray is None:
            self.prev_gray = gray
            self.prev_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
            return [], np.zeros_like(gray)
        
        # Najdi nové feature pointy
        curr_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
        
        if curr_points is None or len(curr_points) == 0:
            self.prev_gray = gray
            return [], np.zeros_like(gray)
        
        # Spočítej optical flow
        next_points, status, error = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, curr_points, None, **self.lk_params
        )
        
        if next_points is None:
            self.prev_gray = gray
            return [], np.zeros_like(gray)
        
        # Vytvoř motion magnitude mapu
        motion_magnitude = np.zeros_like(gray, dtype=np.float32)
        
        good_old = curr_points[status == 1]
        good_new = next_points[status == 1]
        
        for i, (new, old) in enumerate(zip(good_new, good_old)):
            a, b = new.ravel()
            c, d = old.ravel()
            
            # Vypočítej magnitude pohybu
            magnitude = np.sqrt((a - c)**2 + (b - d)**2)
            
            # Zakresli do motion mapy pouze pokud je pohyb větší než threshold
            if magnitude > self.motion_threshold:
                # 🎯 OPRAVA: Použij int() pro magnitude
                cv2.circle(motion_magnitude, (int(a), int(b)), 15, int(magnitude * 10), -1)
        
        # Threshold a morfologické operace
        motion_mask = (motion_magnitude > (self.motion_threshold * 10)).astype(np.uint8) * 255
        
        # Morfologické operace pro spojení blízkých pohybů
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, 
                                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        
        # Najdi contours pohybujících se oblastí
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if self.min_area < area < self.max_area:
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
                
                # Kontrola pre-detection oblasti
                if self.coord_system.is_in_predetection_area(center_x, center_y):
                    world_pos = self.coord_system.pixel_to_world(center_x, center_y)
                    
                    # Vypočítej průměrnou rychlost pohybu v této oblasti
                    mask_roi = motion_mask[y:y+h, x:x+w]
                    if np.sum(mask_roi > 0) > 0:
                        avg_motion = np.mean(motion_magnitude[y:y+h, x:x+w][mask_roi > 0]) / 10.0
                    else:
                        avg_motion = 0.0
                    
                    detections.append({
                        'bbox': (x, y, w, h),
                        'center': (center_x, center_y),
                        'world_pos': world_pos,
                        'area': area,
                        'motion_magnitude': avg_motion
                    })
        
        # Update pro další frame
        self.prev_gray = gray
        self.prev_points = curr_points
        
        return detections, motion_mask
