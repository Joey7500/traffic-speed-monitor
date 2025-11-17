# config/settings.py
CAMERA_SETTINGS = {
    'fps': 30,
    'resolution': (2304, 1296),
    'buffer_size': 450  # 3 sekundy při 50 FPS
}

DETECTION_SETTINGS = {
    'min_vehicle_area': 3000,        # Menší pro 45° úhel
    'max_vehicle_area':25000,      # Maximum filtr
    'max_tracking_distance': 120,   # Větší kvůli rychlosti
    'speed_limit_kmh': 30,         # Český limit v obci
    'max_reasonable_speed': 45,    # Filtr nesmyslů
}

COORDINATE_SETTINGS = {
    'road_width_m': 5.4,
    'road_length_m': 12.0,
    'trigger_threshold': 40,       # Pixely od trigger line
}

# Kalibrace trigger lines
TRIGGER_LINES = {
    'A1': (459, 911),   # Start line point 1
    'B1': (510, 1185),  # Start line point 2
    'A13': (1147, 665), # End line point 1  
    'B13': (1378, 763), # End line point 2
}
