# modules/coordinate_system.py

import cv2
import numpy as np
from pathlib import Path

class CoordinateSystem:
    def __init__(self, homography_file="config/homography_matrix.txt"):
        """Načte homografii a inicializuje souřadnicový systém"""
        self.H = np.loadtxt(homography_file)
        
    
        self.trigger_lines = {
            'start_line': {
                'point1': (300, 750),   # Levý okraj 
                'point2': (600, 1280),  # Pravý okraj 
                'world_y': 0.0
            },
            'end_line': {
                'point1': (900, 570),   # Levý okraj 
                'point2': (1600, 850),  # Pravý okraj 
                'world_y': 12.0
            }
        }
        
        
        self.predetection_polygon_1 = np.array([
            [1653, 582],
            [1480, 532],
            [1146, 666],
            [1386, 759]
        ], dtype=np.int32)
        
        self.predetection_polygon_2 = np.array([
            [304, 965],
            [456, 915],
            [503, 1190],
            [371, 1235]
        ], dtype=np.int32)
        
        # Obdélník pokrývající celou oblast měření
        self.measurement_zone = np.array([
            [300, 750],    # START LINE levý
            [900, 570],    # END LINE levý
            [1600, 850],   # END LINE pravý
            [600, 1280]    # START LINE pravý
        ], dtype=np.int32)
        
        print(f"✓ Loaded homography matrix from {homography_file}")
        print(f"✓ Trigger lines: START & END extended to full road width")
        print(f"✓ Pre-detection: 2 zones | Measurement: 1 zone")
        
    def pixel_to_world(self, pixel_x, pixel_y):
        """Převede pixely na reálné metry pomocí homografie"""
        pixel_pt = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
        world_pt = cv2.perspectiveTransform(pixel_pt, self.H)
        return world_pt[0][0]
        
    def calculate_distance(self, pos1, pos2):
        """Spočítá vzdálenost mezi dvěma body v metrech"""
        return np.sqrt((pos2[0] - pos1[0])**2 + (pos2[1] - pos1[1])**2)
    
    def point_line_distance(self, point, line_point1, line_point2):
        """Vypočítá vzdálenost bodu od přímky"""
        x0, y0 = point
        x1, y1 = line_point1
        x2, y2 = line_point2
        
        A = y2 - y1
        B = x1 - x2  
        C = x2*y1 - x1*y2
        
        distance = abs(A*x0 + B*y0 + C) / np.sqrt(A*A + B*B)
        return distance
    
    def is_near_trigger_line(self, pixel_x, pixel_y, line_name='start_line', threshold=50):
        """Kontrola zda je bod blízko trigger line"""
        line = self.trigger_lines[line_name]
        distance = self.point_line_distance(
            (pixel_x, pixel_y), 
            line['point1'], 
            line['point2']
        )
        return distance < threshold
    
    def which_trigger_line_crossed(self, pixel_x, pixel_y, threshold=50):
        """Vrátí kterou trigger linii vozidlo překročilo"""
        if self.is_near_trigger_line(pixel_x, pixel_y, 'start_line', threshold):
            return 'start_line'
        elif self.is_near_trigger_line(pixel_x, pixel_y, 'end_line', threshold):
            return 'end_line'
        return None
    
    def is_in_predetection_area(self, pixel_x, pixel_y):
        """Kontrola zda je bod v pre-detection zóně"""
        point = (pixel_x, pixel_y)
        
        result1 = cv2.pointPolygonTest(self.predetection_polygon_1, point, False)
        if result1 >= 0:
            return True
        
        result2 = cv2.pointPolygonTest(self.predetection_polygon_2, point, False)
        if result2 >= 0:
            return True
            
        return False
    
    def is_in_measurement_zone(self, pixel_x, pixel_y):
        point = (pixel_x, pixel_y)
        result = cv2.pointPolygonTest(self.measurement_zone, point, False)
        return result >= 0
    
    def get_trigger_line_coordinates(self):
        """Vrátí souřadnice trigger lines"""
        return self.trigger_lines
    
    def get_predetection_polygons(self):
        """Vrátí pre-detection polygony"""
        return [self.predetection_polygon_1, self.predetection_polygon_2]
    
    def get_measurement_zone(self):
        return self.measurement_zone

