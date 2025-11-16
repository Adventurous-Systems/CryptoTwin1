"""
IFC Processor Service using TopologicPy for graph extraction.

Implements robust IFC processing with multiple fallback strategies based on 
adventurous_topologic patterns, preserving IFC metadata through TopologicPy Dictionary system.
"""

import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    from topologicpy.Graph import Graph
    from topologicpy.Topology import Topology 
    from topologicpy.Dictionary import Dictionary
    from topologicpy.Vertex import Vertex
    from topologicpy.Edge import Edge
except ImportError as e:
    logging.warning(f"TopologicPy not available: {e}")
    # Create mock classes for development without TopologicPy
    class Graph:
        @staticmethod
        def ByIFCPath(*args, **kwargs):
            raise ImportError("TopologicPy not installed")
    class Topology: pass
    class Dictionary: pass
    class Vertex: pass
    class Edge: pass

from models.topologic_models import (
    TopologicGraph, TopologicVertex, TopologicEdge, IFCProcessingContext
)
from models.data_models import ProcessingConfig, ProcessingResult, GraphStats


class IFCProcessorService:
    """
    IFC processing service with TopologicPy integration and robust error handling.
    
    Based on patterns from adventurous_topologic with enhancements for Kuzu integration.
    Implements multiple processing strategies with fallbacks for maximum compatibility.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common IFC entity types for filtering
        self.default_ifc_types = [
            "IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", "IfcWindow",
            "IfcSpace", "IfcRoom", "IfcBuildingStorey", "IfcBuilding"
        ]
        
        # Dictionary keys for IFC metadata extraction
        self.ifc_type_keys = ["IFC_type", "ifc_type", "IFCType", "type", "Entity"]
        self.ifc_guid_keys = [
            "IFC_global_id", "ifc_guid", "IFCGuid", "IFC_GUID", "GlobalId", "guid"
        ]
        self.ifc_name_keys = ["Name", "name", "IFC_name"]

    def process_ifc_file(
        self,
        file_path: str,
        config: ProcessingConfig
    ) -> Tuple[TopologicGraph, ProcessingResult, Optional[Any]]:
        """
        Process IFC file using TopologicPy with fallback strategies.

        Args:
            file_path: Path to IFC file
            config: Processing configuration

        Returns:
            Tuple of (TopologicGraph, ProcessingResult, original_topologic_graph)
        """
        context = IFCProcessingContext(
            file_path=file_path,
            method=config.method.value,
            include_types=config.include_types or [],
            transfer_dictionaries=config.transfer_dictionaries,
            tolerance=config.tolerance
        )
        
        context.start_processing()
        
        try:
            # Validate file
            if not self._validate_ifc_file(file_path):
                raise ValueError(f"Invalid IFC file: {file_path}")
            
            # Try processing with primary method
            graph = self._process_with_fallbacks(context)
            
            if graph:
                context.complete_processing(success=True)
                result = ProcessingResult(
                    success=True,
                    message=f"Successfully processed IFC file using {context.current_method}",
                    stats=self._calculate_stats(graph, file_path),
                    processing_time=context.processing_time
                )
                return graph, result, context.original_topologic_graph
            else:
                raise Exception("All processing methods failed")

        except Exception as e:
            context.add_error(str(e))
            context.complete_processing(success=False)

            self.logger.error(f"IFC processing failed: {e}")
            result = ProcessingResult(
                success=False,
                message=f"Failed to process IFC file: {str(e)}",
                error_details=str(e),
                processing_time=context.processing_time
            )
            return TopologicGraph(), result, None

    def _process_with_fallbacks(self, context: IFCProcessingContext) -> Optional[TopologicGraph]:
        """
        Process IFC with multiple fallback strategies.
        
        Based on adventurous_topologic patterns for maximum compatibility.
        """
        strategies = [
            ("direct_with_dictionaries", self._process_direct_with_dictionaries),
            ("direct_without_dictionaries", self._process_direct_without_dictionaries),
            ("traditional_with_types", self._process_traditional_with_types),
            ("traditional_fallback", self._process_traditional_fallback)
        ]
        
        for strategy_name, strategy_func in strategies:
            if strategy_name in context.attempted_methods:
                continue
                
            self.logger.info(f"Attempting processing strategy: {strategy_name}")
            context.attempted_methods.append(strategy_name)
            context.current_method = strategy_name
            
            try:
                graph = strategy_func(context)
                if graph and len(graph.vertices) > 0:
                    self.logger.info(f"Success with {strategy_name}: {len(graph.vertices)} vertices")
                    return graph
                    
            except Exception as e:
                self.logger.warning(f"Strategy {strategy_name} failed: {e}")
                context.add_error(f"{strategy_name}: {str(e)}")
                continue
        
        return None

    def _process_direct_with_dictionaries(self, context: IFCProcessingContext) -> TopologicGraph:
        """Primary processing method: Graph.ByIFCPath with full dictionary preservation"""
        self.logger.info("Processing with Graph.ByIFCPath (dictionaries=True)")

        include_types = context.include_types if context.include_types else None

        # Log detailed information for debugging
        self.logger.info(f"File path: {context.file_path}")
        self.logger.info(f"Include types: {include_types}")
        self.logger.info(f"File exists: {Path(context.file_path).exists()}")
        self.logger.info(f"File size: {Path(context.file_path).stat().st_size if Path(context.file_path).exists() else 'N/A'} bytes")

        try:
            topologic_graph = Graph.ByIFCPath(
                path=context.file_path,
                includeTypes=include_types,
                transferDictionaries=True
            )
        except Exception as e:
            raise Exception(f"Graph.ByIFCPath failed with exception: {e}")

        if not topologic_graph:
            # Try without include_types as fallback
            self.logger.warning("Graph.ByIFCPath returned None with include_types, trying without types filter")
            try:
                topologic_graph = Graph.ByIFCPath(
                    path=context.file_path,
                    includeTypes=None,  # No type filtering
                    transferDictionaries=True
                )
            except Exception as e:
                raise Exception(f"Graph.ByIFCPath fallback failed: {e}")

            if not topologic_graph:
                raise Exception(f"Graph.ByIFCPath returned None even without type filtering. "
                              f"File may be corrupted or unsupported: {context.file_path}")

        return self._extract_graph_data(topologic_graph, context)

    def _process_direct_without_dictionaries(self, context: IFCProcessingContext) -> TopologicGraph:
        """Fallback 1: Graph.ByIFCPath without dictionaries"""
        self.logger.info("Processing with Graph.ByIFCPath (dictionaries=False)")
        
        topologic_graph = Graph.ByIFCPath(
            path=context.file_path,
            includeTypes=context.include_types or None,
            transferDictionaries=False
        )
        
        if not topologic_graph:
            raise Exception("Graph.ByIFCPath without dictionaries returned None")
            
        return self._extract_graph_data(topologic_graph, context)

    def _process_traditional_with_types(self, context: IFCProcessingContext) -> TopologicGraph:
        """Fallback 2: Traditional topology extraction with specified types"""
        self.logger.info("Processing with traditional topology method (with types)")
        
        include_types = context.include_types or self.default_ifc_types
        
        # This would implement traditional IFC → Topology → Graph conversion
        # For now, attempt direct processing with default types
        topologic_graph = Graph.ByIFCPath(
            path=context.file_path,
            includeTypes=include_types,
            transferDictionaries=True
        )
        
        if not topologic_graph:
            raise Exception("Traditional processing with types failed")
            
        return self._extract_graph_data(topologic_graph, context)

    def _process_traditional_fallback(self, context: IFCProcessingContext) -> TopologicGraph:
        """Fallback 3: Traditional method with minimal parameters"""
        self.logger.info("Processing with minimal traditional method")
        
        # Final fallback - minimal parameters, maximum tolerance
        topologic_graph = Graph.ByIFCPath(
            path=context.file_path,
            includeTypes=None,  # Include all types
            transferDictionaries=False
        )
        
        if not topologic_graph:
            raise Exception("All fallback methods failed")
            
        return self._extract_graph_data(topologic_graph, context)

    def _extract_graph_data(
        self,
        topologic_graph: Graph,
        context: IFCProcessingContext
    ) -> TopologicGraph:
        """
        Extract vertices and edges from TopologicPy Graph with metadata preservation.
        """
        if not topologic_graph:
            raise Exception("TopologicPy Graph is None - cannot extract data")

        self.logger.info("Extracting vertices and edges from TopologicPy Graph")

        # Store original TopologicPy Graph for visualization
        context.original_topologic_graph = topologic_graph
        
        # Extract vertices
        vertices = self._extract_vertices(topologic_graph)
        self.logger.info(f"Extracted {len(vertices)} vertices")
        
        # Extract edges  
        edges = self._extract_edges(topologic_graph, vertices)
        self.logger.info(f"Extracted {len(edges)} edges")
        
        # Create TopologicGraph
        graph = TopologicGraph(
            vertices=vertices,
            edges=edges,
            source_file=context.file_path,
            processing_method=context.current_method,
            creation_timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        graph.update_statistics()
        return graph

    def _extract_vertices(self, topologic_graph: Graph) -> List[TopologicVertex]:
        """Extract vertices with coordinates and IFC metadata"""
        vertices = []

        try:
            # Get vertices from TopologicPy Graph
            graph_vertices = Graph.Vertices(topologic_graph)

            if not graph_vertices:
                self.logger.warning("No vertices found in TopologicPy Graph")
                return vertices

            for i, vertex in enumerate(graph_vertices):
                # Extract coordinates
                coords = (
                    Vertex.X(vertex),
                    Vertex.Y(vertex), 
                    Vertex.Z(vertex)
                )
                
                # Extract dictionaries
                dictionaries = {}
                try:
                    vertex_dict = Topology.Dictionary(vertex)
                    if vertex_dict:
                        dict_keys = Dictionary.Keys(vertex_dict)
                        for key in dict_keys:
                            value = Dictionary.ValueAtKey(vertex_dict, key)
                            dictionaries[key] = value
                except Exception as e:
                    self.logger.debug(f"No dictionary for vertex {i}: {e}")
                
                # Create TopologicVertex
                topo_vertex = TopologicVertex(
                    coordinates=coords,
                    dictionaries=dictionaries
                )
                topo_vertex.extract_ifc_metadata()
                vertices.append(topo_vertex)
                
        except Exception as e:
            self.logger.error(f"Error extracting vertices: {e}")
            raise
            
        return vertices

    def _extract_edges(
        self, 
        topologic_graph: Graph, 
        vertices: List[TopologicVertex]
    ) -> List[TopologicEdge]:
        """Extract edges with relationship metadata"""
        edges = []
        vertex_lookup = {i: v.id for i, v in enumerate(vertices)}
        
        try:
            # Get edges from TopologicPy Graph
            graph_edges = Graph.Edges(topologic_graph)

            if not graph_edges:
                self.logger.warning("No edges found in TopologicPy Graph")
                return edges

            for edge in graph_edges:
                # Get edge vertices
                edge_vertices = Edge.Vertices(edge)
                if len(edge_vertices) >= 2:
                    # Find corresponding vertex IDs
                    start_idx = self._find_vertex_index(edge_vertices[0], vertices)
                    end_idx = self._find_vertex_index(edge_vertices[1], vertices)
                    
                    if start_idx is not None and end_idx is not None:
                        # Extract edge dictionaries
                        dictionaries = {}
                        try:
                            edge_dict = Topology.Dictionary(edge)
                            if edge_dict:
                                dict_keys = Dictionary.Keys(edge_dict)
                                for key in dict_keys:
                                    value = Dictionary.ValueAtKey(edge_dict, key)
                                    dictionaries[key] = value
                        except Exception as e:
                            self.logger.debug(f"No dictionary for edge: {e}")
                        
                        # Create TopologicEdge
                        topo_edge = TopologicEdge(
                            start_vertex_id=vertices[start_idx].id,
                            end_vertex_id=vertices[end_idx].id,
                            dictionaries=dictionaries
                        )
                        topo_edge.extract_connection_metadata()
                        edges.append(topo_edge)
                        
        except Exception as e:
            self.logger.error(f"Error extracting edges: {e}")
            # Continue without edges rather than failing completely
            
        return edges

    def _find_vertex_index(self, target_vertex, vertices: List[TopologicVertex]) -> Optional[int]:
        """Find vertex index by coordinate matching"""
        target_coords = (
            Vertex.X(target_vertex),
            Vertex.Y(target_vertex),
            Vertex.Z(target_vertex)
        )
        
        for i, vertex in enumerate(vertices):
            if self._coordinates_match(vertex.coordinates, target_coords):
                return i
        return None

    def _coordinates_match(self, coords1: Tuple[float, float, float], coords2: Tuple[float, float, float], tolerance: float = 1e-6) -> bool:
        """Check if coordinates match within tolerance"""
        return all(abs(a - b) < tolerance for a, b in zip(coords1, coords2))

    def _validate_ifc_file(self, file_path: str) -> bool:
        """Validate IFC file exists and has correct extension"""
        path = Path(file_path)
        return path.exists() and path.suffix.lower() == '.ifc'

    def _calculate_stats(self, graph: TopologicGraph, file_path: str) -> GraphStats:
        """Calculate graph statistics"""
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        
        return GraphStats(
            vertex_count=graph.vertex_count,
            edge_count=graph.edge_count,
            ifc_types=graph.ifc_type_counts,
            file_size_mb=file_size_mb
        )