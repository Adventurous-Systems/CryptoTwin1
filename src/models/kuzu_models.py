"""
Kuzu database schema definitions for IFC TopologicPy data storage.

Defines the graph database schema optimized for IFC entity relationships,
spatial coordinates, and metadata preservation from TopologicPy processing.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from enum import Enum


class KuzuNodeType(Enum):
    """Kuzu node table types"""
    IFC_FILE = "IfcFile"
    IFC_BUILDING = "IfcBuilding"
    IFC_SPACE = "IfcSpace"
    IFC_ELEMENT = "IfcElement"
    IFC_STOREY = "IfcStorey"


class KuzuRelationType(Enum):
    """Kuzu relationship table types"""
    CONTAINED_IN_FILE = "ContainedInFile"
    CONTAINED_IN_BUILDING = "ContainedInBuilding"
    CONTAINED_IN_SPACE = "ContainedInSpace"
    TOPOLOGICAL_CONNECTION = "TopologicalConnection"
    SPATIAL_CONTAINMENT = "SpatialContainment"


class KuzuIfcFile(BaseModel):
    """Kuzu IFC file tracking model"""
    id: str
    filename: str
    file_path: str
    upload_timestamp: str
    building_name: Optional[str] = None
    file_size_mb: Optional[float] = None
    processing_method: Optional[str] = None

    def to_kuzu_params(self) -> Dict[str, Any]:
        """Convert to Kuzu query parameters"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'upload_timestamp': self.upload_timestamp,
            'building_name': self.building_name or '',
            'file_size_mb': self.file_size_mb or 0.0,
            'processing_method': self.processing_method or ''
        }


class KuzuBuilding(BaseModel):
    """Kuzu building model"""
    id: str
    file_id: str
    ifc_guid: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    properties: Dict[str, str] = {}

    def to_kuzu_params(self) -> Dict[str, Any]:
        """Convert to Kuzu query parameters"""
        return {
            'id': self.id,
            'file_id': self.file_id,
            'ifc_guid': self.ifc_guid or '',
            'name': self.name or '',
            'description': self.description or '',
            'properties': self.properties
        }


class KuzuVertex(BaseModel):
    """Kuzu vertex node model"""
    id: str
    file_id: str
    building_id: Optional[str] = None
    space_id: Optional[str] = None
    ifc_type: Optional[str] = None
    ifc_guid: Optional[str] = None
    name: Optional[str] = None
    x: float
    y: float
    z: float
    properties: Dict[str, str] = {}

    def to_kuzu_params(self) -> Dict[str, Any]:
        """Convert to Kuzu query parameters"""
        return {
            'id': self.id,
            'file_id': self.file_id,
            'building_id': self.building_id or '',
            'space_id': self.space_id or '',
            'ifc_type': self.ifc_type or '',
            'ifc_guid': self.ifc_guid or '',
            'name': self.name or '',
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'properties': self.properties
        }


class KuzuEdge(BaseModel):
    """Kuzu edge relationship model"""
    from_vertex_id: str
    to_vertex_id: str
    connection_type: Optional[str] = None
    edge_type: Optional[str] = None
    properties: Dict[str, str] = {}
    
    def to_kuzu_params(self) -> Dict[str, Any]:
        """Convert to Kuzu query parameters"""
        return {
            'from_id': self.from_vertex_id,
            'to_id': self.to_vertex_id,
            'connection_type': self.connection_type or '',
            'edge_type': self.edge_type or '',
            'properties': self.properties
        }


class KuzuSchema:
    """Kuzu database schema definitions"""
    
    @staticmethod
    def get_create_table_statements() -> List[str]:
        """Get all CREATE TABLE statements for Kuzu schema"""
        return [
            # Track individual IFC files as separate buildings
            """
            CREATE NODE TABLE IF NOT EXISTS IfcFile(
                id STRING,
                filename STRING,
                file_path STRING,
                upload_timestamp STRING,
                building_name STRING,
                file_size_mb DOUBLE,
                processing_method STRING,
                PRIMARY KEY(id)
            )
            """,

            # Building hierarchy with source tracking
            """
            CREATE NODE TABLE IF NOT EXISTS IfcBuilding(
                id STRING,
                file_id STRING,
                ifc_guid STRING,
                name STRING,
                description STRING,
                properties MAP(STRING, STRING),
                PRIMARY KEY(id)
            )
            """,

            # Specialized space node table
            """
            CREATE NODE TABLE IF NOT EXISTS IfcSpace(
                id STRING,
                file_id STRING,
                building_id STRING,
                ifc_guid STRING,
                name STRING,
                area DOUBLE,
                volume DOUBLE,
                x DOUBLE,
                y DOUBLE,
                z DOUBLE,
                properties MAP(STRING, STRING),
                PRIMARY KEY(id)
            )
            """,

            # Elements with building context
            """
            CREATE NODE TABLE IF NOT EXISTS IfcElement(
                id STRING,
                file_id STRING,
                building_id STRING,
                space_id STRING,
                ifc_type STRING,
                ifc_guid STRING,
                name STRING,
                x DOUBLE,
                y DOUBLE,
                z DOUBLE,
                properties MAP(STRING, STRING),
                PRIMARY KEY(id)
            )
            """,

            # Hierarchical relationships
            """
            CREATE REL TABLE IF NOT EXISTS ContainedInFile(
                FROM IfcBuilding TO IfcFile,
                relationship_type STRING
            )
            """,

            """
            CREATE REL TABLE IF NOT EXISTS ContainedInBuilding(
                FROM IfcElement TO IfcBuilding,
                containment_type STRING
            )
            """,

            """
            CREATE REL TABLE IF NOT EXISTS ContainedInSpace(
                FROM IfcElement TO IfcSpace,
                containment_type STRING
            )
            """,

            # Topological connections between elements
            """
            CREATE REL TABLE IF NOT EXISTS TopologicalConnection(
                FROM IfcElement TO IfcElement,
                connection_type STRING,
                edge_type STRING,
                shared_geometry STRING,
                properties MAP(STRING, STRING)
            )
            """
        ]
    
    @staticmethod
    def get_index_statements() -> List[str]:
        """Get CREATE INDEX statements for performance"""
        return [
            "CREATE INDEX IF NOT EXISTS idx_ifc_type ON IfcElement(ifc_type)",
            "CREATE INDEX IF NOT EXISTS idx_ifc_guid ON IfcElement(ifc_guid)",
            "CREATE INDEX IF NOT EXISTS idx_coordinates ON IfcElement(x, y, z)",
            "CREATE INDEX IF NOT EXISTS idx_file_id ON IfcElement(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_building_id ON IfcElement(building_id)",
            "CREATE INDEX IF NOT EXISTS idx_filename ON IfcFile(filename)"
        ]


class KuzuQueryBuilder:
    """Helper class for building common Kuzu queries"""

    @staticmethod
    def insert_ifc_file(ifc_file: KuzuIfcFile) -> str:
        """Build INSERT query for IFC file"""
        return """
        CREATE (f:IfcFile {
            id: $id,
            filename: $filename,
            file_path: $file_path,
            upload_timestamp: $upload_timestamp,
            building_name: $building_name,
            file_size_mb: $file_size_mb,
            processing_method: $processing_method
        })
        """

    @staticmethod
    def insert_building(building: KuzuBuilding) -> str:
        """Build INSERT query for building"""
        return """
        CREATE (b:IfcBuilding {
            id: $id,
            file_id: $file_id,
            ifc_guid: $ifc_guid,
            name: $name,
            description: $description,
            properties: $properties
        })
        """

    @staticmethod
    def insert_vertex(vertex: KuzuVertex) -> str:
        """Build INSERT query for vertex with building context"""
        return """
        CREATE (n:IfcElement {
            id: $id,
            file_id: $file_id,
            building_id: $building_id,
            space_id: $space_id,
            ifc_type: $ifc_type,
            ifc_guid: $ifc_guid,
            name: $name,
            x: $x,
            y: $y,
            z: $z,
            properties: $properties
        })
        """

    @staticmethod
    def insert_edge(edge: KuzuEdge) -> str:
        """Build INSERT query for edge"""
        return """
        MATCH (a:IfcElement {id: $from_id})
        MATCH (b:IfcElement {id: $to_id})
        CREATE (a)-[:TopologicalConnection {
            connection_type: $connection_type,
            edge_type: $edge_type,
            properties: $properties
        }]->(b)
        """

    @staticmethod
    def get_all_files() -> str:
        """Get all IFC files"""
        return "MATCH (f:IfcFile) RETURN f ORDER BY f.upload_timestamp DESC"

    @staticmethod
    def get_buildings_by_file(file_id: str) -> str:
        """Get buildings for a specific file"""
        return "MATCH (b:IfcBuilding {file_id: $file_id}) RETURN b"

    @staticmethod
    def get_elements_by_file(file_id: str) -> str:
        """Get elements for a specific file"""
        return "MATCH (e:IfcElement {file_id: $file_id}) RETURN e"

    @staticmethod
    def get_elements_by_building(building_id: str) -> str:
        """Get elements for a specific building"""
        return "MATCH (e:IfcElement {building_id: $building_id}) RETURN e"

    @staticmethod
    def get_vertex_by_id() -> str:
        """Get vertex by ID"""
        return "MATCH (n:IfcElement {id: $id}) RETURN n"

    @staticmethod
    def get_vertices_by_type() -> str:
        """Get all vertices of a specific IFC type"""
        return "MATCH (n:IfcElement {ifc_type: $ifc_type}) RETURN n"

    @staticmethod
    def get_vertices_by_file_and_type(file_id: str, ifc_type: str) -> str:
        """Get vertices by file and type"""
        return "MATCH (n:IfcElement {file_id: $file_id, ifc_type: $ifc_type}) RETURN n"

    @staticmethod
    def get_connected_vertices() -> str:
        """Get vertices connected to a specific vertex"""
        return """
        MATCH (start:IfcElement {id: $vertex_id})
        MATCH (start)-[r:TopologicalConnection]-(connected:IfcElement)
        RETURN connected, r
        """

    @staticmethod
    def get_file_statistics(file_id: str) -> str:
        """Get statistics for a specific file"""
        return """
        MATCH (e:IfcElement {file_id: $file_id})
        OPTIONAL MATCH (e)-[r:TopologicalConnection]-()
        RETURN
            count(DISTINCT e) as vertex_count,
            count(DISTINCT r) as edge_count,
            collect(DISTINCT e.ifc_type) as ifc_types
        """

    @staticmethod
    def get_graph_statistics() -> str:
        """Get basic graph statistics"""
        return """
        MATCH (n:IfcElement)
        OPTIONAL MATCH (n)-[r:TopologicalConnection]-()
        RETURN
            count(DISTINCT n) as vertex_count,
            count(DISTINCT r) as edge_count,
            collect(DISTINCT n.ifc_type) as ifc_types
        """

    @staticmethod
    def clear_all_data() -> str:
        """Clear all data from database (for testing)"""
        return "MATCH (n) DETACH DELETE n"

    @staticmethod
    def delete_file_data(file_id: str) -> str:
        """Delete all data for a specific file"""
        return """
        MATCH (e:IfcElement {file_id: $file_id})
        OPTIONAL MATCH (b:IfcBuilding {file_id: $file_id})
        OPTIONAL MATCH (f:IfcFile {id: $file_id})
        DETACH DELETE e, b, f
        """