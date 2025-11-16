"""
Kuzu Database Service for storing and querying IFC graph data.

Provides high-performance graph database operations for TopologicPy data
with optimized schema for IFC entity relationships and spatial queries.
"""

import logging
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    import kuzu
except ImportError as e:
    logging.warning(f"Kuzu not available: {e}")
    # Create mock for development
    class kuzu:
        class Database: pass
        class Connection: pass

from models.topologic_models import TopologicGraph, TopologicVertex, TopologicEdge
from models.kuzu_models import KuzuVertex, KuzuEdge, KuzuIfcFile, KuzuBuilding, KuzuSchema, KuzuQueryBuilder
from models.data_models import GraphStats


class KuzuService:
    """
    Kuzu graph database service for IFC data storage and analytics.
    
    Provides optimized storage for TopologicPy graphs with spatial indexing
    and efficient querying for graph analytics and visualization.
    """
    
    def __init__(self, db_path: str = "kuzu_db"):
        """
        Initialize Kuzu database connection.
        
        Args:
            db_path: Path to Kuzu database directory
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = Path(db_path)
        self.database = None
        self.connection = None
        self.is_available = False
        
        try:
            self._initialize_database()
            self.is_available = True
        except Exception as e:
            self.logger.error(f"Failed to initialize Kuzu database: {e}")
            self.is_available = False

    def _initialize_database(self):
        """Initialize Kuzu database and create schema"""
        # Ensure the parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing database files completely for schema migration
        if self.db_path.exists():
            if self.db_path.is_dir():
                import shutil
                shutil.rmtree(self.db_path)
                self.logger.info(f"Removed existing database directory: {self.db_path}")
            else:
                self.db_path.unlink()
                self.logger.info(f"Removed existing database file: {self.db_path}")

        # Remove WAL file if it exists
        wal_file = self.db_path.with_suffix('.wal')
        if wal_file.exists():
            wal_file.unlink()
            self.logger.info(f"Removed existing WAL file: {wal_file}")

        # Initialize Kuzu database (it will create the directory)
        self.database = kuzu.Database(str(self.db_path))
        self.connection = kuzu.Connection(self.database)

        self.logger.info(f"Kuzu database initialized at: {self.db_path}")

        # Create schema
        self._create_schema()

    def _create_schema(self):
        """Create database schema tables and indexes"""
        try:
            # Create node and relationship tables
            for statement in KuzuSchema.get_create_table_statements():
                self.logger.debug(f"Executing: {statement.strip()}")
                self.connection.execute(statement)
            
            # Create indexes for performance
            for index_statement in KuzuSchema.get_index_statements():
                try:
                    self.connection.execute(index_statement)
                except Exception as e:
                    # Indexes might already exist, continue
                    self.logger.debug(f"Index creation note: {e}")
            
            self.logger.info("Kuzu schema created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create schema: {e}")
            raise

    def store_graph(self, graph: TopologicGraph, filename: str = None, building_name: str = None) -> bool:
        """
        Store TopologicGraph in Kuzu database with building separation.

        Args:
            graph: TopologicGraph to store
            filename: Original filename for tracking
            building_name: Optional building name

        Returns:
            Success status
        """
        if not self.is_available:
            self.logger.warning("Kuzu database not available, skipping storage")
            return False

        try:
            self.logger.info(f"Storing graph with {len(graph.vertices)} vertices and {len(graph.edges)} edges")

            # Create file record
            file_id = self._store_ifc_file_record(graph, filename, building_name)
            if not file_id:
                raise Exception("Failed to store IFC file record")

            # Update graph with file context
            graph.file_id = file_id
            graph.filename = filename
            graph.building_name = building_name

            # Create building record (optional)
            building_id = self._store_building_record(graph, file_id)
            if building_id:
                graph.building_id = building_id

            # Convert and store vertices with building context
            vertices_stored = self._store_vertices(graph.vertices, file_id, building_id)
            self.logger.info(f"Stored {vertices_stored} vertices")

            # Convert and store edges
            edges_stored = self._store_edges(graph.edges)
            self.logger.info(f"Stored {edges_stored} edges")

            return True

        except Exception as e:
            self.logger.error(f"Failed to store graph: {e}")
            return False

    def _store_ifc_file_record(self, graph: TopologicGraph, filename: str = None, building_name: str = None) -> Optional[str]:
        """Store IFC file record in database"""
        try:
            file_id = str(uuid.uuid4())

            ifc_file = KuzuIfcFile(
                id=file_id,
                filename=filename or graph.source_file or "unknown.ifc",
                file_path=graph.source_file or "",
                upload_timestamp=graph.creation_timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
                building_name=building_name or f"Building_{file_id[:8]}",
                file_size_mb=0.0,  # Could be calculated from file_path
                processing_method=graph.processing_method or "direct"
            )

            query = f"""
            CREATE (f:IfcFile {{
                id: '{ifc_file.id}',
                filename: '{ifc_file.filename}',
                file_path: '{ifc_file.file_path}',
                upload_timestamp: '{ifc_file.upload_timestamp}',
                building_name: '{ifc_file.building_name}',
                file_size_mb: {ifc_file.file_size_mb},
                processing_method: '{ifc_file.processing_method}'
            }})
            """

            self.connection.execute(query)
            self.logger.info(f"Stored IFC file record: {filename} with ID {file_id}")
            return file_id

        except Exception as e:
            self.logger.error(f"Failed to store IFC file record: {e}")
            return None

    def _store_building_record(self, graph: TopologicGraph, file_id: str) -> Optional[str]:
        """Store building record in database"""
        try:
            building_id = str(uuid.uuid4())

            # Look for building elements in vertices to extract building info
            building_vertices = [v for v in graph.vertices if v.ifc_type and 'building' in v.ifc_type.lower()]
            building_name = graph.building_name or "Unknown Building"
            building_guid = ""

            if building_vertices:
                building_vertex = building_vertices[0]
                building_name = building_vertex.ifc_name or building_name
                building_guid = building_vertex.ifc_guid or ""

            building = KuzuBuilding(
                id=building_id,
                file_id=file_id,
                ifc_guid=building_guid,
                name=building_name,
                description=f"Building from {graph.filename or 'IFC file'}",
                properties={}
            )

            query = f"""
            CREATE (b:IfcBuilding {{
                id: '{building.id}',
                file_id: '{building.file_id}',
                ifc_guid: '{building.ifc_guid}',
                name: '{building.name}',
                description: '{building.description}',
                properties: map([], [])
            }})
            """

            self.connection.execute(query)
            self.logger.info(f"Stored building record: {building_name} with ID {building_id}")
            return building_id

        except Exception as e:
            self.logger.error(f"Failed to store building record: {e}")
            return None

    def _store_vertices(self, vertices: List[TopologicVertex], file_id: str, building_id: Optional[str] = None) -> int:
        """Store vertices in Kuzu database with building context"""
        stored_count = 0

        for vertex in vertices:
            try:
                kuzu_vertex = self._convert_to_kuzu_vertex(vertex, file_id, building_id)

                # Use direct CREATE query to avoid parameter type issues
                query = f"""
                CREATE (n:IfcElement {{
                    id: '{kuzu_vertex.id}',
                    file_id: '{kuzu_vertex.file_id}',
                    building_id: '{kuzu_vertex.building_id or ""}',
                    space_id: '{kuzu_vertex.space_id or ""}',
                    ifc_type: '{kuzu_vertex.ifc_type or ""}',
                    ifc_guid: '{kuzu_vertex.ifc_guid or ""}',
                    name: '{kuzu_vertex.name or ""}',
                    x: {kuzu_vertex.x},
                    y: {kuzu_vertex.y},
                    z: {kuzu_vertex.z},
                    properties: map([], [])
                }})
                """

                result = self.connection.execute(query)
                stored_count += 1

            except Exception as e:
                self.logger.warning(f"Failed to store vertex {vertex.id}: {e}")
                continue

        return stored_count

    def _store_edges(self, edges: List[TopologicEdge]) -> int:
        """Store edges in Kuzu database"""
        stored_count = 0
        
        for edge in edges:
            try:
                kuzu_edge = self._convert_to_kuzu_edge(edge)
                
                # Use direct CREATE query to avoid parameter type issues
                query = f"""
                MATCH (a:IfcElement {{id: '{kuzu_edge.from_vertex_id}'}})
                MATCH (b:IfcElement {{id: '{kuzu_edge.to_vertex_id}'}})
                CREATE (a)-[:TopologicalConnection {{
                    connection_type: '{kuzu_edge.connection_type or ""}',
                    edge_type: '{kuzu_edge.edge_type or ""}',
                    properties: map([], [])
                }}]->(b)
                """
                
                result = self.connection.execute(query)
                stored_count += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to store edge {edge.id}: {e}")
                continue
                
        return stored_count

    def _convert_to_kuzu_vertex(self, vertex: TopologicVertex, file_id: str, building_id: Optional[str] = None) -> KuzuVertex:
        """Convert TopologicVertex to KuzuVertex with building context"""
        # Convert dictionaries to string map for Kuzu storage
        properties = {str(k): str(v) for k, v in vertex.dictionaries.items()}

        return KuzuVertex(
            id=vertex.id,
            file_id=file_id,
            building_id=building_id,
            space_id=None,  # Could be extracted from vertex.dictionaries if needed
            ifc_type=vertex.ifc_type,
            ifc_guid=vertex.ifc_guid,
            name=vertex.ifc_name,
            x=vertex.coordinates[0],
            y=vertex.coordinates[1],
            z=vertex.coordinates[2],
            properties=properties
        )

    def _convert_to_kuzu_edge(self, edge: TopologicEdge) -> KuzuEdge:
        """Convert TopologicEdge to KuzuEdge"""
        # Convert dictionaries to string map for Kuzu storage
        properties = {str(k): str(v) for k, v in edge.dictionaries.items()}
        
        return KuzuEdge(
            from_vertex_id=edge.start_vertex_id,
            to_vertex_id=edge.end_vertex_id,
            connection_type=edge.connection_type,
            edge_type=edge.edge_type,
            properties=properties
        )

    def get_graph_statistics(self) -> GraphStats:
        """Get basic graph statistics from database"""
        if not self.is_available:
            return GraphStats()
            
        try:
            # Simple vertex count query
            vertex_query = "MATCH (n:IfcElement) RETURN count(n)"
            vertex_result = self.connection.execute(vertex_query)
            vertex_count = 0
            if vertex_result.has_next():
                vertex_count = vertex_result.get_next()[0]
            
            # Simple edge count query  
            edge_query = "MATCH ()-[r:TopologicalConnection]-() RETURN count(r)"
            edge_result = self.connection.execute(edge_query)
            edge_count = 0
            if edge_result.has_next():
                edge_count = edge_result.get_next()[0]
            
            # Count IFC types
            ifc_type_counts = {}
            type_query = "MATCH (n:IfcElement) RETURN n.ifc_type, count(n) ORDER BY count(n) DESC"
            type_result = self.connection.execute(type_query)
            while type_result.has_next():
                type_row = type_result.get_next()
                if type_row[0] and type_row[0].strip():  # Skip empty/null types
                    ifc_type_counts[type_row[0]] = type_row[1]
            
            return GraphStats(
                vertex_count=vertex_count,
                edge_count=edge_count,
                ifc_types=ifc_type_counts
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return GraphStats()

    def get_vertices_by_type(self, ifc_type: str) -> List[Dict[str, Any]]:
        """Get all vertices of a specific IFC type"""
        try:
            query = KuzuQueryBuilder.get_vertices_by_type()
            result = self.connection.execute(query, {"ifc_type": ifc_type})
            
            vertices = []
            while True:
                row = result.get_next()
                if row is None:
                    break
                    
                vertex_data = row[0]  # Node data
                vertices.append({
                    'id': vertex_data.get('id'),
                    'ifc_type': vertex_data.get('ifc_type'),
                    'ifc_guid': vertex_data.get('ifc_guid'),
                    'name': vertex_data.get('name'),
                    'coordinates': [
                        vertex_data.get('x', 0.0),
                        vertex_data.get('y', 0.0),
                        vertex_data.get('z', 0.0)
                    ],
                    'properties': vertex_data.get('properties', {})
                })
                
            return vertices
            
        except Exception as e:
            self.logger.error(f"Failed to get vertices by type {ifc_type}: {e}")
            return []

    def get_connected_vertices(self, vertex_id: str) -> List[Dict[str, Any]]:
        """Get vertices connected to a specific vertex"""
        try:
            query = KuzuQueryBuilder.get_connected_vertices()
            result = self.connection.execute(query, {"vertex_id": vertex_id})
            
            connected = []
            while True:
                row = result.get_next()
                if row is None:
                    break
                    
                vertex_data = row[0]  # Connected vertex
                edge_data = row[1] if len(row) > 1 else {}  # Relationship data
                
                connected.append({
                    'vertex': {
                        'id': vertex_data.get('id'),
                        'ifc_type': vertex_data.get('ifc_type'),
                        'name': vertex_data.get('name'),
                        'coordinates': [
                            vertex_data.get('x', 0.0),
                            vertex_data.get('y', 0.0), 
                            vertex_data.get('z', 0.0)
                        ]
                    },
                    'relationship': {
                        'connection_type': edge_data.get('connection_type'),
                        'edge_type': edge_data.get('edge_type'),
                        'properties': edge_data.get('properties', {})
                    }
                })
                
            return connected
            
        except Exception as e:
            self.logger.error(f"Failed to get connected vertices for {vertex_id}: {e}")
            return []

    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all IFC files in the database"""
        if not self.is_available:
            return []

        try:
            query = "MATCH (f:IfcFile) RETURN f ORDER BY f.upload_timestamp DESC"
            result = self.connection.execute(query)
            files = []

            while result.has_next():
                row = result.get_next()
                file_data = row[0]
                files.append({
                    'id': file_data.get('id', ''),
                    'filename': file_data.get('filename', ''),
                    'building_name': file_data.get('building_name', ''),
                    'upload_timestamp': file_data.get('upload_timestamp', ''),
                    'processing_method': file_data.get('processing_method', ''),
                    'file_size_mb': file_data.get('file_size_mb', 0.0)
                })

            return files

        except Exception as e:
            self.logger.error(f"Failed to get files: {e}")
            return []

    def get_file_statistics(self, file_id: str) -> GraphStats:
        """Get statistics for a specific file"""
        if not self.is_available:
            return GraphStats()

        try:
            # Count vertices and edges for this file
            vertex_query = "MATCH (n:IfcElement {file_id: $file_id}) RETURN count(n)"
            vertex_result = self.connection.execute(vertex_query, {"file_id": file_id})
            vertex_count = 0
            if vertex_result.has_next():
                vertex_count = vertex_result.get_next()[0]

            # Count edges for this file
            edge_query = """
            MATCH (a:IfcElement {file_id: $file_id})-[r:TopologicalConnection]-(b:IfcElement {file_id: $file_id})
            RETURN count(r)
            """
            edge_result = self.connection.execute(edge_query, {"file_id": file_id})
            edge_count = 0
            if edge_result.has_next():
                edge_count = edge_result.get_next()[0]

            # Count IFC types for this file
            ifc_type_counts = {}
            type_query = """
            MATCH (n:IfcElement {file_id: $file_id})
            RETURN n.ifc_type, count(n)
            ORDER BY count(n) DESC
            """
            type_result = self.connection.execute(type_query, {"file_id": file_id})
            while type_result.has_next():
                type_row = type_result.get_next()
                if type_row[0] and type_row[0].strip():
                    ifc_type_counts[type_row[0]] = type_row[1]

            return GraphStats(
                vertex_count=vertex_count,
                edge_count=edge_count,
                ifc_types=ifc_type_counts
            )

        except Exception as e:
            self.logger.error(f"Failed to get file statistics: {e}")
            return GraphStats()

    def get_vertices_by_file(self, file_id: str) -> List[Dict[str, Any]]:
        """Get all vertices for a specific file"""
        if not self.is_available:
            return []

        try:
            query = """
            MATCH (n:IfcElement {file_id: $file_id})
            RETURN n.id, n.ifc_type, n.name, n.x, n.y, n.z, n.ifc_guid, n.building_id
            ORDER BY n.ifc_type, n.name
            """

            result = self.connection.execute(query, {"file_id": file_id})
            vertices = []

            while result.has_next():
                row = result.get_next()
                vertices.append({
                    'id': row[0],
                    'ifc_type': row[1] or 'Unknown',
                    'name': row[2] or 'Unnamed',
                    'x': row[3] or 0.0,
                    'y': row[4] or 0.0,
                    'z': row[5] or 0.0,
                    'ifc_guid': row[6] or '',
                    'building_id': row[7] or '',
                    'file_id': file_id
                })

            return vertices

        except Exception as e:
            self.logger.error(f"Failed to get vertices for file {file_id}: {e}")
            return []

    def get_all_vertices_with_coordinates(self) -> List[Dict[str, Any]]:
        """Get all vertices with their coordinates for visualization"""
        if not self.is_available:
            return []

        try:
            query = """
            MATCH (n:IfcElement)
            RETURN n.id, n.ifc_type, n.name, n.x, n.y, n.z, n.ifc_guid, n.file_id, n.building_id
            ORDER BY n.file_id, n.ifc_type, n.name
            """

            result = self.connection.execute(query)
            vertices = []

            while result.has_next():
                row = result.get_next()
                vertices.append({
                    'id': row[0],
                    'ifc_type': row[1] or 'Unknown',
                    'name': row[2] or 'Unnamed',
                    'x': row[3] or 0.0,
                    'y': row[4] or 0.0,
                    'z': row[5] or 0.0,
                    'ifc_guid': row[6] or '',
                    'file_id': row[7] or '',
                    'building_id': row[8] or ''
                })

            return vertices

        except Exception as e:
            self.logger.error(f"Failed to get vertices with coordinates: {e}")
            return []

    def clear_database(self) -> bool:
        """Clear all data from database (for testing)"""
        if not self.is_available:
            self.logger.warning("Kuzu database not available, cannot clear")
            return False
            
        try:
            query = KuzuQueryBuilder.clear_all_data()
            self.connection.execute(query)
            self.logger.info("Database cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear database: {e}")
            return False

    def close(self):
        """Close database connection"""
        try:
            if self.connection:
                self.connection = None
            if self.database:
                self.database = None
            self.logger.info("Kuzu database connection closed")
            
        except Exception as e:
            self.logger.error(f"Error closing database: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()