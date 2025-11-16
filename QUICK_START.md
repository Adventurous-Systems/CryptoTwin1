# 🚀 Quick Start Guide

## Getting Started in 3 Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Application
```bash
python start_app.py
```

The application will open in your browser at http://localhost:8501

### 3. Test the Application

**Without IFC Files (Mock Data Testing):**
1. Run the test script to verify everything works:
```bash
python scripts/test_pipeline.py
```

**With IFC Files:**
1. Upload an IFC file using the sidebar
2. Configure processing options:
   - Processing Method: Direct (recommended) or Traditional
   - Transfer Dictionaries: Keep checked to preserve IFC metadata
   - IFC Entity Types: Optionally filter specific building elements
3. Click "Process IFC File"
4. View results in the 3D visualization and data tables

## What You'll See

### Dashboard Features
- **Processing Status**: Real-time updates during IFC processing
- **Database Statistics**: Current vertex/edge counts and IFC types
- **Configuration Panel**: Processing options and file upload
- **3D Visualization**: Interactive graph of building elements
- **Data Tables**: Detailed vertex information with coordinates

### Expected Processing Flow
1. **File Upload** → IFC file validation
2. **TopologicPy Processing** → Graph extraction with multiple fallback strategies  
3. **Kuzu Storage** → High-performance graph database storage
4. **Visualization** → 3D interactive display with IFC coordinates

## Troubleshooting

### Missing Dependencies
If you see missing package warnings:
```bash
# Install optional packages for full functionality
pip install topologicpy kuzu ifcopenshell

# Or continue with limited functionality (mock data only)
```

### Import Errors
Make sure you're running from the project root:
```bash
# Correct
python start_app.py

# Or from src directory
cd src && streamlit run app.py
```

### No IFC Files?
The application works without real IFC files:
- Database statistics show current state
- Test script creates mock building data
- All functionality can be verified with generated data

## Architecture Overview

```
IFC File → TopologicPy → Kuzu DB → Streamlit UI
     ↓           ↓          ↓          ↓
  Validation   Graph    Storage   Visualization
             Extraction
```

**Data Flow:**
- IFC entities → TopologicPy vertices with dictionaries
- Spatial relationships → Graph edges with metadata  
- Complete graph → Kuzu database with spatial indexing
- Database queries → 3D visualization with coordinates

## Next Steps

Once you have the basic application running:
1. Try processing different IFC files
2. Explore the 3D visualization controls
3. Check the database statistics for different file types
4. Review TASKS.md for Phase 2 development (advanced features)

---

**Need Help?** Check the full README.md for detailed documentation and troubleshooting.