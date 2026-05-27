#!/bin/bash
# Setup script for LMS to Pixoo64 service

echo "================================================"
echo "LMS to Pixoo64 - Setup Script"
echo "================================================"
echo ""

# Create virtual environment
echo "[1/3] Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "[2/3] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "[3/3] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "================================================"
echo "✓ Setup complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Test Pixoo64 connection:"
echo "   source venv/bin/activate"
echo "   python test_pixoo.py"
echo ""
echo "2. Test LMS connection:"
echo "   source venv/bin/activate"
echo "   python test_lms.py"
echo ""
echo "3. Run the full service:"
echo "   source venv/bin/activate"
echo "   python lms_pixoo_service.py"
echo ""
echo "To deactivate virtual environment: deactivate"
echo "================================================"
