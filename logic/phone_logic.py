"""
Logic for detecting and tracking phone usage events.
"""

import time
from typing import Dict, Optional, List
from datetime import datetime


class PhoneUsageTracker:
    """
    Tracks phone usage events for each person.
    """
    
    def __init__(self, look_down_threshold: float = -15.0):
        """
        Initialize phone usage tracker.
        
        Args:
            look_down_threshold: Head angle threshold for looking down (degrees)
        """
        self.look_down_threshold = look_down_threshold
        # Store current state for each person
        self.person_states = {}
        
    def update(self, person_id: int, has_phone_nearby: bool, is_looking_down: bool,
              timestamp: datetime) -> Optional[Dict]:
        """
        Update phone usage state for a person.
        
        Args:
            person_id: Person tracking ID
            has_phone_nearby: Whether phone detected near person
            is_looking_down: Whether person is looking down
            timestamp: Current timestamp
            
        Returns:
            Event dictionary if state changed, None otherwise
            Format: {'event_type': 'phone_start'/'phone_end', 'person_id': int,
                    'start_time': datetime, 'end_time': datetime, 'duration': float}
        """
        # Determine if person is using phone (phone nearby AND looking down)
        using_phone = has_phone_nearby and is_looking_down
        
        # Initialize state if new person
        if person_id not in self.person_states:
            self.person_states[person_id] = {
                'is_using_phone': False,
                'start_time': None,
                'last_update': timestamp,
                'event_count': 0
            }
        
        state = self.person_states[person_id]
        event = None
        
        # State transition: not using -> using
        if using_phone and not state['is_using_phone']:
            state['is_using_phone'] = True
            state['start_time'] = timestamp
            state['event_count'] += 1
            event = {
                'event_type': 'phone_start',
                'person_id': person_id,
                'start_time': timestamp,
                'end_time': None,
                'duration': None
            }
        
        # State transition: using -> not using
        elif not using_phone and state['is_using_phone']:
            state['is_using_phone'] = False
            if state['start_time']:
                duration = (timestamp - state['start_time']).total_seconds()
                event = {
                    'event_type': 'phone_end',
                    'person_id': person_id,
                    'start_time': state['start_time'],
                    'end_time': timestamp,
                    'duration': duration
                }
            state['start_time'] = None
        
        state['last_update'] = timestamp
        return event
    
    def get_current_phone_duration(self, person_id: int, current_time: datetime) -> float:
        """
        Get current phone usage duration for a person (if currently using).
        
        Args:
            person_id: Person tracking ID
            current_time: Current timestamp
            
        Returns:
            Duration in seconds, or 0 if not using phone
        """
        if person_id not in self.person_states:
            return 0.0
        
        state = self.person_states[person_id]
        if state['is_using_phone'] and state['start_time']:
            return (current_time - state['start_time']).total_seconds()
        return 0.0
    
    def get_phone_event_count(self, person_id: int) -> int:
        """Get total number of phone usage events for a person."""
        if person_id not in self.person_states:
            return 0
        return self.person_states[person_id]['event_count']
    
    def is_currently_using_phone(self, person_id: int) -> bool:
        """Check if person is currently using phone."""
        if person_id not in self.person_states:
            return False
        return self.person_states[person_id]['is_using_phone']
    
    def cleanup_old_persons(self, active_person_ids: list):
        """
        Remove state for persons no longer being tracked.
        
        Args:
            active_person_ids: List of currently active person IDs
        """
        inactive_ids = [pid for pid in self.person_states.keys() 
                       if pid not in active_person_ids]
        for pid in inactive_ids:
            del self.person_states[pid]

