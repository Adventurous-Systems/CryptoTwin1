"""
TopologicPy data model wrappers that preserve IFC metadata and respect the Topology hierarchy.

Based on TopologicPy documentation analysis:
- Topology Hierarchy: Vertex → Edge → Face → Shell → Cell → CellComplex
- Dictionary System: Key-value metadata attached to vertices/edges preserving IFC attributes
- Graph Class: Creates graphs from IFC files with transferDictionaries=True
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import uuid
import time


class TopologicVertex(BaseModel):
    """
    TopologicPy Vertex wrapper preserving IFC metadata via Dictionary system.
    
    Vertices are fundamental geometric elements with 3D coordinates and attached dictionaries
    containing IFC entity information like type, GUID, and properties.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    coordinates: Tuple[float, float, float]
    dictionaries: Dict[str, Any] = Field(default_factory=dict)
    
    # IFC-specific metadata extracted from dictionaries
    ifc_type: Optional[str] = None
    ifc_guid: Optional[str] = None
    ifc_name: Optional[str] = None
    
    def extract_ifc_metadata(self) -> None:
        """Extract common IFC metadata from dictionaries for easier access"""
        # Common IFC type keys from graph_topo.py analysis
        type_keys = ["IFC_type", "ifc_type", "IFCType", "type", "Entity"]
        for key in type_keys:
            if key in self.dictionaries:
                self.ifc_type = self.dictionaries[key]
                break
                
        # Common IFC GUID keys  
        guid_keys = ["IFC_global_id", "ifc_guid", "IFCGuid", "IFC_GUID", "GlobalId", "guid"]
        for key in guid_keys:
            if key in self.dictionaries:
                self.ifc_guid = self.dictionaries[key]
                break
                
        # Name variations
        name_keys = ["Name", "name", "IFC_name"]
        for key in name_keys:
            if key in self.dictionaries:
                self.ifc_name = self.dictionaries[key]
                break


class TopologicEdge(BaseModel):
    """
    TopologicPy Edge wrapper representing connections between vertices.
    
    Edges maintain relationships between vertices and preserve IFC relationship metadata
    like spatial connections, adjacencies, and containment relationships.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_vertex_id: str
    end_vertex_id: str
    dictionaries: Dict[str, Any] = Field(default_factory=dict)
    
    # Edge-specific metadata
    edge_type: Optional[str] = None
    connection_type: Optional[str] = None
    shared_geometry: Optional[str] = None
    
    def extract_connection_metadata(self) -> None:
        """Extract connection-specific metadata from dictionaries"""
        if "connection_type" in self.dictionaries:
            self.connection_type = self.dictionaries["connection_type"]
        if "edge_type" in self.dictionaries:
            self.edge_type = self.dictionaries["edge_type"]
        if "shared_geometry" in self.dictionaries:
            self.shared_geometry = self.dictionaries["shared_geometry"]


class TopologicGraph(BaseModel):
    """
    Complete TopologicPy Graph representation with vertices, edges, and metadata.

    This model preserves the full graph structure from TopologicPy with all IFC metadata
    intact, ready for storage in Kuzu database and visualization in Streamlit.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vertices: List[TopologicVertex] = Field(default_factory=list)
    edges: List[TopologicEdge] = Field(default_factory=list)

    # File and building context
    file_id: Optional[str] = None
    building_id: Optional[str] = None
    source_file: Optional[str] = None
    filename: Optional[str] = None
    building_name: Optional[str] = None

    # Graph-level metadata
    ifc_file_info: Dict[str, Any] = Field(default_factory=dict)
    processing_method: Optional[str] = None
    creation_timestamp: Optional[str] = None

    # Statistics
    vertex_count: int = 0
    edge_count: int = 0
    ifc_type_counts: Dict[str, int] = Field(default_factory=dict)
    
    def update_statistics(self) -> None:
        """Update graph statistics based on current vertices and edges"""
        self.vertex_count = len(self.vertices)
        self.edge_count = len(self.edges)
        
        # Count IFC types
        type_counts = {}
        for vertex in self.vertices:
            if vertex.ifc_type:
                type_counts[vertex.ifc_type] = type_counts.get(vertex.ifc_type, 0) + 1
        self.ifc_type_counts = type_counts
    
    def get_vertices_by_type(self, ifc_type: str) -> List[TopologicVertex]:
        """Get all vertices of a specific IFC type"""
        return [v for v in self.vertices if v.ifc_type == ifc_type]
    
    def get_vertex_by_id(self, vertex_id: str) -> Optional[TopologicVertex]:
        """Get vertex by ID"""
        return next((v for v in self.vertices if v.id == vertex_id), None)
    
    def get_edges_for_vertex(self, vertex_id: str) -> List[TopologicEdge]:
        """Get all edges connected to a specific vertex"""
        return [e for e in self.edges if e.start_vertex_id == vertex_id or e.end_vertex_id == vertex_id]


class IFCProcessingContext(BaseModel):
    """
    Context information for IFC processing operations.
    
    Maintains state and configuration during the IFC → TopologicPy → Kuzu pipeline.
    """
    file_path: str
    method: str = "direct"
    include_types: List[str] = Field(default_factory=list)
    transfer_dictionaries: bool = True
    tolerance: float = 0.001
    
    # Processing state
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_status: str = "pending"
    error_messages: List[str] = Field(default_factory=list)
    
    # Fallback tracking
    attempted_methods: List[str] = Field(default_factory=list)
    current_method: Optional[str] = None

    # Store original TopologicPy Graph for visualization
    original_topologic_graph: Optional[Any] = None
    
    def add_error(self, message: str) -> None:
        """Add error message to context"""
        self.error_messages.append(message)
    
    def start_processing(self) -> None:
        """Mark processing start"""
        self.start_time = time.time()
        self.current_status = "processing"
    
    def complete_processing(self, success: bool = True) -> None:
        """Mark processing completion"""
        self.end_time = time.time()
        self.current_status = "completed" if success else "failed"
    
    @property
    def processing_time(self) -> float:
        """Get processing time in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0