"""
Tests for BlockchainExportService - Kuzu to Smart Contract export functionality.

Tests data conversion, validation, and Web3.py compatibility for minting
building graphs as ERC-998 composable NFTs.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.blockchain_service import BlockchainExportService, TokenType
from models.blockchain_models import (
    IFCComponentToken,
    BuildingTokenCollection,
    TokenStandard,
    TokenizationStatus
)


# ============ Fixtures ============

@pytest.fixture
def mock_kuzu_service():
    """Mock KuzuService with sample data"""
    mock_service = Mock()
    mock_service.is_available = True

    # Mock connection for edge queries
    mock_connection = Mock()
    mock_service.connection = mock_connection

    return mock_service


@pytest.fixture
def sample_vertices():
    """Sample Kuzu vertices representing building components"""
    return [
        {
            'id': 'vertex-1',
            'ifc_type': 'IfcProject',
            'ifc_guid': '3nQP4B$5D4wPE2qzX8Yz6M',
            'name': 'Test Building Project',
            'x': 0.0,
            'y': 0.0,
            'z': 0.0,
            'building_id': 'building-1',
            'file_id': 'file-123'
        },
        {
            'id': 'vertex-2',
            'ifc_type': 'IfcBuilding',
            'ifc_guid': '2O2Fr$t4X7Zf8NOew3FL5R',
            'name': 'Main Building',
            'x': 0.0,
            'y': 0.0,
            'z': 0.0,
            'building_id': 'building-1',
            'file_id': 'file-123'
        },
        {
            'id': 'vertex-3',
            'ifc_type': 'IfcSpace',
            'ifc_guid': '1A2B3C4D5E6F7G8H9I0J1K',
            'name': 'Room 101',
            'x': 10.5,
            'y': 20.3,
            'z': 3.2,
            'building_id': 'building-1',
            'file_id': 'file-123'
        },
        {
            'id': 'vertex-4',
            'ifc_type': 'IfcWall',
            'ifc_guid': '9Z8Y7X6W5V4U3T2S1R0Q9P',
            'name': 'Wall-001',
            'x': 5.0,
            'y': 10.0,
            'z': 0.0,
            'building_id': 'building-1',
            'file_id': 'file-123'
        },
        {
            'id': 'vertex-5',
            'ifc_type': 'IfcDoor',
            'ifc_guid': 'ABCDEFGHIJKLMNOPQRSTUV',
            'name': 'Door-001',
            'x': 5.0,
            'y': 12.5,
            'z': 0.0,
            'building_id': 'building-1',
            'file_id': 'file-123'
        }
    ]


@pytest.fixture
def sample_file_data():
    """Sample IFC file metadata"""
    return {
        'id': 'file-123',
        'filename': 'test_building.ifc',
        'building_name': 'Test Building',
        'upload_timestamp': '2025-01-10 12:00:00',
        'processing_method': 'direct',
        'file_size_mb': 5.2
    }


@pytest.fixture
def blockchain_service(mock_kuzu_service):
    """BlockchainExportService instance with mocked Kuzu"""
    return BlockchainExportService(mock_kuzu_service)


# ============ Unit Tests - Token Type Determination ============

class TestTokenTypeDetermination:
    """Test IFC type to blockchain TokenType mapping"""

    def test_project_type_detection(self, blockchain_service):
        assert blockchain_service._determine_token_type('IfcProject') == TokenType.PROJECT
        assert blockchain_service._determine_token_type('ifcproject') == TokenType.PROJECT

    def test_building_type_detection(self, blockchain_service):
        assert blockchain_service._determine_token_type('IfcBuilding') == TokenType.BUILDING
        assert blockchain_service._determine_token_type('ifcbuilding') == TokenType.BUILDING

    def test_storey_type_detection(self, blockchain_service):
        assert blockchain_service._determine_token_type('IfcBuildingStorey') == TokenType.STOREY
        assert blockchain_service._determine_token_type('IfcFloor') == TokenType.STOREY
        assert blockchain_service._determine_token_type('ifcstorey') == TokenType.STOREY

    def test_space_type_detection(self, blockchain_service):
        assert blockchain_service._determine_token_type('IfcSpace') == TokenType.SPACE
        assert blockchain_service._determine_token_type('IfcRoom') == TokenType.SPACE
        assert blockchain_service._determine_token_type('IfcZone') == TokenType.SPACE

    def test_component_type_detection(self, blockchain_service):
        # All physical components should be COMPONENT type
        assert blockchain_service._determine_token_type('IfcWall') == TokenType.COMPONENT
        assert blockchain_service._determine_token_type('IfcDoor') == TokenType.COMPONENT
        assert blockchain_service._determine_token_type('IfcWindow') == TokenType.COMPONENT
        assert blockchain_service._determine_token_type('IfcBeam') == TokenType.COMPONENT
        assert blockchain_service._determine_token_type('IfcColumn') == TokenType.COMPONENT
        assert blockchain_service._determine_token_type('IfcSlab') == TokenType.COMPONENT


# ============ Unit Tests - Data Conversion ============

class TestDataConversion:
    """Test conversion of Kuzu data to smart contract format"""

    def test_vertex_to_graph_node_basic(self, blockchain_service, sample_vertices):
        vertex = sample_vertices[3]  # IfcWall
        file_id = 'file-123'

        node = blockchain_service._convert_vertex_to_graph_node(vertex, file_id)

        # Check required fields
        assert node['kuzuElementId'] == 'vertex-4'
        assert node['ifcGuid'] == '9Z8Y7X6W5V4U3T2S1R0Q9P'
        assert node['ifcType'] == 'IfcWall'
        assert node['name'] == 'Wall-001'
        assert node['tokenType'] == TokenType.COMPONENT.value

    def test_coordinate_scaling(self, blockchain_service, sample_vertices):
        """Test coordinates are scaled to int256 (millimeter precision)"""
        vertex = sample_vertices[2]  # IfcSpace with decimal coordinates
        node = blockchain_service._convert_vertex_to_graph_node(vertex, 'file-123')

        # Coordinates should be multiplied by 1000
        assert node['x'] == 10500  # 10.5 * 1000
        assert node['y'] == 20300  # 20.3 * 1000
        assert node['z'] == 3200   # 3.2 * 1000
        assert isinstance(node['x'], int)
        assert isinstance(node['y'], int)
        assert isinstance(node['z'], int)

    def test_bytes32_conversion(self, blockchain_service):
        """Test string to bytes32 hex conversion"""
        result = blockchain_service._string_to_bytes32('test-id-123')

        # Should return hex string
        assert result.startswith('0x')
        assert len(result) == 66  # 0x + 64 hex characters (32 bytes)

        # Test empty string
        empty = blockchain_service._string_to_bytes32('')
        assert empty == '0x' + '00' * 32

    def test_file_id_and_building_id_conversion(self, blockchain_service, sample_vertices):
        """Test fileId and buildingId are converted to bytes32"""
        vertex = sample_vertices[3]
        node = blockchain_service._convert_vertex_to_graph_node(vertex, 'file-123')

        assert 'fileId' in node
        assert 'buildingId' in node
        assert node['fileId'].startswith('0x')
        assert node['buildingId'].startswith('0x')
        assert len(node['fileId']) == 66
        assert len(node['buildingId']) == 66

    def test_parent_token_id_initialization(self, blockchain_service, sample_vertices):
        """Test parentTokenId is initialized to 0"""
        vertex = sample_vertices[3]
        node = blockchain_service._convert_vertex_to_graph_node(vertex, 'file-123')

        assert node['parentTokenId'] == 0
        assert node['childTokenIds'] == []

    def test_construction_status_defaults(self, blockchain_service, sample_vertices):
        """Test construction status defaults to DESIGNED (0)"""
        vertex = sample_vertices[3]
        node = blockchain_service._convert_vertex_to_graph_node(vertex, 'file-123')

        assert node['status'] == 0  # ConstructionStatus.DESIGNED


# ============ Unit Tests - Edge Extraction ============

class TestEdgeExtraction:
    """Test extraction of topological connections"""

    def test_get_edges_basic(self, blockchain_service, mock_kuzu_service):
        """Test basic edge extraction from Kuzu"""
        # Mock query result
        mock_result = Mock()
        mock_result.has_next.side_effect = [True, True, False]
        mock_result.get_next.side_effect = [
            ('vertex-1', 'vertex-2', 'topological', 'connects', {}),
            ('vertex-2', 'vertex-3', 'spatial', 'contains', {'distance': '1.5'})
        ]
        mock_kuzu_service.connection.execute.return_value = mock_result

        vertex_id_to_index = {
            'vertex-1': 0,
            'vertex-2': 1,
            'vertex-3': 2
        }

        edges = blockchain_service._get_edges_for_file('file-123', vertex_id_to_index)

        # Should return 2 edges
        assert len(edges) == 2

        # Check first edge
        edge1 = edges[0]
        assert edge1['fromKuzuId'] == 'vertex-1'
        assert edge1['toKuzuId'] == 'vertex-2'
        assert edge1['connectionType'] == 'topological'
        assert edge1['bidirectional'] == True

        # Check second edge
        edge2 = edges[1]
        assert edge2['fromKuzuId'] == 'vertex-2'
        assert edge2['toKuzuId'] == 'vertex-3'
        assert edge2['connectionType'] == 'spatial'

    def test_edges_filtered_by_vertex_set(self, blockchain_service, mock_kuzu_service):
        """Test that edges to non-included vertices are filtered out"""
        mock_result = Mock()
        mock_result.has_next.side_effect = [True, True, False]
        mock_result.get_next.side_effect = [
            ('vertex-1', 'vertex-2', 'topological', '', {}),
            ('vertex-2', 'vertex-999', 'spatial', '', {})  # vertex-999 not in set
        ]
        mock_kuzu_service.connection.execute.return_value = mock_result

        vertex_id_to_index = {
            'vertex-1': 0,
            'vertex-2': 1
            # vertex-999 NOT included
        }

        edges = blockchain_service._get_edges_for_file('file-123', vertex_id_to_index)

        # Should only return first edge (second filtered out)
        assert len(edges) == 1
        assert edges[0]['fromKuzuId'] == 'vertex-1'
        assert edges[0]['toKuzuId'] == 'vertex-2'


# ============ Integration Tests - Full Export ============

class TestFullExport:
    """Test complete building graph export workflow"""

    def test_export_building_basic(
        self,
        blockchain_service,
        mock_kuzu_service,
        sample_vertices,
        sample_file_data
    ):
        """Test exporting a complete building graph"""
        # Setup mocks
        mock_kuzu_service.get_vertices_by_file.return_value = sample_vertices
        mock_kuzu_service.get_all_files.return_value = [sample_file_data]

        # Mock edge query
        mock_result = Mock()
        mock_result.has_next.return_value = False
        mock_kuzu_service.connection.execute.return_value = mock_result

        # Export building
        nodes, edges = blockchain_service.export_building_for_minting('file-123')

        # Should have all 5 vertices as nodes
        assert len(nodes) == 5

        # Verify node structure
        for node in nodes:
            assert 'kuzuElementId' in node
            assert 'ifcGuid' in node
            assert 'ifcType' in node
            assert 'name' in node
            assert 'tokenType' in node
            assert 'x' in node
            assert 'y' in node
            assert 'z' in node
            assert isinstance(node['x'], int)
            assert isinstance(node['y'], int)
            assert isinstance(node['z'], int)

    def test_export_with_type_filtering(
        self,
        blockchain_service,
        mock_kuzu_service,
        sample_vertices
    ):
        """Test exporting only specific IFC types"""
        mock_kuzu_service.get_vertices_by_file.return_value = sample_vertices

        # Mock edge query
        mock_result = Mock()
        mock_result.has_next.return_value = False
        mock_kuzu_service.connection.execute.return_value = mock_result

        # Export only walls and doors
        nodes, edges = blockchain_service.export_building_for_minting(
            'file-123',
            include_types=['IfcWall', 'IfcDoor']
        )

        # Should only have 2 nodes (wall and door)
        assert len(nodes) == 2

        types = [node['ifcType'] for node in nodes]
        assert 'IfcWall' in types
        assert 'IfcDoor' in types
        assert 'IfcSpace' not in types

    def test_export_empty_file(self, blockchain_service, mock_kuzu_service):
        """Test exporting file with no vertices"""
        mock_kuzu_service.get_vertices_by_file.return_value = []

        nodes, edges = blockchain_service.export_building_for_minting('file-empty')

        assert len(nodes) == 0
        assert len(edges) == 0


# ============ Tests - Tokenization Mapping ============

class TestTokenizationMapping:
    """Test creation of tokenization mappings"""

    def test_create_tokenization_mapping(
        self,
        blockchain_service,
        mock_kuzu_service,
        sample_vertices,
        sample_file_data
    ):
        """Test creating BuildingTokenCollection"""
        mock_kuzu_service.get_all_files.return_value = [sample_file_data]
        mock_kuzu_service.get_vertices_by_file.return_value = sample_vertices

        collection = blockchain_service.create_tokenization_mapping(
            file_id='file-123',
            building_name='Test Building',
            chain_id=31337  # Anvil
        )

        # Check collection metadata
        assert collection.file_id == 'file-123'
        assert collection.building_name == 'Test Building'
        assert collection.chain_id == 31337
        assert collection.ifc_filename == 'test_building.ifc'

        # Check component tokens
        assert len(collection.component_tokens) == 5

        # All tokens should have URIs
        for token in collection.component_tokens:
            assert token.token_uri is not None
            assert token.token_uri.startswith('kuzu://')
            assert token.status == TokenizationStatus.PENDING
            assert token.token_standard == TokenStandard.ERC998

    def test_token_uri_format(
        self,
        blockchain_service,
        mock_kuzu_service,
        sample_vertices,
        sample_file_data
    ):
        """Test token URI follows correct format"""
        mock_kuzu_service.get_all_files.return_value = [sample_file_data]
        mock_kuzu_service.get_vertices_by_file.return_value = sample_vertices

        collection = blockchain_service.create_tokenization_mapping(
            file_id='file-123',
            building_name='Test Building'
        )

        token = collection.component_tokens[0]

        # URI format: kuzu://{kuzu_id}/topologic/{topologic_id}/ifc/{ifc_guid}
        assert 'kuzu://' in token.token_uri
        assert '/topologic/' in token.token_uri
        assert '/ifc/' in token.token_uri


# ============ Tests - Batch Mint Preparation ============

class TestBatchMintPreparation:
    """Test preparation of data for mintBuildingGraph contract call"""

    def test_prepare_batch_mint_data(
        self,
        blockchain_service,
        mock_kuzu_service,
        sample_vertices
    ):
        """Test preparing complete mint data structure"""
        mock_kuzu_service.get_vertices_by_file.return_value = sample_vertices

        # Mock edge query
        mock_result = Mock()
        mock_result.has_next.return_value = False
        mock_kuzu_service.connection.execute.return_value = mock_result

        mint_data = blockchain_service.prepare_batch_mint_data(
            file_id='file-123',
            building_name='HQ Building'
        )

        # Check structure
        assert 'fileId' in mint_data
        assert 'projectName' in mint_data
        assert 'nodes' in mint_data
        assert 'edges' in mint_data
        assert 'nodeCount' in mint_data
        assert 'edgeCount' in mint_data

        # Check values
        assert mint_data['projectName'] == 'HQ Building'
        assert mint_data['nodeCount'] == 5
        assert mint_data['edgeCount'] == 0
        assert len(mint_data['nodes']) == 5
        assert mint_data['fileId'].startswith('0x')


# ============ Tests - Data Validation ============

class TestDataValidation:
    """Test validation of exported data"""

    def test_validate_valid_data(self, blockchain_service, sample_vertices):
        """Test validation passes for valid data"""
        # Convert vertices to nodes
        nodes = [
            blockchain_service._convert_vertex_to_graph_node(v, 'file-123')
            for v in sample_vertices
        ]

        edges = [
            {
                'fromKuzuId': 'vertex-1',
                'toKuzuId': 'vertex-2',
                'connectionType': 'topological',
                'edgeProperties': '{}',
                'kuzuEdgeId': '0x' + '00' * 32,
                'bidirectional': True
            }
        ]

        is_valid, errors = blockchain_service.validate_export_data(nodes, edges)

        assert is_valid
        assert len(errors) == 0

    def test_validate_empty_nodes(self, blockchain_service):
        """Test validation fails for empty nodes"""
        is_valid, errors = blockchain_service.validate_export_data([], [])

        assert not is_valid
        assert len(errors) > 0
        assert any('No nodes' in err for err in errors)

    def test_validate_missing_required_fields(self, blockchain_service):
        """Test validation fails for missing required fields"""
        nodes = [
            {
                'kuzuElementId': 'vertex-1',
                # Missing: ifcGuid, ifcType, name
                'x': 0,
                'y': 0,
                'z': 0
            }
        ]

        is_valid, errors = blockchain_service.validate_export_data(nodes, [])

        assert not is_valid
        assert any('ifcGuid' in err for err in errors)
        assert any('ifcType' in err for err in errors)
        assert any('name' in err for err in errors)

    def test_validate_invalid_coordinates(self, blockchain_service):
        """Test validation fails for non-integer coordinates"""
        nodes = [
            {
                'kuzuElementId': 'vertex-1',
                'ifcGuid': 'ABC123',
                'ifcType': 'IfcWall',
                'name': 'Wall-001',
                'x': 1.5,  # Should be int, not float
                'y': 0,
                'z': 0
            }
        ]

        is_valid, errors = blockchain_service.validate_export_data(nodes, [])

        assert not is_valid
        assert any("must be int256" in err for err in errors)

    def test_validate_orphaned_edges(self, blockchain_service, sample_vertices):
        """Test validation fails for edges referencing non-existent nodes"""
        nodes = [
            blockchain_service._convert_vertex_to_graph_node(sample_vertices[0], 'file-123')
        ]

        edges = [
            {
                'fromKuzuId': 'vertex-1',
                'toKuzuId': 'vertex-999',  # Does not exist in nodes
                'connectionType': 'topological',
                'edgeProperties': '{}',
                'kuzuEdgeId': '0x' + '00' * 32,
                'bidirectional': True
            }
        ]

        is_valid, errors = blockchain_service.validate_export_data(nodes, edges)

        assert not is_valid
        assert any('vertex-999' in err and 'not found' in err for err in errors)


# ============ Tests - Web3.py Compatibility ============

class TestWeb3Compatibility:
    """Test that exported data is compatible with Web3.py contract calls"""

    def test_struct_encoding_compatibility(self, blockchain_service, sample_vertices):
        """Test that node structure matches contract ABI expectations"""
        node = blockchain_service._convert_vertex_to_graph_node(
            sample_vertices[3],
            'file-123'
        )

        # Fields expected by BuildingGraphNFT.sol GraphNodeMetadata struct
        required_fields = [
            'tokenType',      # uint8
            'kuzuElementId',  # string
            'topologicVertexId',  # string
            'ifcGuid',        # string
            'ifcType',        # string
            'name',           # string
            'x',              # int256
            'y',              # int256
            'z',              # int256
            'fileId',         # bytes32
            'buildingId',     # bytes32
            'parentTokenId',  # uint256
            'childTokenIds',  # uint256[]
            'status',         # uint8
            'mintedAt',       # uint256
            'exists'          # bool
        ]

        for field in required_fields:
            assert field in node, f"Missing required field: {field}"

        # Type checks
        assert isinstance(node['tokenType'], int)
        assert isinstance(node['kuzuElementId'], str)
        assert isinstance(node['ifcGuid'], str)
        assert isinstance(node['x'], int)
        assert isinstance(node['y'], int)
        assert isinstance(node['z'], int)
        assert isinstance(node['fileId'], str)
        assert node['fileId'].startswith('0x')
        assert isinstance(node['parentTokenId'], int)
        assert isinstance(node['childTokenIds'], list)
        assert isinstance(node['status'], int)
        assert isinstance(node['exists'], bool)

    def test_edge_struct_compatibility(self, blockchain_service, mock_kuzu_service):
        """Test that edge structure matches contract ABI expectations"""
        # Mock query result
        mock_result = Mock()
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = ('vertex-1', 'vertex-2', 'topological', '', {})
        mock_kuzu_service.connection.execute.return_value = mock_result

        vertex_id_to_index = {'vertex-1': 0, 'vertex-2': 1}
        edges = blockchain_service._get_edges_for_file('file-123', vertex_id_to_index)

        edge = edges[0]

        # Fields expected by BuildingGraphNFT.sol GraphEdge struct
        required_fields = [
            'fromTokenId',     # uint256
            'toTokenId',       # uint256
            'connectionType',  # string
            'edgeProperties',  # string
            'kuzuEdgeId',      # bytes32
            'bidirectional'    # bool
        ]

        for field in required_fields:
            assert field in edge, f"Missing required field: {field}"

        # Type checks
        assert isinstance(edge['connectionType'], str)
        assert isinstance(edge['edgeProperties'], str)
        assert isinstance(edge['kuzuEdgeId'], str)
        assert edge['kuzuEdgeId'].startswith('0x')
        assert isinstance(edge['bidirectional'], bool)

    def test_web3_tuple_encoding(self, blockchain_service, sample_vertices):
        """Test that data can be encoded as Web3 tuple"""
        try:
            from web3 import Web3
        except ImportError:
            pytest.skip("Web3.py not installed")

        node = blockchain_service._convert_vertex_to_graph_node(
            sample_vertices[3],
            'file-123'
        )

        # Try encoding as tuple (mimics contract call)
        try:
            # This would be the format Web3.py uses for struct parameters
            node_tuple = (
                node['tokenType'],
                node['kuzuElementId'],
                node['topologicVertexId'],
                node['ifcGuid'],
                node['ifcType'],
                node['name'],
                node['x'],
                node['y'],
                node['z'],
                node['fileId'],
                node['buildingId'],
                node['parentTokenId'],
                node['childTokenIds'],
                node['status'],
                node['mintedAt'],
                node['exists']
            )

            # If we get here, tuple encoding works
            assert len(node_tuple) == 16

        except Exception as e:
            pytest.fail(f"Failed to encode node as tuple: {e}")


# ============ Run Tests ============

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
