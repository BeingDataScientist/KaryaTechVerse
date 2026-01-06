"""
Script to run the tracking system separately from the dashboard.
"""

from main import BehaviorTrackingSystem

if __name__ == '__main__':
    system = BehaviorTrackingSystem()
    system.run(show_display=True)

