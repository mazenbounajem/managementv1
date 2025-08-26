import os
import sys
from create_pos_tables import create_pos_tables

def setup_pos_system():
    """Complete setup for POS system"""
    print("Setting up Point of Sale System...")
    
    # Create database tables
    create_pos_tables()
    
    print("✓ POS tables created successfully")
    print("✓ POS system is ready to use")
    print("\nTo launch the POS system:")
    print("1. Run: python pos_launcher.py")
    print("2. Or import pos_launcher and call launch_pos_system()")

if __name__ == "__main__":
    setup_pos_system()
