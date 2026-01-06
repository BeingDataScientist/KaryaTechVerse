"""
SQLite database module for storing tracking events.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
import threading


class TrackingDatabase:
    """
    SQLite database for storing person tracking events.
    """
    
    def __init__(self, db_path: str = "tracking_events.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _get_connection(self):
        """Get a database connection with proper settings for concurrent access."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        # Enable WAL mode for better concurrent access
        conn.execute('PRAGMA journal_mode=WAL')
        # Set busy timeout
        conn.execute('PRAGMA busy_timeout=10000')
        return conn
    
    def _init_database(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create persons table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS persons (
                person_id INTEGER PRIMARY KEY,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP
            )
        ''')
        
        # Create sitting_events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sitting_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                FOREIGN KEY (person_id) REFERENCES persons(person_id)
            )
        ''')
        
        # Create phone_usage_events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                event_number INTEGER,
                FOREIGN KEY (person_id) REFERENCES persons(person_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")
    
    def add_person(self, person_id: int, timestamp: datetime):
        """
        Add or update a person record.
        
        Args:
            person_id: Person tracking ID
            timestamp: Current timestamp
        """
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Check if person exists
                cursor.execute('SELECT person_id FROM persons WHERE person_id = ?', (person_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update last_seen
                    cursor.execute('''
                        UPDATE persons SET last_seen = ? WHERE person_id = ?
                    ''', (timestamp, person_id))
                else:
                    # Insert new person
                    cursor.execute('''
                        INSERT INTO persons (person_id, first_seen, last_seen)
                        VALUES (?, ?, ?)
                    ''', (person_id, timestamp, timestamp))
                
                conn.commit()
                conn.close()
        except sqlite3.OperationalError as e:
            # Retry once if database is locked
            if "locked" in str(e).lower():
                import time
                time.sleep(0.1)
                try:
                    with self.lock:
                        conn = self._get_connection()
                        cursor = conn.cursor()
                        cursor.execute('SELECT person_id FROM persons WHERE person_id = ?', (person_id,))
                        exists = cursor.fetchone()
                        if exists:
                            cursor.execute('UPDATE persons SET last_seen = ? WHERE person_id = ?', 
                                         (timestamp, person_id))
                        else:
                            cursor.execute('INSERT INTO persons (person_id, first_seen, last_seen) VALUES (?, ?, ?)',
                                         (person_id, timestamp, timestamp))
                        conn.commit()
                        conn.close()
                except:
                    pass  # Silently fail if still locked (non-critical operation)
    
    def add_sitting_event(self, event: Dict):
        """
        Add a sitting event to database.
        
        Args:
            event: Event dictionary with keys: person_id, start_time, end_time, duration
        """
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Only save completed events (with end_time)
                if event.get('end_time') and event.get('duration') is not None:
                    cursor.execute('''
                        INSERT INTO sitting_events (person_id, start_time, end_time, duration)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        event['person_id'],
                        event['start_time'],
                        event['end_time'],
                        event['duration']
                    ))
                    
                    # Update person's last_seen (without lock to avoid deadlock)
                    try:
                        self.add_person(event['person_id'], event['end_time'])
                    except:
                        pass
                
                conn.commit()
                conn.close()
        except sqlite3.OperationalError:
            pass  # Silently fail if locked (will retry on next event)
    
    def add_phone_usage_event(self, event: Dict, event_number: int):
        """
        Add a phone usage event to database.
        
        Args:
            event: Event dictionary with keys: person_id, start_time, end_time, duration
            event_number: Sequential event number for this person
        """
        try:
            with self.lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Only save completed events (with end_time)
                if event.get('end_time') and event.get('duration') is not None:
                    cursor.execute('''
                        INSERT INTO phone_usage_events (person_id, start_time, end_time, duration, event_number)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        event['person_id'],
                        event['start_time'],
                        event['end_time'],
                        event['duration'],
                        event_number
                    ))
                    
                    # Update person's last_seen (without lock to avoid deadlock)
                    try:
                        self.add_person(event['person_id'], event['end_time'])
                    except:
                        pass
                
                conn.commit()
                conn.close()
        except sqlite3.OperationalError:
            pass  # Silently fail if locked (will retry on next event)
    
    def get_sitting_stats(self, person_id: Optional[int] = None) -> List[Dict]:
        """
        Get sitting statistics.
        
        Args:
            person_id: Optional person ID to filter by
            
        Returns:
            List of dictionaries with sitting statistics
        """
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if person_id:
                cursor.execute('''
                    SELECT person_id, SUM(duration) as total_duration, COUNT(*) as event_count
                    FROM sitting_events
                    WHERE person_id = ?
                    GROUP BY person_id
                ''', (person_id,))
            else:
                cursor.execute('''
                    SELECT person_id, SUM(duration) as total_duration, COUNT(*) as event_count
                    FROM sitting_events
                    GROUP BY person_id
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            stats = []
            for row in results:
                stats.append({
                    'person_id': row[0],
                    'total_duration': row[1] or 0.0,
                    'event_count': row[2] or 0
                })
            
            return stats
    
    def get_phone_usage_stats(self, person_id: Optional[int] = None) -> List[Dict]:
        """
        Get phone usage statistics.
        
        Args:
            person_id: Optional person ID to filter by
            
        Returns:
            List of dictionaries with phone usage statistics
        """
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if person_id:
                cursor.execute('''
                    SELECT person_id, SUM(duration) as total_duration, COUNT(*) as event_count
                    FROM phone_usage_events
                    WHERE person_id = ?
                    GROUP BY person_id
                ''', (person_id,))
            else:
                cursor.execute('''
                    SELECT person_id, SUM(duration) as total_duration, COUNT(*) as event_count
                    FROM phone_usage_events
                    GROUP BY person_id
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            stats = []
            for row in results:
                stats.append({
                    'person_id': row[0],
                    'total_duration': row[1] or 0.0,
                    'event_count': row[2] or 0
                })
            
            return stats
    
    def get_phone_usage_timeline(self, person_id: Optional[int] = None, 
                                 limit: int = 100) -> List[Dict]:
        """
        Get phone usage timeline data.
        
        Args:
            person_id: Optional person ID to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of phone usage events with timestamps
        """
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if person_id:
                cursor.execute('''
                    SELECT person_id, start_time, end_time, duration
                    FROM phone_usage_events
                    WHERE person_id = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                ''', (person_id, limit))
            else:
                cursor.execute('''
                    SELECT person_id, start_time, end_time, duration
                    FROM phone_usage_events
                    ORDER BY start_time DESC
                    LIMIT ?
                ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            events = []
            for row in results:
                events.append({
                    'person_id': row[0],
                    'start_time': row[1],
                    'end_time': row[2],
                    'duration': row[3]
                })
            
            return events
    
    def get_all_persons(self) -> List[Dict]:
        """Get all persons in database."""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT person_id, first_seen, last_seen
                FROM persons
                ORDER BY person_id
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            persons = []
            for row in results:
                persons.append({
                    'person_id': row[0],
                    'first_seen': row[1],
                    'last_seen': row[2]
                })
            
            return persons
    
    def clear_database(self):
        """Clear all data from database (for testing/reset)."""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM sitting_events')
            cursor.execute('DELETE FROM phone_usage_events')
            cursor.execute('DELETE FROM persons')
            
            conn.commit()
            conn.close()
            print("Database cleared")

