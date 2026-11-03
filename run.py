#!/usr/bin/env python3
"""
Quick start script for Criminal Network Analysis System
Run: python run.py
"""
import os
import sys

# Generate data if needed
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

if not os.path.exists(os.path.join(DATA_DIR, "persons.json")):
    print("=" * 55)
    print("  Generating synthetic criminal network dataset...")
    print("=" * 55)
    sys.path.insert(0, DATA_DIR)
    import generate_dataset
    generate_dataset.main(DATA_DIR)
    print()

# Launch Flask app
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from app import app
print("=" * 55)
print("  AI-Powered Criminal Network Analysis System")
print("  SIH26189 — Ministry of Home Affairs, India")
print("=" * 55)
print("  Open your browser at: http://127.0.0.1:5000")
print("=" * 55)
app.run(debug=False, host="127.0.0.1", port=5000)
