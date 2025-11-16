"""
Blockchain Export Service for IFC Building Graphs.

Converts Kuzu graph database data into smart contract-compatible format
for minting ERC-998 composable NFTs on Ethereum blockchain.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from models.blockchain_models import (
    IFCComponentToken,
    BuildingTokenCollection,
    TokenizationMapping,
    TokenStandard,
    TokenizationStatus
)


class TokenType(Enum):
    """Token types matching BuildingGraphNFT.sol"""
    PROJECT = 0
    BUILDING = 1
    STOREY = 2
    SPACE = 3
    COMPONENT = 4


class BlockchainExportService:
    """
    Service for exporting Kuzu graph data to blockchain-compatible format.

    Converts IFC building components from Kuzu database into GraphNodeMetadata
    and GraphEdge structs compatible with BuildingGraphNFT.sol smart contract.
    """

    def __init__(self, kuzu_service):
        """
        Initialize blockchain export service.

        Args:
            kuzu_service: KuzuService instance for database queries
        """
        self.logger = logging.getLogger(__name__)
        self.kuzu_service = kuzu_service

    def export_building_for_minting(
        self,
        file_id: str,
        include_types: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Export complete building graph from Kuzu for blockchain minting.

        Retrieves all elements and relationships for a specific IFC file
        and converts them to smart contract-compatible format.

        Args:
            file_id: IFC file ID in Kuzu database
            include_types: Optional list of IFC types to include (filters elements)

        Returns:
            Tuple of (nodes, edges) as dictionaries ready for contract encoding

        Example:
            >>> nodes, edges = service.export_building_for_minting("file-123")
            >>> # nodes: List of GraphNodeMetadata dicts
            >>> # edges: List of GraphEdge dicts
        """
        try:
            self.logger.info(f"Exporting building graph for file_id: {file_id}")

            # Get all vertices (elements) for this file
            vertices = self.kuzu_service.get_vertices_by_file(file_id)

            if not vertices:
                self.logger.warning(f"No vertices found for file_id: {file_id}")
                return ([], [])

            # Filter by IFC type if specified
            if include_types:
                normalized_types = [t.lower() for t in include_types]
                vertices = [
                    v for v in vertices
                    if v.get('ifc_type', '').lower() in normalized_types
                ]
                self.logger.info(f"Filtered to {len(vertices)} vertices of types: {include_types}")

            # Convert vertices to GraphNodeMetadata format
            nodes = []
            vertex_id_to_index = {}  # Map vertex ID to array index for parent-child lookup

            for idx, vertex in enumerate(vertices):
                node = self._convert_vertex_to_graph_node(vertex, file_id)
                nodes.append(node)
                vertex_id_to_index[vertex['id']] = idx

            # Get edges (relationships) for this file
            edges = self._get_edges_for_file(file_id, vertex_id_to_index)

            self.logger.info(f"Exported {len(nodes)} nodes and {len(edges)} edges")
            return (nodes, edges)

        except Exception as e:
            self.logger.error(f"Failed to export building for minting: {e}", exc_info=True)
            return ([], [])

    def _convert_vertex_to_graph_node(
        self,
        vertex: Dict[str, Any],
        file_id: str
    ) -> Dict[str, Any]:
        """
        Convert Kuzu vertex to GraphNodeMetadata struct format.

        Maps Kuzu IfcElement data to the smart contract's GraphNodeMetadata struct
        with proper type encoding and coordinate scaling.

        Args:
            vertex: Kuzu vertex data dict
            file_id: IFC file identifier

        Returns:
            GraphNodeMetadata dict compatible with smart contract
        """
        # Determine token type based on IFC type
        ifc_type = vertex.get('ifc_type', '').lower()
        token_type = self._determine_token_type(ifc_type)

        # Convert coordinates to int256 (scale by 1000 for millimeter precision)
        x = int(vertex.get('x', 0.0) * 1000)
        y = int(vertex.get('y', 0.0) * 1000)
        z = int(vertex.get('z', 0.0) * 1000)

        # Convert file_id and building_id to bytes32 format
        file_id_bytes32 = self._string_to_bytes32(file_id)
        building_id_bytes32 = self._string_to_bytes32(vertex.get('building_id', ''))

        # Build GraphNodeMetadata struct
        node = {
            'tokenType': token_type.value,
            'kuzuElementId': vertex.get('id', ''),
            'topologicVertexId': vertex.get('id', ''),  # Kuzu ID used as topologic reference
            'ifcGuid': vertex.get('ifc_guid', ''),
            'ifcType': vertex.get('ifc_type', 'Unknown'),
            'name': vertex.get('name', 'Unnamed'),
            'x': x,
            'y': y,
            'z': z,
            'fileId': file_id_bytes32,
            'buildingId': building_id_bytes32,
            'parentTokenId': 0,  # Will be computed later based on hierarchy
            'childTokenIds': [],  # Will be populated after minting
            'status': 0,  # ConstructionStatus.DESIGNED
            'mintedAt': 0,  # Will be set by contract
            'exists': False  # Will be set to true by contract on mint
        }

        return node

    def _determine_token_type(self, ifc_type: str) -> TokenType:
        """
        Determine blockchain token type from IFC type string.

        Maps IFC entity types to the 5-level hierarchy:
        PROJECT → BUILDING → STOREY → SPACE → COMPONENT

        Args:
            ifc_type: IFC entity type (e.g., "IfcWall", "IfcSpace")

        Returns:
            TokenType enum value
        """
        ifc_type_lower = ifc_type.lower()

        if 'project' in ifc_type_lower:
            return TokenType.PROJECT
        elif 'building' in ifc_type_lower and 'storey' not in ifc_type_lower:
            return TokenType.BUILDING
        elif 'storey' in ifc_type_lower or 'floor' in ifc_type_lower:
            return TokenType.STOREY
        elif 'space' in ifc_type_lower or 'room' in ifc_type_lower or 'zone' in ifc_type_lower:
            return TokenType.SPACE
        else:
            # Everything else is a component (walls, doors, windows, beams, etc.)
            return TokenType.COMPONENT

    def _get_edges_for_file(
        self,
        file_id: str,
        vertex_id_to_index: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """
        Get all edges (relationships) for a file and convert to GraphEdge format.

        Queries Kuzu for TopologicalConnection relationships and converts them
        to smart contract-compatible GraphEdge structs.

        Args:
            file_id: IFC file identifier
            vertex_id_to_index: Mapping of vertex IDs to their indices

        Returns:
            List of GraphEdge dicts
        """
        edges = []

        try:
            # Query for all topological connections within this file
            query = """
            MATCH (a:IfcElement {file_id: $file_id})-[r:TopologicalConnection]->(b:IfcElement {file_id: $file_id})
            RETURN a.id, b.id, r.connection_type, r.edge_type, r.properties
            """

            result = self.kuzu_service.connection.execute(query, {"file_id": file_id})

            edge_counter = 0
            while result.has_next():
                row = result.get_next()
                from_id = row[0]
                to_id = row[1]
                connection_type = row[2] or "topological"
                edge_type = row[3] or ""
                properties = row[4] if len(row) > 4 else {}

                # Only include edges where both vertices are in our export
                if from_id in vertex_id_to_index and to_id in vertex_id_to_index:
                    edge = {
                        'fromTokenId': 0,  # Will be resolved by contract during minting
                        'toTokenId': 0,    # Will be resolved by contract during minting
                        'fromIndex': vertex_id_to_index[from_id],  # Array index for resolution
                        'toIndex': vertex_id_to_index[to_id],      # Array index for resolution
                        'connectionType': connection_type,
                        'edgeProperties': str(properties) if properties else "{}",
                        'kuzuEdgeId': self._string_to_bytes32(f"edge_{edge_counter}"),
                        'bidirectional': True  # Most topological connections are bidirectional
                    }
                    edges.append(edge)
                    edge_counter += 1

            self.logger.info(f"Found {len(edges)} edges for file {file_id}")

        except Exception as e:
            self.logger.error(f"Failed to get edges for file: {e}", exc_info=True)

        return edges

    def _string_to_bytes32(self, text: str) -> str:
        """
        Convert string to bytes32 hex format for Solidity.

        Pads or truncates string to 32 bytes and returns hex string.

        Args:
            text: String to convert

        Returns:
            Hex string starting with '0x', 66 characters total (0x + 64 hex digits)
        """
        if not text:
            return "0x" + "00" * 32

        # Convert to bytes and pad/truncate to 32 bytes
        text_bytes = text.encode('utf-8')[:32]
        padded = text_bytes.ljust(32, b'\x00')

        return "0x" + padded.hex()

    def create_tokenization_mapping(
        self,
        file_id: str,
        building_name: str,
        contract_address: Optional[str] = None,
        chain_id: int = 31337  # Default to Anvil local chain
    ) -> BuildingTokenCollection:
        """
        Create tokenization mapping for a building before minting.

        Generates IFCComponentToken instances for each element in the building
        and organizes them into a BuildingTokenCollection with proper token URIs.

        Args:
            file_id: IFC file ID in Kuzu database
            building_name: Name of the building/collection
            contract_address: Smart contract address (if already deployed)
            chain_id: Blockchain network ID (1=mainnet, 11155111=Sepolia, 31337=Anvil)

        Returns:
            BuildingTokenCollection with all component tokens
        """
        try:
            # Get file data
            files = self.kuzu_service.get_all_files()
            file_data = next((f for f in files if f['id'] == file_id), None)

            if not file_data:
                raise ValueError(f"File {file_id} not found in database")

            filename = file_data.get('filename', 'unknown.ifc')

            # Get all vertices for this file
            vertices = self.kuzu_service.get_vertices_by_file(file_id)

            # Create collection
            collection = BuildingTokenCollection(
                file_id=file_id,
                building_name=building_name,
                ifc_filename=filename,
                collection_name=f"{building_name} Digital Twin",
                collection_symbol="BLDG",
                collection_description=f"Tokenized building components from {filename}",
                contract_address=contract_address,
                chain_id=chain_id
            )

            # Create component tokens
            for vertex in vertices:
                token = IFCComponentToken(
                    topologic_vertex_id=vertex['id'],
                    kuzu_element_id=vertex['id'],
                    ifc_guid=vertex.get('ifc_guid', ''),
                    ifc_type=vertex.get('ifc_type', 'Unknown'),
                    ifc_name=vertex.get('name', 'Unnamed'),
                    file_id=file_id,
                    building_id=vertex.get('building_id', ''),
                    building_name=building_name,
                    contract_address=contract_address,
                    token_standard=TokenStandard.ERC998,
                    chain_id=chain_id,
                    status=TokenizationStatus.PENDING
                )

                # Generate token URI
                token.token_uri = token.generate_token_uri()

                collection.component_tokens.append(token)

            # Update statistics
            collection.update_statistics()

            self.logger.info(
                f"Created tokenization mapping: {len(collection.component_tokens)} tokens "
                f"for building '{building_name}'"
            )

            return collection

        except Exception as e:
            self.logger.error(f"Failed to create tokenization mapping: {e}", exc_info=True)
            raise

    def prepare_batch_mint_data(
        self,
        file_id: str,
        building_name: str
    ) -> Dict[str, Any]:
        """
        Prepare complete batch minting data for smart contract call.

        Exports building graph and formats it as JSON-serializable dict
        ready for Web3.py contract interaction.

        Args:
            file_id: IFC file ID in Kuzu database
            building_name: Name for the building project

        Returns:
            Dict with keys: 'fileId', 'projectName', 'nodes', 'edges'

        Example:
            >>> mint_data = service.prepare_batch_mint_data("file-123", "HQ Building")
            >>> contract.functions.mintBuildingGraph(
            ...     owner_address,
            ...     mint_data['fileId'],
            ...     mint_data['projectName'],
            ...     mint_data['nodes'],
            ...     mint_data['edges']
            ... ).transact()
        """
        try:
            # Export graph data
            nodes, edges = self.export_building_for_minting(file_id)

            if not nodes:
                raise ValueError(f"No nodes found for file_id: {file_id}")

            # Format for contract call
            mint_data = {
                'fileId': self._string_to_bytes32(file_id),
                'projectName': building_name,
                'nodes': nodes,
                'edges': edges,
                'nodeCount': len(nodes),
                'edgeCount': len(edges)
            }

            self.logger.info(
                f"Prepared batch mint data for '{building_name}': "
                f"{len(nodes)} nodes, {len(edges)} edges"
            )

            return mint_data

        except Exception as e:
            self.logger.error(f"Failed to prepare batch mint data: {e}", exc_info=True)
            raise

    def validate_export_data(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate exported graph data before minting.

        Checks for:
        - Non-empty nodes list
        - Valid IFC GUIDs
        - Valid coordinates
        - Edge references point to existing nodes
        - Required fields are present

        Args:
            nodes: List of GraphNodeMetadata dicts
            edges: List of GraphEdge dicts

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check nodes
        if not nodes:
            errors.append("No nodes provided")
            return (False, errors)

        # Validate each node
        kuzu_ids = set()
        for idx, node in enumerate(nodes):
            # Required fields
            required_fields = ['kuzuElementId', 'ifcGuid', 'ifcType', 'name']
            for field in required_fields:
                if not node.get(field):
                    errors.append(f"Node {idx}: Missing required field '{field}'")

            # Track IDs for edge validation
            kuzu_id = node.get('kuzuElementId')
            if kuzu_id:
                kuzu_ids.add(kuzu_id)

            # Validate coordinate types
            for coord in ['x', 'y', 'z']:
                if coord not in node:
                    errors.append(f"Node {idx}: Missing coordinate '{coord}'")
                elif not isinstance(node[coord], int):
                    errors.append(f"Node {idx}: Coordinate '{coord}' must be int256")

        # Validate edges
        for idx, edge in enumerate(edges):
            from_id = edge.get('fromKuzuId')
            to_id = edge.get('toKuzuId')

            if from_id and from_id not in kuzu_ids:
                errors.append(f"Edge {idx}: fromKuzuId '{from_id}' not found in nodes")

            if to_id and to_id not in kuzu_ids:
                errors.append(f"Edge {idx}: toKuzuId '{to_id}' not found in nodes")

            if not edge.get('connectionType'):
                errors.append(f"Edge {idx}: Missing connectionType")

        is_valid = len(errors) == 0

        if is_valid:
            self.logger.info(f"Validation passed: {len(nodes)} nodes, {len(edges)} edges")
        else:
            self.logger.warning(f"Validation failed with {len(errors)} errors")

        return (is_valid, errors)

    def sync_token_ids_to_kuzu(
        self,
        file_id: str,
        kuzu_id_to_token_id: Dict[str, int]
    ) -> int:
        """
        Sync minted token IDs back to Kuzu database.

        Updates IfcElement nodes with their corresponding blockchain token IDs
        after successful minting.

        Args:
            file_id: IFC file ID
            kuzu_id_to_token_id: Mapping of Kuzu element IDs to blockchain token IDs

        Returns:
            Number of elements updated

        Example:
            >>> kuzu_id_to_token_id = {
            ...     'vertex-1': 1000000000001,
            ...     'vertex-2': 2000000000001,
            ...     'vertex-3': 5000000000001
            ... }
            >>> updated = service.sync_token_ids_to_kuzu('file-123', kuzu_id_to_token_id)
        """
        try:
            updated_count = 0

            for kuzu_id, token_id in kuzu_id_to_token_id.items():
                # Update Kuzu node with token ID
                # Note: This requires adding a token_id field to IfcElement schema
                query = """
                MATCH (n:IfcElement {id: $kuzu_id, file_id: $file_id})
                SET n.token_id = $token_id,
                    n.minted_at = $timestamp,
                    n.minting_status = 'minted'
                RETURN n.id
                """

                try:
                    import time
                    result = self.kuzu_service.connection.execute(query, {
                        "kuzu_id": kuzu_id,
                        "file_id": file_id,
                        "token_id": str(token_id),  # Store as string to handle large uint256
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })

                    if result.has_next():
                        updated_count += 1

                except Exception as e:
                    self.logger.warning(f"Failed to update token ID for {kuzu_id}: {e}")
                    continue

            self.logger.info(
                f"Synced {updated_count}/{len(kuzu_id_to_token_id)} token IDs to Kuzu"
            )

            return updated_count

        except Exception as e:
            self.logger.error(f"Failed to sync token IDs: {e}", exc_info=True)
            return 0
