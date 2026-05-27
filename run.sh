#!/bin/bash
# Quick run script - automatically activates venv and runs the service

# Activate virtual environment
source venv/bin/activate

# Run the service
python lms_pixoo_service.py
