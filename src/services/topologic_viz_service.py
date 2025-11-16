"""
TopologicPy Visualization Service for Streamlit integration.

Provides native TopologicPy.Show visualization capabilities within Streamlit,
replacing traditional Plotly 3D scatter plots with TopologicPy's advanced
graph visualization features including vertex sizing, IFC grouping, and
embedded rendering.
"""

import logging
import tempfile
import streamlit as st
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

try:
    from topologicpy.Topology import Topology
    from topologicpy.Graph import Graph
    from topologicpy.Dictionary import Dictionary
    from topologicpy.Vertex import Vertex
    TOPOLOGIC_AVAILABLE = True
except ImportError as e:
    logging.warning(f"TopologicPy not available: {e}")
    TOPOLOGIC_AVAILABLE = False
    # Mock classes for development
    class Topology:
        @staticmethod
        def Show(*args, **kwargs):
            raise ImportError("TopologicPy not installed")
    class Graph: pass
    class Dictionary: pass
    class Vertex: pass

from models.topologic_models import TopologicGraph, TopologicVertex


class TopologicVisualizationService:
    """
    Service for TopologicPy native visualization in Streamlit.

    Integrates TopologicPy.Show() functionality directly into Streamlit
    interface, providing advanced graph visualization with IFC metadata
    preservation and interactive controls.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_available = TOPOLOGIC_AVAILABLE

        # Default visualization parameters
        self.default_params = {
            "width": 1024,
            "height": 900,
            "backgroundColor": "white",
            "showVertexLegend": False,
            "showEdgeLegend": False,
            "showFaceLegend": False,
            "faceOpacity": 0.1,
            "sagitta": 0.05,
            "absolute": False
        }

        # IFC type groups for visualization
        self.ifc_vertex_groups = [
            "Unknown", "IfcSpace", "IfcSlab", "IfcRoof", "IfcWall",
            "IfcWallStandardCase", "IfcDoor", "IfcWindow", "IfcFooting",
            "IfcPile", "IfcBuildingElementProxy", "IfcBeam", "IfcColumn"
        ]

        # Create case-insensitive mapping for IFC types
        self.ifc_type_mapping = {}
        for ifc_type in self.ifc_vertex_groups:
            if ifc_type != "Unknown":
                self.ifc_type_mapping[ifc_type.lower()] = ifc_type

    def _normalize_ifc_types_in_graph(self, topologic_graph: Graph) -> Graph:
        """
        Normalize IFC types in graph dictionaries to match expected vertex groups.

        TopologicPy visualization expects exact case matches, but IFC data might
        contain lowercase types like 'ifcwall' instead of 'IfcWall'.
        """
        try:
            vertices = Graph.Vertices(topologic_graph)
            if not vertices:
                return topologic_graph

            for vertex in vertices:
                # Get vertex dictionary
                vertex_dict = Topology.Dictionary(vertex)
                if not vertex_dict:
                    continue

                # Check common IFC type keys and normalize them
                type_keys = ["IFC_type", "ifc_type", "IFCType", "type", "Entity"]
                for key in type_keys:
                    try:
                        current_value = Dictionary.ValueAtKey(vertex_dict, key)
                        if current_value and isinstance(current_value, str):
                            # Convert to lowercase for lookup
                            lookup_key = current_value.lower()
                            # Find proper case version
                            if lookup_key in self.ifc_type_mapping:
                                proper_case = self.ifc_type_mapping[lookup_key]
                                # Update dictionary with proper case
                                vertex_dict = Dictionary.SetValueAtKey(vertex_dict, key, proper_case)
                                vertex = Topology.SetDictionary(vertex, vertex_dict)
                                self.logger.debug(f"Normalized '{current_value}' to '{proper_case}' for key '{key}'")
                            elif current_value not in self.ifc_vertex_groups:
                                # Set to "Unknown" if not recognized
                                vertex_dict = Dictionary.SetValueAtKey(vertex_dict, key, "Unknown")
                                vertex = Topology.SetDictionary(vertex, vertex_dict)
                                self.logger.debug(f"Set unrecognized type '{current_value}' to 'Unknown' for key '{key}'")
                    except Exception as e:
                        self.logger.debug(f"Could not process key '{key}': {e}")

            return topologic_graph

        except Exception as e:
            self.logger.warning(f"Failed to normalize IFC types: {e}")
            return topologic_graph

    def show_graph_visualization(
        self,
        graph_data: Union[TopologicGraph, Graph],
        renderer: str = "browser",
        vertex_size_key: str = "closeness_centrality",
        vertex_label_key: str = "IFC_name",
        vertex_group_key: str = "IFC_type",
        custom_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Display TopologicPy graph visualization in Streamlit.

        Args:
            graph_data: TopologicGraph model or TopologicPy Graph object
            renderer: Visualization renderer ("browser", "jupyterlab", "vscode")
            vertex_size_key: Dictionary key for vertex sizing
            vertex_label_key: Dictionary key for vertex labels
            vertex_group_key: Dictionary key for vertex grouping/coloring
            custom_params: Additional visualization parameters

        Returns:
            Success status
        """
        if not self.is_available:
            st.error("TopologicPy not available - cannot display native visualization")
            return False

        try:
            # Convert TopologicGraph to TopologicPy Graph if needed
            if isinstance(graph_data, TopologicGraph):
                topologic_graph = self._convert_to_topologic_graph(graph_data)
            else:
                topologic_graph = graph_data

            if not topologic_graph:
                st.warning("No graph data available for visualization")
                return False

            # Normalize IFC types to match expected vertex groups
            topologic_graph = self._normalize_ifc_types_in_graph(topologic_graph)

            # Prepare visualization parameters
            viz_params = self.default_params.copy()
            if custom_params:
                viz_params.update(custom_params)

            # Add specific parameters
            viz_params.update({
                "renderer": renderer,
                "vertexSizeKey": vertex_size_key,
                "vertexLabelKey": vertex_label_key,
                "vertexGroupKey": vertex_group_key,
                "vertexGroups": self.ifc_vertex_groups
            })

            # Display in Streamlit
            with st.container():
                st.subheader("TopologicPy Native Visualization")

                # Show renderer info
                st.info(f"🎨 Using TopologicPy.Show with {renderer} renderer")

                # Execute TopologicPy visualization
                try:
                    self.logger.info(f"Displaying TopologicPy visualization with {renderer} renderer")

                    # Call TopologicPy.Show with parameters
                    Topology.Show(
                        topologic_graph,
                        nameKey="IFC_name",
                        vertexSizeKey=vertex_size_key,
                        vertexLabelKey=vertex_label_key,
                        vertexGroupKey=vertex_group_key,
                        vertexGroups=self.ifc_vertex_groups,
                        renderer=renderer,
                        backgroundColor=viz_params["backgroundColor"],
                        width=viz_params["width"],
                        height=viz_params["height"],
                        showVertexLegend=viz_params["showVertexLegend"],
                        showEdgeLegend=viz_params["showEdgeLegend"],
                        showFaceLegend=viz_params["showFaceLegend"],
                        faceOpacity=viz_params["faceOpacity"],
                        sagitta=viz_params["sagitta"],
                        absolute=viz_params["absolute"]
                    )

                    st.success("✅ TopologicPy visualization displayed successfully")
                    return True

                except Exception as viz_error:
                    st.error(f"TopologicPy visualization error: {viz_error}")
                    self.logger.error(f"Visualization failed: {viz_error}")
                    return False

        except Exception as e:
            st.error(f"Failed to prepare TopologicPy visualization: {e}")
            self.logger.error(f"Visualization preparation failed: {e}")
            return False

    def show_graph_with_centrality(
        self,
        graph_data: Union[TopologicGraph, Graph],
        renderer: str = "browser"
    ) -> bool:
        """
        Display graph with closeness centrality analysis.

        Based on the GraphByIFCPath.ipynb pattern with centrality calculation.
        """
        if not self.is_available:
            return False

        try:
            # Convert if needed
            if isinstance(graph_data, TopologicGraph):
                topologic_graph = self._convert_to_topologic_graph(graph_data)
            else:
                topologic_graph = graph_data

            if not topologic_graph:
                return False

            # Normalize IFC types before processing
            topologic_graph = self._normalize_ifc_types_in_graph(topologic_graph)

            # Calculate closeness centrality
            st.info("Calculating closeness centrality...")
            centralities = Graph.ClosenessCentrality(topologic_graph, silent=False)

            # Update vertex dictionaries with centrality
            vertices = Graph.Vertices(topologic_graph)
            for vertex in vertices:
                d = Topology.Dictionary(vertex)
                c = Dictionary.ValueAtKey(d, "closeness_centrality")
                if c is not None:
                    # Scale centrality for visualization (multiply by 20 + 4 as in example)
                    scaled_centrality = c * 20 + 4
                    d = Dictionary.SetValueAtKey(d, "closeness_centrality", scaled_centrality)
                    vertex = Topology.SetDictionary(vertex, d)

            # Display with centrality-based sizing
            return self.show_graph_visualization(
                topologic_graph,
                renderer=renderer,
                vertex_size_key="closeness_centrality",
                vertex_label_key="IFC_name",
                vertex_group_key="IFC_type"
            )

        except Exception as e:
            st.error(f"Failed to calculate centrality: {e}")
            return False

    def _convert_to_topologic_graph(self, graph_model: TopologicGraph) -> Optional[Graph]:
        """
        Convert TopologicGraph model back to TopologicPy Graph object.

        This is a complex conversion that would need to rebuild the TopologicPy
        Graph from stored vertices and edges. For now, we'll need to store
        the original TopologicPy Graph object for visualization.
        """
        # TODO: Implement conversion from TopologicGraph back to TopologicPy Graph
        # This is complex and may require storing the original Graph object
        # in session state or implementing a full reconstruction method

        self.logger.warning("Conversion from TopologicGraph to TopologicPy Graph not yet implemented")
        self.logger.info("Consider storing original TopologicPy Graph in session state for visualization")

        # For now, return None and require original Graph object
        return None

    def get_available_renderers(self) -> List[str]:
        """Get list of available TopologicPy renderers"""
        return ["browser", "jupyterlab", "vscode"]

    def validate_renderer(self, renderer: str) -> bool:
        """Validate renderer choice"""
        return renderer in self.get_available_renderers()

    def get_visualization_info(self) -> Dict[str, Any]:
        """Get information about TopologicPy visualization capabilities"""
        return {
            "available": self.is_available,
            "renderers": self.get_available_renderers(),
            "features": [
                "Native TopologicPy.Show integration",
                "IFC metadata-based vertex sizing",
                "IFC type-based vertex grouping and coloring",
                "Closeness centrality analysis",
                "Interactive 3D graph visualization",
                "Multiple renderer support"
            ],
            "vertex_groups": self.ifc_vertex_groups,
            "default_params": self.default_params
        }