"""
Basic tests for IFC TopologicPy Kuzu pipeline.

Tests the core functionality without requiring actual IFC files or TopologicPy installation.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from models.data_models import ProcessingConfig, ProcessingMethod, GraphStats
from models.topologic_models import TopologicVertex, TopologicEdge, TopologicGraph
from models.kuzu_models import KuzuVertex, KuzuEdge, KuzuSchema


class TestDataModels:
    """Test data model functionality"""
    
    def test_processing_config_creation(self):
        """Test ProcessingConfig creation"""
        config = ProcessingConfig(
            method=ProcessingMethod.DIRECT,
            include_types=["IfcWall", "IfcSpace"],
            transfer_dictionaries=True,
            tolerance=0.001
        )
        
        assert config.method == ProcessingMethod.DIRECT
        assert "IfcWall" in config.include_types
        assert config.transfer_dictionaries is True
        assert config.tolerance == 0.001
    
    def test_topologic_vertex_creation(self):
        """Test TopologicVertex creation and metadata extraction"""
        vertex = TopologicVertex(
            coordinates=(1.0, 2.0, 3.0),
            dictionaries={
                "IFC_type": "IfcWall",
                "IFC_global_id": "test-guid-123",
                "Name": "Test Wall"
            }
        )
        
        vertex.extract_ifc_metadata()
        
        assert vertex.coordinates == (1.0, 2.0, 3.0)
        assert vertex.ifc_type == "IfcWall"
        assert vertex.ifc_guid == "test-guid-123"
        assert vertex.ifc_name == "Test Wall"
    
    def test_topologic_graph_statistics(self):
        """Test TopologicGraph statistics calculation"""
        vertices = [
            TopologicVertex(coordinates=(0, 0, 0), dictionaries={"IFC_type": "IfcWall"}),
            TopologicVertex(coordinates=(1, 1, 1), dictionaries={"IFC_type": "IfcWall"}),
            TopologicVertex(coordinates=(2, 2, 2), dictionaries={"IFC_type": "IfcSpace"})
        ]
        
        for v in vertices:
            v.extract_ifc_metadata()
        
        edges = [
            TopologicEdge(
                start_vertex_id=vertices[0].id,
                end_vertex_id=vertices[1].id,
                dictionaries={"connection_type": "adjacent"}
            )
        ]
        
        graph = TopologicGraph(vertices=vertices, edges=edges)
        graph.update_statistics()
        
        assert graph.vertex_count == 3
        assert graph.edge_count == 1
        assert graph.ifc_type_counts["IfcWall"] == 2
        assert graph.ifc_type_counts["IfcSpace"] == 1
    
    def test_kuzu_vertex_conversion(self):
        """Test KuzuVertex parameter conversion"""
        vertex = KuzuVertex(
            id="test-id",
            ifc_type="IfcWall",
            ifc_guid="guid-123",
            name="Test Wall",
            x=1.0, y=2.0, z=3.0,
            properties={"material": "concrete"}
        )
        
        params = vertex.to_kuzu_params()
        
        assert params["id"] == "test-id"
        assert params["ifc_type"] == "IfcWall"
        assert params["x"] == 1.0
        assert params["properties"]["material"] == "concrete"


class TestKuzuSchema:
    """Test Kuzu schema generation"""
    
    def test_schema_statements_generation(self):
        """Test CREATE TABLE statements generation"""
        statements = KuzuSchema.get_create_table_statements()
        
        assert len(statements) > 0
        
        # Check that main tables are included
        statement_text = " ".join(statements)
        assert "IfcElement" in statement_text
        assert "TopologicalConnection" in statement_text
        assert "SpatialContainment" in statement_text
    
    def test_index_statements_generation(self):
        """Test CREATE INDEX statements generation"""
        index_statements = KuzuSchema.get_index_statements()
        
        assert len(index_statements) > 0
        
        # Check for key indexes
        index_text = " ".join(index_statements)
        assert "idx_ifc_type" in index_text
        assert "idx_ifc_guid" in index_text


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_file_handling(self):
        """Test handling of invalid file paths"""
        from services.ifc_processor import IFCProcessorService
        
        processor = IFCProcessorService()
        
        # Test with non-existent file
        assert not processor._validate_ifc_file("non_existent_file.ifc")
        
        # Test with wrong extension
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            assert not processor._validate_ifc_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_coordinate_matching(self):
        """Test coordinate matching tolerance"""
        from services.ifc_processor import IFCProcessorService
        
        processor = IFCProcessorService()
        
        # Test exact match
        assert processor._coordinates_match((1.0, 2.0, 3.0), (1.0, 2.0, 3.0))
        
        # Test within tolerance
        assert processor._coordinates_match((1.0, 2.0, 3.0), (1.000001, 2.0, 3.0))
        
        # Test outside tolerance
        assert not processor._coordinates_match((1.0, 2.0, 3.0), (1.1, 2.0, 3.0))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])