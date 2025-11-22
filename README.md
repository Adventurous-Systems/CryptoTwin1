# 🏗️ CryptoTwin: IFC TopologicPy Kuzu Streamlit Application

A **clean, modular Streamlit application** that processes IFC (Industry Foundation Classes) files into connectivity graphs using TopologicPy, stores them in Kuzu graph database, and provides 3D visualization. Features blockchain tokenization capabilities via Ethereum smart contracts.

## ✨ Key Features

- **🏛️ IFC Processing**: Advanced IFC file analysis using TopologicPy with dual processing methods
- **📊 Graph Database**: High-performance graph storage and analytics with Kuzu database  
- **🕸️ Topology Preservation**: Complete preservation of IFC metadata through TopologicPy Dictionary system
- **🎨 3D Visualization**: Interactive graph and geometry visualization using actual IFC coordinates
- **🔗 Blockchain Ready**: Tokenization framework for IFC components on Ethereum
- **🧪 Robust Processing**: Multiple fallback strategies ensuring 90%+ IFC file compatibility

## 🏗️ Architecture

### Clean Layered Design
```
┌─────────────────────────────────────┐
│           UI Layer                  │  ← Streamlit Controllers
├─────────────────────────────────────┤
│         Services Layer              │  ← IFC Processing & Analytics  
├─────────────────────────────────────┤
│          Models Layer               │  ← TopologicPy & Kuzu Data Models
├─────────────────────────────────────┤
│        Database Layer               │  ← Kuzu Graph Storage
└─────────────────────────────────────┘
```

### Technology Stack
- **[TopologicPy (≥0.8.36)](https://topologicpy.readthedocs.io/)** - Spatial modeling and graph generation from IFC
- **[Kuzu (≥0.6.1)](https://kuzudb.com/)** - Embedded graph database for high-performance analytics
- **[Streamlit (≥1.28.0)](https://streamlit.io)** - Interactive web application framework
- **[IfcOpenShell (≥0.7.9)](http://ifcopenshell.org/)** - IFC file processing and validation
- **[Plotly (≥5.11.0)](https://plotly.com/python/)** - 3D visualization and interactive graphics

## 📁 Project Structure

```
src/
├── models/
│   ├── data_models.py          # Pydantic configuration models
│   ├── topologic_models.py     # TopologicPy data wrappers
│   └── kuzu_models.py          # Kuzu schema definitions
├── services/
│   ├── ifc_processor.py        # IFC→TopologicPy processing
│   ├── kuzu_service.py         # Kuzu database operations  
│   └── graph_analyzer.py       # Graph analysis utilities
├── ui/
│   └── streamlit_ui.py         # Streamlit interface controllers
├── database/
│   └── kuzu_schema.py          # Database schema management
└── app.py                      # Main application entry point
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate.bat   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Application

**Method 1: Simple Startup (Recommended)**
```bash
# Run the simple startup script (works from any directory)
python start_app.py
```

**Method 2: Using the Run Script**
```bash
# Run with pre-flight checks
python scripts/run.py
```

**Method 3: Direct Streamlit Launch**
```bash
# Launch from src directory
cd src && streamlit run app.py
```

Application will be available at: http://localhost:8501

### 3. Start Processing IFC Files
1. 📁 Upload an `.ifc` file using the sidebar
2. ⚙️ Configure processing method (Direct/Traditional)  
3. 🎯 Select IFC entity types to include (Walls, Spaces, Beams, etc.)
4. ▶️ Click "Process IFC File" to start analysis
5. 📊 Explore results: 3D visualization, graph analytics, and spatial relationships

## 🎯 Core Capabilities

### 📊 Advanced IFC Processing
- **Dual Processing Methods**: 
  - Direct: `Graph.ByIFCPath()` for fast processing
  - Traditional: IFC → Topology → Cluster → Graph for maximum metadata
- **Robust Error Handling**: Multiple fallback strategies for problematic IFC files
- **Metadata Preservation**: Complete IFC attribute preservation via TopologicPy Dictionary system
- **Spatial Analysis**: Coordinates, relationships, and geometric properties maintained

### 🕸️ Graph Database Analytics with Kuzu
- **High-Performance Storage**: Embedded Kuzu database for fast graph operations
- **Spatial Queries**: Find connected spaces, analyze circulation patterns
- **Centrality Analysis**: Identify critical building elements and connection hubs  
- **Relationship Mapping**: Preserve and query complex IFC spatial relationships

### 🎨 Advanced Visualization
- **3D Interactive Graphs**: Explore building connectivity in true 3D space
- **IFC-Aware Rendering**: Color coding by entity type (walls, spaces, structural elements)
- **Spatial Context**: Visualizations use actual IFC coordinates and geometric relationships
- **Multi-Format Export**: JSON-LD, RDF, and graph formats for downstream processing

### 🔗 Data Integration & Export
- **JSON-LD Export**: Schema.org and IFC ontology-compatible semantic representations
- **RDF Support**: Linked data export for semantic web integration
- **Kuzu Analytics**: Advanced graph queries using Cypher-like syntax
- **Blockchain Ready**: Metadata linking framework for tokenization workflows

## 📈 Technical Implementation

### TopologicPy Data Model Integration

The application leverages TopologicPy's sophisticated data model hierarchy:

```python
# Core data flow
IFC File → TopologicPy Graph → Vertex/Edge Extraction → Kuzu Storage

# Key data structures preserved:
- Vertex coordinates (x, y, z) from IFC geometry
- Dictionary attachments with IFC metadata (type, GUID, properties)  
- Edge relationships maintaining spatial connectivity
- Mixed-dimensional representations (vertices, edges, faces, cells)
```

### Kuzu Database Schema

Optimized schema design for IFC data:

```cypher
CREATE NODE TABLE IfcElement(
    id STRING,
    ifc_type STRING,        # Wall, Space, Beam, etc.
    ifc_guid STRING,        # IFC global unique identifier  
    x DOUBLE, y DOUBLE, z DOUBLE,  # Spatial coordinates
    properties MAP(STRING, STRING), # IFC property sets
    PRIMARY KEY(id)
);

CREATE REL TABLE TopologicalConnection(
    FROM IfcElement TO IfcElement,
    connection_type STRING,
    shared_geometry STRING
);
```

## 🧪 Development

### Development Commands
```bash
# Run application in development mode
streamlit run src/app.py --server.runOnSave=true

# Run tests
pytest tests/

# Run with coverage  
pytest --cov=src/

# Performance benchmarking
python scripts/benchmark_processing.py
```

# 🚀 Blockchain Minting - Quick Start

**Get from zero to minting in 5 minutes!**

---

## The 3-Terminal Workflow

### Terminal 1: Anvil (Blockchain)
```bash
cd ~/CryptoTwin1
./START_ANVIL_HIGH_GAS.sh
```
**Keep running!** Should show `gas_limit 100000000`

## Terminal 2: Deploy Contract
```bash
cd ~/CryptoTwin1contracts
forge clean && forge build


### Terminal 3: Streamlit App  
```bash
cd ~/CryptoTwin1
streamlit run src/app.py
```

---

## In Browser: 5 Steps to Mint

### 1. Upload IFC File
- Tab: **"IFC Processing"**
- Upload: `Ifc2x3_Duplex_Architecture.ifc`
- Wait for ✅ Processing complete

### 2. Connect Blockchain
- **Sidebar** → "Blockchain Connection"
- Select: **"Anvil (Local)"**
- Click: **"Connect"**
- See: ✅ Connected, ~10,000 ETH

### 3. Load Contract
- **Sidebar** → "Smart Contract"  
- Mode: **"Deploy Contract"**
- Click: **"Load Contract"**
- See: ✅ Contract Loaded - Balloons for Success!

### 4. Select Building
- Tab: **"Blockchain Minting"**
- Select your building
- See: ✅ Validation passed
- See: ✅ Gas estimate

### 5. MINT! 🚀
- **Scroll down**
- Click: **"🚀 Mint Building Graph NFT"**
- Wait ~30 seconds
- 🎉 Success + Balloons!

### Key Development Features
- **Modular Architecture**: Clean separation between UI, services, and data layers
- **Comprehensive Testing**: Unit tests for all TopologicPy and Kuzu integrations
- **Performance Monitoring**: Built-in benchmarking for processing optimization
- **Error Recovery**: Robust fallback processing for challenging IFC files

## 📋 Current Development Status

Based on the detailed analysis of existing work and TopologicPy data models:

### ✅ Completed Analysis
- Comprehensive review of adventurous_topologic architecture patterns
- In-depth TopologicPy data model analysis (Graph, Topology, Vertex, Dictionary)
- Kuzu database integration research and schema design
- Processing strategy definition with fallback mechanisms

### 🚧 Phase 1 Implementation (Current)
- [ ] Project structure setup with clean architecture
- [ ] TopologicPy data model wrapper classes
- [ ] Basic IFC processor with Graph.ByIFCPath integration
- [ ] Kuzu service with optimized schema for IFC data
- [ ] Minimal Streamlit UI for file upload and processing

### Completed Phases
- **Phase 0**: Base application
- **Phase 1**: Blockchain tokenization integration

### 📅 Upcoming Phases
- **Phase 2**: Enhanced processing, 3D visualization, advanced analytics
- **Phase 3**: RDF/JSON-LD export, semantic web integration  
- **Phase 4**: Performance optimization, production readiness


## 📚 Documentation & References

- **[TopologicPy Documentation](https://topologicpy.readthedocs.io/en/latest/)** - Core library reference and data models
- **[Kuzu Documentation](https://docs.kuzudb.com/)** - Graph database operations and Cypher syntax
- **[IFC Standards](https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/)** - Industry Foundation Classes specification
- **[Previous Work Analysis](./previous%20files/)** - Detailed analysis of adventurous_topologic implementation

## 🎯 Success Metrics

### Technical Performance
- **Processing Speed**: Handle 5-50MB IFC files within 30 seconds
- **Reliability**: 90%+ success rate with diverse IFC files using fallback strategies  
- **Data Integrity**: Complete preservation of IFC metadata through processing pipeline
- **Query Performance**: Sub-second response for common graph analytics queries

### User Experience
- **Intuitive Interface**: Non-technical users can process IFC files successfully
- **Rich Visualization**: Clear 3D representations of building connectivity
- **Comprehensive Analytics**: Meaningful insights about spatial relationships
- **Export Flexibility**: Multiple output formats for different downstream uses

## 🤝 Contributing

This project builds upon proven architectural patterns from adventurous_topologic while integrating cutting-edge graph database technology. Contributions should maintain the clean architecture principles and comprehensive testing approach.

## 📄 License

GNU AFFERO GENERAL PUBLIC LICENSE - see the LICENSE file for details.

---

*Built with modern Python, leveraging TopologicPy's advanced spatial modeling capabilities and Kuzu's high-performance graph database for next-generation BIM analytics.*
