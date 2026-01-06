"""
Logic for detecting and tracking sitting events.
"""

import time
from typing import Dict, Optional, Tuple
from datetime import datetime


class SittingTracker:
    """
    Tracks sitting events for each person.
    """
    
    def __init__(self):
        """Initialize sitting tracker."""
        # Store current state for each person: {person_id: {'is_sitting': bool, 'start_time': datetime, ...}}
        self.person_states = {}
        
    def update(self, person_id: int, is_sitting: bool, has_chair_overlap: bool,
              timestamp: datetime) -> Optional[Dict]:
        """
        Update sitting state for a person.
        
        Args:
            person_id: Person tracking ID
            is_sitting: Whether pose indicates sitting
            has_chair_overlap: Whether person overlaps with chair
            timestamp: Current timestamp
            
        Returns:
            Event dictionary if state changed, None otherwise
            Format: {'event_type': 'sitting_start'/'sitting_end', 'person_id': int, 
                    'start_time': datetime, 'end_time': datetime, 'duration': float}
        """
        # Determine if person is actually sitting (both pose and chair overlap)
        actually_sitting = is_sitting and has_chair_overlap
        
        # Initialize state if new person
        if person_id not in self.person_states:
            self.person_states[person_id] = {
                'is_sitting': False,
                'start_time': None,
                'last_update': timestamp
            }
        
        state = self.person_states[person_id]
        event = None
        
        # State transition: not sitting -> sitting
        if actually_sitting and not state['is_sitting']:
            state['is_sitting'] = True
            state['start_time'] = timestamp
            event = {
                'event_type': 'sitting_start',
                'person_id': person_id,
                'start_time': timestamp,
                'end_time': None,
                'duration': None
            }
        
        # State transition: sitting -> not sitting
        elif not actually_sitting and state['is_sitting']:
            state['is_sitting'] = False
            if state['start_time']:
                duration = (timestamp - state['start_time']).total_seconds()
                event = {
                    'event_type': 'sitting_end',
                    'person_id': person_id,
                    'start_time': state['start_time'],
                    'end_time': timestamp,
                    'duration': duration
                }
            state['start_time'] = None
        
        state['last_update'] = timestamp
        return event
    
    def get_current_sitting_duration(self, person_id: int, current_time: datetime) -> float:
        """
        Get current sitting duration for a person (if currently sitting).
        
        Args:
            person_id: Person tracking ID
            current_time: Current timestamp
            
        Returns:
            Duration in seconds, or 0 if not sitting
        """
        if person_id not in self.person_states:
            return 0.0
        
        state = self.person_states[person_id]
        if state['is_sitting'] and state['start_time']:
            return (current_time - state['start_time']).total_seconds()
        return 0.0
    
    def is_currently_sitting(self, person_id: int) -> bool:
        """Check if person is currently sitting."""
        if person_id not in self.person_states:
            return False
        return self.person_states[person_id]['is_sitting']
    
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

