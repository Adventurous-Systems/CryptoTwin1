"""
Blockchain tokenization models for IFC elements with TopologicPy IDs.

Provides data structures for mapping IFC building components to blockchain tokens,
enabling decentralized ownership, provenance tracking, and smart contract integration.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime
import uuid


class TokenStandard(str, Enum):
    """Supported token standards for IFC component tokenization"""
    ERC721 = "ERC-721"  # Non-fungible tokens (unique components)
    ERC1155 = "ERC-1155"  # Multi-token standard (batches)
    ERC998 = "ERC-998"  # Composable NFTs (building hierarchies)


class TokenizationStatus(str, Enum):
    """Status of tokenization process"""
    PENDING = "pending"
    MINTING = "minting"
    MINTED = "minted"
    TRANSFERRED = "transferred"
    BURNED = "burned"
    FAILED = "failed"


class IFCComponentToken(BaseModel):
    """
    Mapping between IFC element and blockchain token.

    Links TopologicPy vertex/element to an on-chain token with metadata
    and ownership tracking.
    """
    # Internal identifiers
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # TopologicPy/Kuzu identifiers
    topologic_vertex_id: str = Field(description="UUID from TopologicVertex.id")
    kuzu_element_id: str = Field(description="Element ID in Kuzu database")

    # IFC identifiers
    ifc_guid: str = Field(description="IFC GlobalId - permanent identifier")
    ifc_type: str = Field(description="IFC entity type (IfcWall, IfcSpace, etc.)")
    ifc_name: Optional[str] = None

    # Building context
    file_id: str = Field(description="Source IFC file ID")
    building_id: Optional[str] = None
    building_name: Optional[str] = None

    # Blockchain identifiers
    token_id: Optional[int] = Field(None, description="On-chain token ID")
    contract_address: Optional[str] = Field(None, description="Smart contract address")
    token_standard: TokenStandard = TokenStandard.ERC721
    chain_id: int = Field(1, description="Blockchain network ID (1=Ethereum mainnet)")

    # Token metadata - encoded with graph database references
    token_uri: Optional[str] = Field(
        None,
        description="URI encoding Kuzu element ID and TopologicPy vertex ID (e.g., 'kuzu://{kuzu_id}/topologic/{vertex_id}')"
    )
    metadata_hash: Optional[str] = Field(None, description="Hash of complete IFC metadata for verification")

    # Ownership tracking
    owner_address: Optional[str] = Field(None, description="Current owner wallet address")
    minter_address: Optional[str] = Field(None, description="Original minter address")

    # Status and timestamps
    status: TokenizationStatus = TokenizationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    minted_at: Optional[datetime] = None
    last_transfer_at: Optional[datetime] = None

    # Transaction tracking
    mint_tx_hash: Optional[str] = Field(None, description="Minting transaction hash")
    transfer_tx_hashes: List[str] = Field(default_factory=list)

    @field_validator('ifc_guid')
    @classmethod
    def validate_ifc_guid(cls, v: str) -> str:
        """Validate IFC GUID format"""
        if not v or len(v) < 1:
            raise ValueError("IFC GUID cannot be empty")
        return v

    @field_validator('contract_address', 'owner_address', 'minter_address')
    @classmethod
    def validate_ethereum_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate Ethereum address format"""
        if v is None:
            return v
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError(f"Invalid Ethereum address format: {v}")
        return v.lower()

    def generate_token_uri(self, base_url: Optional[str] = None) -> str:
        """
        Generate token URI encoding Kuzu and TopologicPy identifiers.

        Format: kuzu://{kuzu_element_id}/topologic/{topologic_vertex_id}/ifc/{ifc_guid}

        Or with custom base_url: {base_url}/element/{kuzu_element_id}?topologic={topologic_vertex_id}&ifc={ifc_guid}

        Args:
            base_url: Optional base URL (e.g., API endpoint for metadata resolution)

        Returns:
            Token URI string encoding all graph database references
        """
        if base_url:
            # HTTP-based URI for API resolution
            return f"{base_url}/element/{self.kuzu_element_id}?topologic={self.topologic_vertex_id}&ifc={self.ifc_guid}"
        else:
            # Custom protocol URI for direct graph database reference
            return f"kuzu://{self.kuzu_element_id}/topologic/{self.topologic_vertex_id}/ifc/{self.ifc_guid}"

    @staticmethod
    def parse_token_uri(token_uri: str) -> Dict[str, str]:
        """
        Parse token URI to extract Kuzu, TopologicPy, and IFC identifiers.

        Args:
            token_uri: Token URI string

        Returns:
            Dictionary with 'kuzu_id', 'topologic_id', and 'ifc_guid'

        Example:
            >>> IFCComponentToken.parse_token_uri("kuzu://elem123/topologic/vertex456/ifc/guid789")
            {'kuzu_id': 'elem123', 'topologic_id': 'vertex456', 'ifc_guid': 'guid789'}
        """
        import re
        from urllib.parse import urlparse, parse_qs

        # Try custom protocol format first
        if token_uri.startswith("kuzu://"):
            # Format: kuzu://{kuzu_id}/topologic/{topologic_id}/ifc/{ifc_guid}
            pattern = r"kuzu://([^/]+)/topologic/([^/]+)/ifc/(.+)"
            match = re.match(pattern, token_uri)
            if match:
                return {
                    "kuzu_id": match.group(1),
                    "topologic_id": match.group(2),
                    "ifc_guid": match.group(3)
                }

        # Try HTTP-based format
        elif token_uri.startswith("http://") or token_uri.startswith("https://"):
            # Format: {base_url}/element/{kuzu_id}?topologic={topologic_id}&ifc={ifc_guid}
            parsed = urlparse(token_uri)
            path_parts = parsed.path.split('/')
            query_params = parse_qs(parsed.query)

            kuzu_id = path_parts[-1] if len(path_parts) > 0 else None
            topologic_id = query_params.get('topologic', [None])[0]
            ifc_guid = query_params.get('ifc', [None])[0]

            if kuzu_id and topologic_id and ifc_guid:
                return {
                    "kuzu_id": kuzu_id,
                    "topologic_id": topologic_id,
                    "ifc_guid": ifc_guid
                }

        raise ValueError(f"Unable to parse token URI: {token_uri}")

    def to_token_metadata(self) -> Dict[str, Any]:
        """
        Generate ERC-721/ERC-1155 compliant metadata with graph database references.

        Returns JSON metadata with Kuzu and TopologicPy identifiers embedded.
        The token_uri directly encodes the graph database location of this component.
        """
        # Generate graph database URI if not set
        graph_uri = self.token_uri or self.generate_token_uri()

        return {
            "name": self.ifc_name or f"{self.ifc_type} #{self.ifc_guid[:8]}",
            "description": f"Tokenized {self.ifc_type} from {self.building_name or 'Building'}. "
                          f"Graph data accessible via Kuzu element ID: {self.kuzu_element_id}",
            "external_url": graph_uri,  # Points to graph database reference
            "animation_url": graph_uri,  # Also use for dynamic content
            "attributes": [
                {"trait_type": "IFC Type", "value": self.ifc_type},
                {"trait_type": "IFC GUID", "value": self.ifc_guid},
                {"trait_type": "Building", "value": self.building_name or "Unknown"},
                {"trait_type": "TopologicPy Vertex ID", "value": self.topologic_vertex_id},
                {"trait_type": "Kuzu Element ID", "value": self.kuzu_element_id},
                {"trait_type": "File ID", "value": self.file_id},
                {"trait_type": "Token Standard", "value": self.token_standard.value},
            ],
            "properties": {
                # Primary graph database identifiers
                "kuzu_element_id": self.kuzu_element_id,
                "topologic_vertex_id": self.topologic_vertex_id,
                "ifc_guid": self.ifc_guid,

                # Secondary metadata
                "ifc_type": self.ifc_type,
                "building_id": self.building_id,
                "file_id": self.file_id,
                "created_at": self.created_at.isoformat(),

                # Graph URI for direct resolution
                "graph_uri": graph_uri,
                "metadata_hash": self.metadata_hash,
            }
        }


class BuildingTokenCollection(BaseModel):
    """
    Collection of tokens representing an entire building or IFC file.

    Groups related component tokens into a cohesive collection with
    hierarchical relationships (ERC-998 composability).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Building identifiers
    file_id: str
    building_id: Optional[str] = None
    building_name: str
    ifc_filename: str

    # Collection metadata
    collection_name: str = Field(description="NFT collection name")
    collection_symbol: str = Field(description="NFT collection symbol")
    collection_description: Optional[str] = None

    # Blockchain details
    contract_address: Optional[str] = None
    deployer_address: Optional[str] = None
    chain_id: int = 1

    # Token mappings
    component_tokens: List[IFCComponentToken] = Field(default_factory=list)

    # Collection statistics
    total_components: int = 0
    minted_count: int = 0
    pending_count: int = 0

    # Deployment tracking
    deployed_at: Optional[datetime] = None
    deployment_tx_hash: Optional[str] = None

    # Collection metadata URI
    base_uri: Optional[str] = Field(None, description="Base URI for token metadata")
    contract_uri: Optional[str] = Field(None, description="Collection-level metadata URI")

    def update_statistics(self) -> None:
        """Update collection statistics based on component tokens"""
        self.total_components = len(self.component_tokens)
        self.minted_count = sum(1 for t in self.component_tokens if t.status == TokenizationStatus.MINTED)
        self.pending_count = sum(1 for t in self.component_tokens if t.status == TokenizationStatus.PENDING)

    def get_tokens_by_type(self, ifc_type: str) -> List[IFCComponentToken]:
        """Get all tokens of a specific IFC type"""
        return [t for t in self.component_tokens if t.ifc_type == ifc_type]

    def get_tokens_by_status(self, status: TokenizationStatus) -> List[IFCComponentToken]:
        """Get all tokens with specific status"""
        return [t for t in self.component_tokens if t.status == status]

    def to_collection_metadata(self) -> Dict[str, Any]:
        """Generate collection-level metadata"""
        return {
            "name": self.collection_name,
            "description": self.collection_description or f"Tokenized building components from {self.ifc_filename}",
            "image": self.contract_uri or "",
            "external_link": self.contract_uri or "",
            "seller_fee_basis_points": 0,
            "fee_recipient": self.deployer_address or "",
        }


class TokenizationMapping(BaseModel):
    """
    Complete tokenization mapping for IFC elements with TopologicPy IDs.

    Provides the full mapping schema linking:
    - TopologicPy vertex IDs → Kuzu element IDs → IFC GUIDs → Blockchain tokens
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Mapping metadata
    name: str = Field(description="Mapping name/identifier")
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Source data
    file_id: str
    building_collections: List[BuildingTokenCollection] = Field(default_factory=list)

    # Mapping index for quick lookups
    topologic_to_token: Dict[str, str] = Field(
        default_factory=dict,
        description="Map TopologicPy vertex ID → IFCComponentToken ID"
    )
    kuzu_to_token: Dict[str, str] = Field(
        default_factory=dict,
        description="Map Kuzu element ID → IFCComponentToken ID"
    )
    ifc_guid_to_token: Dict[str, str] = Field(
        default_factory=dict,
        description="Map IFC GUID → IFCComponentToken ID"
    )
    token_id_to_component: Dict[int, str] = Field(
        default_factory=dict,
        description="Map blockchain token ID → IFCComponentToken ID"
    )

    # Statistics
    total_mapped_components: int = 0
    total_collections: int = 0
    total_minted: int = 0

    def add_component_token(self, token: IFCComponentToken, collection_id: str) -> None:
        """Add a component token to the mapping and update indexes"""
        # Find the collection
        collection = next((c for c in self.building_collections if c.id == collection_id), None)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        # Add token to collection
        collection.component_tokens.append(token)

        # Update indexes
        self.topologic_to_token[token.topologic_vertex_id] = token.id
        self.kuzu_to_token[token.kuzu_element_id] = token.id
        self.ifc_guid_to_token[token.ifc_guid] = token.id
        if token.token_id is not None:
            self.token_id_to_component[token.token_id] = token.id

        # Update statistics
        self.update_statistics()
        self.updated_at = datetime.utcnow()

    def get_token_by_topologic_id(self, topologic_id: str) -> Optional[IFCComponentToken]:
        """Get token by TopologicPy vertex ID"""
        token_id = self.topologic_to_token.get(topologic_id)
        if not token_id:
            return None

        for collection in self.building_collections:
            for token in collection.component_tokens:
                if token.id == token_id:
                    return token
        return None

    def get_token_by_ifc_guid(self, ifc_guid: str) -> Optional[IFCComponentToken]:
        """Get token by IFC GUID"""
        token_id = self.ifc_guid_to_token.get(ifc_guid)
        if not token_id:
            return None

        for collection in self.building_collections:
            for token in collection.component_tokens:
                if token.id == token_id:
                    return token
        return None

    def update_statistics(self) -> None:
        """Update mapping statistics"""
        self.total_collections = len(self.building_collections)
        self.total_mapped_components = sum(len(c.component_tokens) for c in self.building_collections)
        self.total_minted = sum(
            sum(1 for t in c.component_tokens if t.status == TokenizationStatus.MINTED)
            for c in self.building_collections
        )


class SmartContractConfig(BaseModel):
    """Smart contract deployment configuration"""
    contract_name: str = "IFCComponentNFT"
    contract_symbol: str = "IFCNFT"
    token_standard: TokenStandard = TokenStandard.ERC721

    # Network configuration
    chain_id: int = 1
    rpc_url: str = "http://localhost:8545"  # Default to local hardhat/ganache

    # Contract parameters
    base_uri: str = ""
    max_supply: Optional[int] = None
    royalty_percentage: int = 0  # Basis points (e.g., 250 = 2.5%)
    royalty_receiver: Optional[str] = None

    # Deployment settings
    deployer_private_key: Optional[str] = Field(None, description="Deployer wallet private key")
    gas_limit: int = 5000000
    gas_price_gwei: Optional[int] = None

    # Verification
    verify_on_etherscan: bool = False
    etherscan_api_key: Optional[str] = None
