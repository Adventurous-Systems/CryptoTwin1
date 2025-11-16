#!/usr/bin/env python3
"""
Run script for IFC TopologicPy Kuzu Streamlit application.

Provides proper startup with environment checking and graceful error handling.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} - OK")
    return True

def check_dependencies():
    """Check if required packages are available"""
    required_packages = [
        'streamlit', 'pydantic', 'plotly', 'pandas'
    ]
    
    optional_packages = [
        ('topologicpy', 'TopologicPy for IFC processing'),
        ('kuzu', 'Kuzu graph database'),
        ('ifcopenshell', 'IFC file support')
    ]
    
    missing_required = []
    missing_optional = []
    
    # Check required packages
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            missing_required.append(package)
            print(f"❌ {package} - MISSING")
    
    # Check optional packages
    for package, description in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            missing_optional.append((package, description))
            print(f"⚠️ {package} - Missing ({description})")
    
    if missing_required:
        print(f"\n❌ Missing required packages: {', '.join(missing_required)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    if missing_optional:
        print(f"\n⚠️ Optional packages missing:")
        for package, description in missing_optional:
            print(f"   - {package}: {description}")
        print("Some functionality may be limited.")
    
    return True

def check_project_structure():
    """Check if project structure is correct"""
    project_root = Path(__file__).parent.parent
    required_paths = [
        "src/app.py",
        "src/models",
        "src/services",
        "requirements.txt"
    ]
    
    for path in required_paths:
        if not (project_root / path).exists():
            print(f"❌ Missing: {path}")
            return False
        print(f"✅ {path} - OK")
    
    return True

def run_application():
    """Run the Streamlit application"""
    project_root = Path(__file__).parent.parent
    app_path = project_root / "src" / "app.py"
    
    print(f"\n🚀 Starting Streamlit application...")
    print(f"App path: {app_path}")
    
    # Change to src directory for proper imports
    os.chdir(project_root / "src")
    
    try:
        # Run Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless", "false",
            "--server.address", "localhost",
            "--server.port", "8501"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start application: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n👋 Application stopped by user")
        return True
    
    return True

def main():
    """Main execution function"""
    print("🏗️ IFC TopologicPy Kuzu Pipeline Launcher")
    print("="*50)
    
    # Run all checks
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n--- {check_name} ---")
        if not check_func():
            all_passed = False
    
    if not all_passed:
        print(f"\n❌ Pre-flight checks failed. Please fix the issues above.")
        return 1
    
    print(f"\n✅ All checks passed!")
    
    # Ask user if they want to continue
    try:
        response = input("\nStart the application? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            run_application()
        else:
            print("👋 Goodbye!")
            return 0
    except KeyboardInterrupt:
        print(f"\n👋 Goodbye!")
        return 0
    
    return 0

if __name__ == "__main__":
    exit(main())