// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2025 Adventurous Systems ltd. <https://www.adventurous.systems>
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./interfaces/IERC998ERC721TopDown.sol";
import "./interfaces/IERC998ERC721BottomUp.sol";

/**
 * @title BuildingGraphNFT
 * @author IFC TopologicPy Kuzu Ethereum Integration
 * @notice ERC-998 Composable NFT representing building graphs as digital twins
 *
 * @dev This contract implements a graph-isomorphic mapping between Kuzu database
 * building graphs and blockchain tokens. Each node in the TopologicPy/Kuzu graph
 * becomes a token, with hierarchical (ERC-998 parent-child) and lateral (adjacency list)
 * relationships preserved on-chain.
 *
 * Token Type Encoding (in tokenId):
 * - Project:   1_000_000_000_000 + projectId
 * - Building:  2_000_000_000_000 + buildingId
 * - Storey:    3_000_000_000_000 + storeyId
 * - Space:     4_000_000_000_000 + spaceId
 * - Component: 5_000_000_000_000 + componentId
 *
 * Workflow:
 * 1. Design Phase: IFC → TopologicPy → Kuzu (off-chain graph modeling)
 * 2. Pre-Construction: Mint entire building graph in single transaction
 * 3. Construction: Digital twin tracks progress, ownership, verification
 * 4. Post-Construction: NFTs represent real-world building component ownership
 */
contract BuildingGraphNFT is
    ERC721,
    ERC721Enumerable,
    Ownable,
    ReentrancyGuard,
    IERC998ERC721TopDown,
    IERC998ERC721BottomUp
{
    // ============ Enums ============

    /// @notice Types of tokens in the building hierarchy
    enum TokenType {
        PROJECT,    // Top-level project (IFC file)
        BUILDING,   // Building within project
        STOREY,     // Building storey/floor
        SPACE,      // Spatial container (room, zone)
        COMPONENT   // Physical component (wall, door, beam, etc.)
    }

    /// @notice Construction status for tracking
    enum ConstructionStatus {
        DESIGNED,      // In design phase
        APPROVED,      // Design approved
        IN_PROGRESS,   // Under construction
        COMPLETED,     // Construction completed
        VERIFIED       // Quality verified
    }

    // ============ Structs ============

    /**
     * @notice Graph node metadata linking blockchain token to Kuzu/TopologicPy/IFC data
     * @dev Stores all identifiers and metadata for a single building component
     */
    struct GraphNodeMetadata {
        TokenType tokenType;            // Type of token in hierarchy

        // Graph database identifiers
        string kuzuElementId;           // Kuzu database element ID
        string topologicVertexId;       // TopologicPy vertex UUID
        string ifcGuid;                 // IFC GlobalId (permanent identifier)

        // IFC metadata
        string ifcType;                 // IFC entity type (IfcWall, IfcSpace, etc.)
        string name;                    // Human-readable name

        // Spatial data (scaled to int256 for coordinates)
        int256 x;                       // X coordinate
        int256 y;                       // Y coordinate
        int256 z;                       // Z coordinate

        // Building context
        bytes32 fileId;                 // Source IFC file identifier
        bytes32 buildingId;             // Building identifier

        // ERC-998 hierarchy
        uint256 parentTokenId;          // Parent token ID (0 if root)
        uint256[] childTokenIds;        // Array of child token IDs

        // Construction tracking
        ConstructionStatus status;      // Current construction status
        uint256 mintedAt;               // Timestamp of minting
        bool exists;                    // Flag for existence check
    }

    /**
     * @notice Graph edge representing connection between components
     * @dev Stores lateral connections not captured by ERC-998 hierarchy
     */
    struct GraphEdge {
        uint256 fromTokenId;            // Source token ID (resolved during minting)
        uint256 toTokenId;              // Target token ID (resolved during minting)
        uint256 fromIndex;              // Source node index in nodes array
        uint256 toIndex;                // Target node index in nodes array
        string connectionType;          // Type: "topological", "spatial", "structural"
        string edgeProperties;          // JSON-encoded edge metadata
        bytes32 kuzuEdgeId;            // Kuzu edge identifier for reference
        bool bidirectional;             // Whether edge is bidirectional
    }

    /**
     * @notice Construction verification record
     * @dev Links documentation and QA data to components
     */
    struct VerificationRecord {
        address verifier;               // Address of verifier
        uint256 timestamp;              // Verification timestamp
        string documentHash;            // IPFS/Arweave hash of verification docs
        string notes;                   // Verification notes
        bool approved;                  // Approval status
    }

    // ============ Constants ============

    /// @notice Token ID offsets for different token types
    uint256 private constant PROJECT_OFFSET = 1_000_000_000_000;
    uint256 private constant BUILDING_OFFSET = 2_000_000_000_000;
    uint256 private constant STOREY_OFFSET = 3_000_000_000_000;
    uint256 private constant SPACE_OFFSET = 4_000_000_000_000;
    uint256 private constant COMPONENT_OFFSET = 5_000_000_000_000;

    // ============ State Variables ============

    /// @notice Mapping from token ID to graph node metadata
    mapping(uint256 => GraphNodeMetadata) public nodeMetadata;

    /// @notice Mapping from token ID to adjacency list (lateral graph edges)
    mapping(uint256 => GraphEdge[]) public nodeEdges;

    /// @notice Mapping from Kuzu element ID hash to token ID
    mapping(bytes32 => uint256) public kuzuToTokenId;

    /// @notice Mapping from IFC GUID to token ID
    mapping(string => uint256) public ifcGuidToTokenId;

    /// @notice Mapping from TopologicPy vertex ID to token ID
    mapping(string => uint256) public topologicToTokenId;

    /// @notice ERC-998: Mapping from parent token ID to array of child token IDs
    mapping(uint256 => uint256[]) private _childTokens;

    /// @notice ERC-998: Mapping from child token ID to parent token ID
    mapping(uint256 => uint256) private _parentToken;

    /// @notice Construction verification records per token
    mapping(uint256 => VerificationRecord[]) public verificationRecords;

    /// @notice Counters for generating unique token IDs per type
    uint256 private projectCounter;
    uint256 private buildingCounter;
    uint256 private storeyCounter;
    uint256 private spaceCounter;
    uint256 private componentCounter;

    // ============ Events ============

    /**
     * @notice Emitted when a graph node is minted
     * @param tokenId The token ID of the minted node
     * @param tokenType The type of token
     * @param kuzuElementId Kuzu database element ID
     * @param ifcGuid IFC GlobalId
     * @param parentTokenId Parent token ID (0 if root)
     */
    event GraphNodeMinted(
        uint256 indexed tokenId,
        TokenType tokenType,
        string kuzuElementId,
        string ifcGuid,
        uint256 parentTokenId
    );

    /**
     * @notice Emitted when a graph edge is created
     * @param fromTokenId Source token ID
     * @param toTokenId Target token ID
     * @param connectionType Type of connection
     * @param kuzuEdgeId Kuzu edge identifier
     */
    event GraphEdgeCreated(
        uint256 indexed fromTokenId,
        uint256 indexed toTokenId,
        string connectionType,
        bytes32 kuzuEdgeId
    );

    /**
     * @notice Emitted when a complete building graph is minted
     * @param projectTokenId Top-level project token ID
     * @param fileId IFC file identifier
     * @param projectName Name of the project
     * @param totalNodes Total number of nodes in the graph
     * @param totalEdges Total number of edges in the graph
     */
    event BuildingGraphMinted(
        uint256 indexed projectTokenId,
        bytes32 indexed fileId,
        string projectName,
        uint256 totalNodes,
        uint256 totalEdges
    );

    /**
     * @notice Emitted when construction status is updated
     * @param tokenId Token ID
     * @param oldStatus Previous status
     * @param newStatus New status
     * @param updatedBy Address that updated the status
     */
    event ConstructionStatusUpdated(
        uint256 indexed tokenId,
        ConstructionStatus oldStatus,
        ConstructionStatus newStatus,
        address indexed updatedBy
    );

    /**
     * @notice Emitted when a verification record is added
     * @param tokenId Token ID being verified
     * @param verifier Address of verifier
     * @param documentHash IPFS hash of verification documents
     * @param approved Whether verification passed
     */
    event ComponentVerified(
        uint256 indexed tokenId,
        address indexed verifier,
        string documentHash,
        bool approved
    );

    // ============ Constructor ============

    /**
     * @notice Initialize the BuildingGraphNFT contract
     * @dev Sets up ERC-721 with name and symbol
     */
    constructor() ERC721("Building Graph NFT", "BLDG") Ownable(msg.sender) {}

    // ============ Core Minting Functions ============

    /**
     * @notice Mint an entire building graph from Kuzu database export
     * @dev This is the main entry point for tokenizing a complete building design
     *
     * @param to Address to receive all tokens
     * @param fileId IFC file identifier
     * @param projectName Name of the building project
     * @param nodes Array of graph node metadata
     * @param edges Array of graph edges
     * @return projectTokenId The token ID of the top-level project
     *
     * @custom:security nonReentrant to prevent reentrancy attacks
     */
    function mintBuildingGraph(
        address to,
        bytes32 fileId,
        string memory projectName,
        GraphNodeMetadata[] memory nodes,
        GraphEdge[] memory edges
    ) external onlyOwner nonReentrant returns (uint256 projectTokenId) {
        require(to != address(0), "Cannot mint to zero address");
        require(nodes.length > 0, "Must have at least one node");

        // 1. Mint project token (top-level)
        projectTokenId = _mintProjectToken(to, fileId, projectName);

        // 2. Array to track minted token IDs for edge resolution
        uint256[] memory mintedTokenIds = new uint256[](nodes.length);

        // 3. Mint all nodes with parent-child relationships
        for (uint256 i = 0; i < nodes.length; i++) {
            uint256 tokenId = _mintGraphNode(to, nodes[i], projectTokenId);

            // Store the minted token ID for edge resolution
            mintedTokenIds[i] = tokenId;

            // Track parent-child relationship if parent exists
            if (nodes[i].parentTokenId != 0) {
                _addChild(nodes[i].parentTokenId, tokenId);
            } else if (tokenId != projectTokenId) {
                // If no parent specified and not project token, attach to project
                _addChild(projectTokenId, tokenId);
            }
        }

        // 4. Resolve edge indices to token IDs and create edges
        for (uint256 i = 0; i < edges.length; i++) {
            // Validate indices are within bounds
            if (edges[i].fromIndex < mintedTokenIds.length &&
                edges[i].toIndex < mintedTokenIds.length) {

                // Resolve indices to actual token IDs
                edges[i].fromTokenId = mintedTokenIds[edges[i].fromIndex];
                edges[i].toTokenId = mintedTokenIds[edges[i].toIndex];

                // Create the edge with resolved token IDs
                _createGraphEdge(edges[i]);
            }
            // Silently skip invalid edges (out of bounds indices)
        }

        emit BuildingGraphMinted(
            projectTokenId,
            fileId,
            projectName,
            nodes.length,
            edges.length
        );

        return projectTokenId;
    }

    /**
     * @notice Mint a single graph node (internal)
     * @dev Creates a token and stores all metadata with proper indexing
     *
     * @param to Address to receive the token
     * @param metadata Graph node metadata
     * @param projectTokenId Top-level project token ID
     * @return tokenId The newly minted token ID
     */
    function _mintGraphNode(
        address to,
        GraphNodeMetadata memory metadata,
        uint256 projectTokenId
    ) internal returns (uint256 tokenId) {
        // Generate unique token ID based on type
        tokenId = _generateTokenId(metadata.tokenType);

        // Mint the token
        _safeMint(to, tokenId);

        // Store metadata
        nodeMetadata[tokenId] = metadata;
        nodeMetadata[tokenId].exists = true;
        nodeMetadata[tokenId].mintedAt = block.timestamp;
        nodeMetadata[tokenId].status = ConstructionStatus.DESIGNED;

        // Create indexes for fast lookups
        if (bytes(metadata.kuzuElementId).length > 0) {
            kuzuToTokenId[keccak256(bytes(metadata.kuzuElementId))] = tokenId;
        }
        if (bytes(metadata.ifcGuid).length > 0) {
            ifcGuidToTokenId[metadata.ifcGuid] = tokenId;
        }
        if (bytes(metadata.topologicVertexId).length > 0) {
            topologicToTokenId[metadata.topologicVertexId] = tokenId;
        }

        emit GraphNodeMinted(
            tokenId,
            metadata.tokenType,
            metadata.kuzuElementId,
            metadata.ifcGuid,
            metadata.parentTokenId
        );

        return tokenId;
    }

    /**
     * @notice Mint project token (top-level)
     * @dev Creates the root token representing the entire IFC file/project
     *
     * @param to Address to receive the token
     * @param fileId IFC file identifier
     * @param projectName Name of the project
     * @return tokenId The project token ID
     */
    function _mintProjectToken(
        address to,
        bytes32 fileId,
        string memory projectName
    ) internal returns (uint256) {
        uint256 tokenId = _generateTokenId(TokenType.PROJECT);

        _safeMint(to, tokenId);

        nodeMetadata[tokenId] = GraphNodeMetadata({
            tokenType: TokenType.PROJECT,
            kuzuElementId: "",
            topologicVertexId: "",
            ifcGuid: "",
            ifcType: "IfcProject",
            name: projectName,
            x: 0,
            y: 0,
            z: 0,
            fileId: fileId,
            buildingId: bytes32(0),
            parentTokenId: 0,
            childTokenIds: new uint256[](0),
            status: ConstructionStatus.DESIGNED,
            mintedAt: block.timestamp,
            exists: true
        });

        return tokenId;
    }

    /**
     * @notice Create graph edge (lateral connection)
     * @dev Stores adjacency list edges that complement the hierarchical ERC-998 structure
     *
     * @param edge Graph edge struct with connection details
     */
    function _createGraphEdge(GraphEdge memory edge) internal {
        require(nodeMetadata[edge.fromTokenId].exists, "From node does not exist");
        require(nodeMetadata[edge.toTokenId].exists, "To node does not exist");

        // Add edge to adjacency list
        nodeEdges[edge.fromTokenId].push(edge);

        // If bidirectional, add reverse edge
        if (edge.bidirectional) {
            GraphEdge memory reverseEdge = GraphEdge({
                fromTokenId: edge.toTokenId,
                toTokenId: edge.fromTokenId,
                fromIndex: edge.toIndex,  // Swap indices for reverse edge
                toIndex: edge.fromIndex,
                connectionType: edge.connectionType,
                edgeProperties: edge.edgeProperties,
                kuzuEdgeId: edge.kuzuEdgeId,
                bidirectional: true
            });
            nodeEdges[edge.toTokenId].push(reverseEdge);
        }

        emit GraphEdgeCreated(
            edge.fromTokenId,
            edge.toTokenId,
            edge.connectionType,
            edge.kuzuEdgeId
        );
    }

    // ============ ERC-998 Parent-Child Relationship Functions ============

    /**
     * @notice Add child to parent (internal ERC-998 tracking)
     * @dev Updates parent-child mappings in both directions
     *
     * @param parentTokenId Parent token ID
     * @param childTokenId Child token ID
     */
    function _addChild(uint256 parentTokenId, uint256 childTokenId) internal {
        require(nodeMetadata[parentTokenId].exists, "Parent does not exist");
        require(nodeMetadata[childTokenId].exists, "Child does not exist");
        require(_parentToken[childTokenId] == 0, "Child already has parent");

        _childTokens[parentTokenId].push(childTokenId);
        _parentToken[childTokenId] = parentTokenId;
        nodeMetadata[childTokenId].parentTokenId = parentTokenId;
    }

    /**
     * @notice Remove child from parent (internal)
     * @dev Removes child from parent's array and clears parent reference
     *
     * @param parentTokenId Parent token ID
     * @param childTokenId Child token ID
     */
    function _removeChild(uint256 parentTokenId, uint256 childTokenId) internal {
        uint256[] storage children = _childTokens[parentTokenId];
        for (uint256 i = 0; i < children.length; i++) {
            if (children[i] == childTokenId) {
                children[i] = children[children.length - 1];
                children.pop();
                break;
            }
        }
        _parentToken[childTokenId] = 0;
        nodeMetadata[childTokenId].parentTokenId = 0;
    }

    // ============ ERC-998 Top-Down Interface Implementation ============

    /**
     * @notice Get the root owner of a token
     * @dev Traverses up the ownership tree to find the ultimate owner
     *
     * @param tokenId Token ID to query
     * @return rootOwner Address of the root owner
     */
    function rootOwnerOf(uint256 tokenId) public view override(IERC998ERC721TopDown, IERC998ERC721BottomUp) returns (address rootOwner) {
        uint256 currentToken = tokenId;
        address currentOwner = ownerOf(currentToken);

        // Traverse up parent chain
        while (_parentToken[currentToken] != 0) {
            currentToken = _parentToken[currentToken];
            currentOwner = ownerOf(currentToken);
        }

        return currentOwner;
    }

    /**
     * @notice Get root owner and parent information
     * @dev Returns detailed ownership information including parent token
     *
     * @param tokenId Token ID to query
     * @return rootOwner Address of root owner
     * @return parentTokenId Parent token ID (0 if none)
     * @return isParent Whether token has a parent
     */
    function rootOwnerOfChild(uint256 tokenId)
        external
        view
        override
        returns (
            address rootOwner,
            uint256 parentTokenId,
            bool isParent
        )
    {
        rootOwner = rootOwnerOf(tokenId);
        parentTokenId = _parentToken[tokenId];
        isParent = parentTokenId != 0;
    }

    /**
     * @notice Get all child tokens of a parent
     * @dev For ERC-998, we only track same-contract children
     *
     * @param parentTokenId Parent token ID
     * @param childContract Child contract address (must be this contract)
     * @return Array of child token IDs
     */
    function childTokensOf(uint256 parentTokenId, address childContract)
        external
        view
        override
        returns (uint256[] memory)
    {
        require(childContract == address(this), "Only same-contract children supported");
        return _childTokens[parentTokenId];
    }

    /**
     * @notice Get all child tokens (convenience function)
     * @dev Returns all children without requiring contract address
     *
     * @param parentTokenId Parent token ID
     * @return Array of child token IDs
     */
    function getChildTokens(uint256 parentTokenId) external view returns (uint256[] memory) {
        return _childTokens[parentTokenId];
    }

    /**
     * @notice Get parent token
     * @dev Returns the parent token ID
     *
     * @param childTokenId Child token ID
     * @return Parent token ID (0 if no parent)
     */
    function getParentToken(uint256 childTokenId) external view returns (uint256) {
        return _parentToken[childTokenId];
    }

    /**
     * @notice Transfer child from parent to address
     * @dev Implements ERC-998 child transfer
     *
     * @param fromTokenId Parent token ID
     * @param to Address to receive child
     * @param childContract Child contract (must be this contract)
     * @param childTokenId Child token ID
     */
    function transferChild(
        uint256 fromTokenId,
        address to,
        address childContract,
        uint256 childTokenId
    ) external override {
        require(childContract == address(this), "Only same-contract children");
        require(ownerOf(fromTokenId) == msg.sender, "Not parent owner");
        require(_parentToken[childTokenId] == fromTokenId, "Not a child of this token");

        _removeChild(fromTokenId, childTokenId);
        _transfer(ownerOf(childTokenId), to, childTokenId);

        emit TransferChild(fromTokenId, to, childContract, childTokenId);
    }

    /**
     * @notice Safe transfer child to another parent
     * @dev Implements ERC-998 safe child-to-parent transfer
     */
    function safeTransferChild(
        uint256 fromTokenId,
        address toContract,
        uint256 toTokenId,
        address childContract,
        uint256 childTokenId,
        bytes calldata data
    ) external override {
        require(childContract == address(this), "Only same-contract children");
        require(toContract == address(this), "Only same-contract parents");
        require(ownerOf(fromTokenId) == msg.sender, "Not parent owner");
        require(_parentToken[childTokenId] == fromTokenId, "Not a child");

        _removeChild(fromTokenId, childTokenId);
        _addChild(toTokenId, childTokenId);

        emit TransferChild(fromTokenId, address(this), childContract, childTokenId);
        emit ReceivedChild(msg.sender, toTokenId, childContract, childTokenId);
    }

    /**
     * @notice Get owner of child token
     * @dev Returns parent owner and parent token ID
     */
    function ownerOfChild(address childContract, uint256 childTokenId)
        external
        view
        override
        returns (address parentTokenOwner, uint256 parentTokenId)
    {
        require(childContract == address(this), "Only same-contract children");
        parentTokenId = _parentToken[childTokenId];
        if (parentTokenId != 0) {
            parentTokenOwner = ownerOf(parentTokenId);
        } else {
            parentTokenOwner = ownerOf(childTokenId);
        }
    }

    /**
     * @notice ERC-721 receiver callback
     * @dev Required for safe transfers
     */
    function onERC721Received(
        address operator,
        address from,
        uint256 childTokenId,
        bytes calldata data
    ) external override returns (bytes4) {
        // Decode parent token ID from data if provided
        if (data.length >= 32) {
            uint256 parentTokenId = abi.decode(data, (uint256));
            if (nodeMetadata[parentTokenId].exists) {
                _addChild(parentTokenId, childTokenId);
                emit ReceivedChild(from, parentTokenId, msg.sender, childTokenId);
            }
        }
        return this.onERC721Received.selector;
    }

    // ============ ERC-998 Bottom-Up Interface Implementation ============

    /**
     * @notice Get parent of a token
     * @dev Returns parent contract and token ID
     */
    function parentOf(uint256 tokenId)
        external
        view
        override
        returns (address parentContract, uint256 parentTokenId)
    {
        parentTokenId = _parentToken[tokenId];
        if (parentTokenId != 0) {
            parentContract = address(this);
        }
    }

    /**
     * @notice Transfer token to parent
     * @dev Implements bottom-up composability
     */
    function transferToParent(
        address from,
        address toContract,
        uint256 toTokenId,
        uint256 tokenId,
        bytes calldata data
    ) external override {
        require(toContract == address(this), "Only same-contract parents");
        require(ownerOf(tokenId) == from, "Not token owner");
        require(msg.sender == from || isApprovedForAll(from, msg.sender), "Not authorized");

        _addChild(toTokenId, tokenId);
        emit TransferToParent(toContract, toTokenId, tokenId);
    }

    /**
     * @notice Transfer token from parent to address
     * @dev Implements bottom-up detachment
     */
    function transferFromParent(
        address fromContract,
        uint256 fromTokenId,
        address to,
        uint256 tokenId,
        bytes calldata data
    ) external override {
        require(fromContract == address(this), "Only same-contract");
        require(_parentToken[tokenId] == fromTokenId, "Not child of parent");
        require(ownerOf(fromTokenId) == msg.sender, "Not authorized");

        _removeChild(fromTokenId, tokenId);
        _transfer(ownerOf(tokenId), to, tokenId);
        emit TransferFromParent(fromContract, fromTokenId, tokenId);
    }

    /**
     * @notice Transfer token from one parent to another
     * @dev Implements bottom-up re-parenting
     */
    function transferAsChild(
        address fromContract,
        uint256 fromTokenId,
        address toContract,
        uint256 toTokenId,
        uint256 tokenId,
        bytes calldata data
    ) external override {
        require(fromContract == address(this) && toContract == address(this), "Same-contract only");
        require(_parentToken[tokenId] == fromTokenId, "Not child of parent");
        require(ownerOf(fromTokenId) == msg.sender, "Not authorized");

        _removeChild(fromTokenId, tokenId);
        _addChild(toTokenId, tokenId);

        emit TransferFromParent(fromContract, fromTokenId, tokenId);
        emit TransferToParent(toContract, toTokenId, tokenId);
    }

    // ============ Cascading Transfer Logic ============

    /**
     * @notice Override safeTransferFrom to implement cascading transfers
     * @dev When transferring a parent, all children are transferred too
     *
     * @param from Current owner
     * @param to New owner
     * @param tokenId Token ID being transferred
     * @param data Additional data
     */
    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId,
        bytes memory data
    ) public virtual override(ERC721, IERC721) {
        // Transfer parent token
        super.safeTransferFrom(from, to, tokenId, data);

        // Recursively transfer all children
        _transferChildren(from, to, tokenId, data);
    }

    /**
     * @notice Recursively transfer all child tokens
     * @dev Internal function for cascading transfers
     *
     * @param from Current owner
     * @param to New owner
     * @param parentTokenId Parent token ID
     * @param data Transfer data
     */
    function _transferChildren(
        address from,
        address to,
        uint256 parentTokenId,
        bytes memory data
    ) internal {
        uint256[] memory children = _childTokens[parentTokenId];

        for (uint256 i = 0; i < children.length; i++) {
            uint256 childTokenId = children[i];

            if (_ownerOf(childTokenId) != address(0)) {
                // Transfer child
                super.safeTransferFrom(from, to, childTokenId, data);

                // Recursively transfer grandchildren
                _transferChildren(from, to, childTokenId, data);
            }
        }
    }

    // ============ Graph Query Functions ============

    /**
     * @notice Get all edges for a node (adjacency list)
     * @dev Returns lateral graph connections
     *
     * @param tokenId Token ID to query
     * @return Array of graph edges
     */
    function getNodeEdges(uint256 tokenId) external view returns (GraphEdge[] memory) {
        return nodeEdges[tokenId];
    }

    /**
     * @notice Get complete subgraph starting from a root node
     * @dev Performs BFS traversal to collect all descendants and their edges
     *
     * @param rootTokenId Root token ID to start traversal
     * @return tokenIds Array of token IDs in subgraph
     * @return nodes Array of node metadata
     * @return edges Array of edges in subgraph
     */
    function getSubgraph(uint256 rootTokenId)
        external
        view
        returns (
            uint256[] memory tokenIds,
            GraphNodeMetadata[] memory nodes,
            GraphEdge[] memory edges
        )
    {
        require(nodeMetadata[rootTokenId].exists, "Root token does not exist");

        // BFS traversal with fixed-size arrays (adjust size as needed)
        uint256[] memory queue = new uint256[](10000);
        bool[] memory visited = new bool[](COMPONENT_OFFSET + componentCounter + 1);

        uint256 queueStart = 0;
        uint256 queueEnd = 1;
        queue[0] = rootTokenId;
        visited[rootTokenId] = true;

        uint256 visitedCount = 0;
        uint256[] memory visitedTokens = new uint256[](10000);

        // BFS traversal
        while (queueStart < queueEnd) {
            uint256 current = queue[queueStart++];
            visitedTokens[visitedCount++] = current;

            // Add children to queue
            uint256[] memory children = _childTokens[current];
            for (uint256 i = 0; i < children.length; i++) {
                if (!visited[children[i]]) {
                    queue[queueEnd++] = children[i];
                    visited[children[i]] = true;
                }
            }
        }

        // Collect results
        tokenIds = new uint256[](visitedCount);
        nodes = new GraphNodeMetadata[](visitedCount);

        uint256 totalEdges = 0;
        for (uint256 i = 0; i < visitedCount; i++) {
            tokenIds[i] = visitedTokens[i];
            nodes[i] = nodeMetadata[visitedTokens[i]];
            totalEdges += nodeEdges[visitedTokens[i]].length;
        }

        // Collect all edges
        edges = new GraphEdge[](totalEdges);
        uint256 edgeIndex = 0;
        for (uint256 i = 0; i < visitedCount; i++) {
            GraphEdge[] memory nodeEdgeList = nodeEdges[visitedTokens[i]];
            for (uint256 j = 0; j < nodeEdgeList.length; j++) {
                edges[edgeIndex++] = nodeEdgeList[j];
            }
        }

        return (tokenIds, nodes, edges);
    }

    /**
     * @notice Get tokens by IFC type
     * @dev Searches all tokens of a specific IFC type
     *
     * @param ifcType IFC type to search for (e.g., "IfcWall")
     * @return Array of token IDs matching the type
     */
    function getTokensByIfcType(string memory ifcType)
        external
        view
        returns (uint256[] memory)
    {
        uint256 totalSupply = totalSupply();
        uint256[] memory matches = new uint256[](totalSupply);
        uint256 matchCount = 0;

        for (uint256 i = 0; i < totalSupply; i++) {
            uint256 tokenId = tokenByIndex(i);
            if (
                keccak256(bytes(nodeMetadata[tokenId].ifcType)) ==
                keccak256(bytes(ifcType))
            ) {
                matches[matchCount++] = tokenId;
            }
        }

        // Resize array to actual match count
        uint256[] memory result = new uint256[](matchCount);
        for (uint256 i = 0; i < matchCount; i++) {
            result[i] = matches[i];
        }

        return result;
    }

    /**
     * @notice Get token by Kuzu element ID
     * @param kuzuElementId Kuzu database element ID
     * @return Token ID (0 if not found)
     */
    function getTokenByKuzuId(string memory kuzuElementId) external view returns (uint256) {
        return kuzuToTokenId[keccak256(bytes(kuzuElementId))];
    }

    /**
     * @notice Get token by IFC GUID
     * @param ifcGuid IFC GlobalId
     * @return Token ID (0 if not found)
     */
    function getTokenByIfcGuid(string memory ifcGuid) external view returns (uint256) {
        return ifcGuidToTokenId[ifcGuid];
    }

    /**
     * @notice Get token by TopologicPy vertex ID
     * @param topologicVertexId TopologicPy vertex UUID
     * @return Token ID (0 if not found)
     */
    function getTokenByTopologicId(string memory topologicVertexId)
        external
        view
        returns (uint256)
    {
        return topologicToTokenId[topologicVertexId];
    }

    // ============ Construction Tracking Functions ============

    /**
     * @notice Update construction status of a component
     * @dev Only owner or approved can update status
     *
     * @param tokenId Token ID to update
     * @param newStatus New construction status
     */
    function updateConstructionStatus(uint256 tokenId, ConstructionStatus newStatus)
        external
    {
        require(_isAuthorized(ownerOf(tokenId), msg.sender, tokenId), "Not authorized");

        ConstructionStatus oldStatus = nodeMetadata[tokenId].status;
        nodeMetadata[tokenId].status = newStatus;

        emit ConstructionStatusUpdated(tokenId, oldStatus, newStatus, msg.sender);
    }

    /**
     * @notice Add verification record for a component
     * @dev Links QA documentation and approval to component
     *
     * @param tokenId Token ID to verify
     * @param documentHash IPFS/Arweave hash of verification documents
     * @param notes Verification notes
     * @param approved Whether component passed verification
     */
    function addVerificationRecord(
        uint256 tokenId,
        string memory documentHash,
        string memory notes,
        bool approved
    ) external {
        require(_isAuthorized(ownerOf(tokenId), msg.sender, tokenId), "Not authorized");

        VerificationRecord memory record = VerificationRecord({
            verifier: msg.sender,
            timestamp: block.timestamp,
            documentHash: documentHash,
            notes: notes,
            approved: approved
        });

        verificationRecords[tokenId].push(record);

        // If approved, update status to VERIFIED
        if (approved && nodeMetadata[tokenId].status == ConstructionStatus.COMPLETED) {
            nodeMetadata[tokenId].status = ConstructionStatus.VERIFIED;
        }

        emit ComponentVerified(tokenId, msg.sender, documentHash, approved);
    }

    /**
     * @notice Get all verification records for a component
     * @param tokenId Token ID to query
     * @return Array of verification records
     */
    function getVerificationRecords(uint256 tokenId)
        external
        view
        returns (VerificationRecord[] memory)
    {
        return verificationRecords[tokenId];
    }

    // ============ Utility Functions ============

    /**
     * @notice Generate token ID based on type
     * @dev Uses offset ranges to encode token type in ID
     *
     * @param tokenType Type of token
     * @return Unique token ID
     */
    function _generateTokenId(TokenType tokenType) internal returns (uint256) {
        if (tokenType == TokenType.PROJECT) {
            return PROJECT_OFFSET + (++projectCounter);
        } else if (tokenType == TokenType.BUILDING) {
            return BUILDING_OFFSET + (++buildingCounter);
        } else if (tokenType == TokenType.STOREY) {
            return STOREY_OFFSET + (++storeyCounter);
        } else if (tokenType == TokenType.SPACE) {
            return SPACE_OFFSET + (++spaceCounter);
        } else {
            return COMPONENT_OFFSET + (++componentCounter);
        }
    }

    /**
     * @notice Get token type from token ID
     * @dev Decodes token type from ID offset
     *
     * @param tokenId Token ID to decode
     * @return Token type
     */
    function getTokenType(uint256 tokenId) public pure returns (TokenType) {
        if (tokenId >= COMPONENT_OFFSET) return TokenType.COMPONENT;
        if (tokenId >= SPACE_OFFSET) return TokenType.SPACE;
        if (tokenId >= STOREY_OFFSET) return TokenType.STOREY;
        if (tokenId >= BUILDING_OFFSET) return TokenType.BUILDING;
        return TokenType.PROJECT;
    }

    /**
     * @notice Get total minted tokens per type
     * @return projects Total project tokens
     * @return buildings Total building tokens
     * @return storeys Total storey tokens
     * @return spaces Total space tokens
     * @return components Total component tokens
     */
    function getMintedCounts()
        external
        view
        returns (
            uint256 projects,
            uint256 buildings,
            uint256 storeys,
            uint256 spaces,
            uint256 components
        )
    {
        return (projectCounter, buildingCounter, storeyCounter, spaceCounter, componentCounter);
    }

    // ============ Required Overrides ============

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Enumerable) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(address account, uint128 value)
        internal
        override(ERC721, ERC721Enumerable)
    {
        super._increaseBalance(account, value);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721Enumerable)
        returns (bool)
    {
        return
            interfaceId == type(IERC998ERC721TopDown).interfaceId ||
            interfaceId == type(IERC998ERC721BottomUp).interfaceId ||
            super.supportsInterface(interfaceId);
    }
}
