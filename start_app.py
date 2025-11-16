#!/usr/bin/env python3
"""
Simple startup script for the IFC TopologicPy Kuzu Streamlit application.

This script ensures the app runs from the correct directory with proper imports.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the Streamlit application from the correct directory"""
    
    # Get the project root directory (where this script is located)
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    app_file = src_dir / "app.py"
    
    # Verify the app file exists
    if not app_file.exists():
        print(f"❌ Error: {app_file} not found!")
        print(f"Please ensure you're running this from the project root directory.")
        return 1
    
    # Change to the src directory for proper imports
    os.chdir(src_dir)
    
    print("🏗️ Starting IFC TopologicPy Kuzu Pipeline")
    print(f"📁 Working directory: {src_dir}")
    print(f"🚀 Launching Streamlit app...")
    print("-" * 50)
    
    try:
        # Start Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())