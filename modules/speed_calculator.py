# modules/speed_calculator.py

import time
import numpy as np

class SpeedCalculator:
    def __init__(self, coordinate_system):
        self.coord_system = coordinate_system
        
        # State machine pro měření
        self.state = 'IDLE'  # IDLE, MEASURING, MEASURED
        
        # Data aktuálního vozidla
        self.current_vehicle = {
            'first_line': None,
            'first_time': None,
            'first_world_pos': None,
            'second_line': None,
            'second_time': None,
            'second_world_pos': None
        }
        
        # Statistiky
        self.vehicle_count = 0
        self.speed_limit_kmh = 50
        self.max_reasonable_speed = 80
        
        # Anti-bounce - aby se jeden crossing nezapočítal 2x
        self.last_crossing_time = 0
        self.crossing_cooldown = 0.3  # 300ms mezi crossingy
        
    def update_position(self, center_pixel, timestamp):
        world_pos = self.coord_system.pixel_to_world(center_pixel[0], center_pixel[1])
        
        # Kontrola trigger lines
        trigger_line = self.coord_system.which_trigger_line_crossed(
            center_pixel[0], center_pixel[1], threshold=40
        )
        
        if trigger_line:
            # Anti-bounce: ignoruj další crossingy po dobu cooldownu
            if timestamp - self.last_crossing_time < self.crossing_cooldown:
                return None
            
            self.last_crossing_time = timestamp
            
            # Zpracování podle stavu
            if self.state == 'IDLE':
                # První crossing - začni měření
                self._start_measurement(trigger_line, timestamp, world_pos)
                
            elif self.state == 'MEASURING':
                # Druhý crossing - pokud je to JINÁ linie
                if trigger_line != self.current_vehicle['first_line']:
                    speed_data = self._finish_measurement(trigger_line, timestamp, world_pos)
                    return speed_data
        
        return None
    
    def _start_measurement(self, trigger_line, timestamp, world_pos):
        self.state = 'MEASURING'
        self.vehicle_count += 1
        
        self.current_vehicle = {
            'first_line': trigger_line,
            'first_time': timestamp,
            'first_world_pos': world_pos,
            'second_line': None,
            'second_time': None,
            'second_world_pos': None
        }
        
        print(f" Vehicle #{self.vehicle_count} crossed {trigger_line.upper()}")
    
    def _finish_measurement(self, trigger_line, timestamp, world_pos):
        self.current_vehicle['second_line'] = trigger_line
        self.current_vehicle['second_time'] = timestamp
        self.current_vehicle['second_world_pos'] = world_pos
        
        print(f" Vehicle #{self.vehicle_count} crossed {trigger_line.upper()}")
        
        # Výpočet rychlosti
        time_diff = self.current_vehicle['second_time'] - self.current_vehicle['first_time']
        
        if time_diff <= 0.1:  # Příliš rychlé - chyba
            self._reset_measurement()
            return None
        
        # Vzdálenost pomocí homografie
        distance = self.coord_system.calculate_distance(
            self.current_vehicle['first_world_pos'],
            self.current_vehicle['second_world_pos']
        )
        
        speed_ms = distance / time_diff
        speed_kmh = speed_ms * 3.6
        
        # Filtr nesmyslných rychlostí
        if speed_kmh > self.max_reasonable_speed or speed_kmh < 5:
            print(f" Unreasonable speed {speed_kmh:.1f} km/h - ignored")
            self._reset_measurement()
            return None
        
        # Směr
        if self.current_vehicle['first_line'] == 'start_line':
            direction = '→'  # START → END
        else:
            direction = '←'  # END → START
        
        #  HLAVNÍ VÝPIS RYCHLOSTI
        print(f"\n{'='*60}")
        print(f" Vehicle #{self.vehicle_count}: {speed_kmh:.1f} km/h {direction}")
        print(f"   Route: {self.current_vehicle['first_line']} → {self.current_vehicle['second_line']}")
        print(f"   Time: {time_diff:.2f}s")
        print(f"   Distance: {distance:.2f}m")
        if speed_kmh > self.speed_limit_kmh:
            print(f"    SPEEDING! (limit: {self.speed_limit_kmh} km/h)")
        print(f"{'='*60}\n")
        
        speed_data = {
            'vehicle_number': self.vehicle_count,
            'speed_kmh': speed_kmh,
            'speed_ms': speed_ms,
            'distance_m': distance,
            'time_s': time_diff,
            'direction': direction,
            'is_speeding': speed_kmh > self.speed_limit_kmh
        }
        
        # Reset pro další vozidlo
        self._reset_measurement()
        
        return speed_data
    
    def _reset_measurement(self):
        self.state = 'IDLE'
        self.current_vehicle = {
            'first_line': None,
            'first_time': None,
            'first_world_pos': None,
            'second_line': None,
            'second_time': None,
            'second_world_pos': None
        }
    
    def get_state(self):
        return self.state
    
    def get_vehicle_count(self):
        """Vrátí počet změřených vozidel"""
        return self.vehicle_count
