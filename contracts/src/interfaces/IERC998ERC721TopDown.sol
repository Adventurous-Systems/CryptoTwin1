// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2025 Adventurous Systems ltd. <https://www.adventurous.systems>
pragma solidity ^0.8.24;

/**
 * @title IERC998ERC721TopDown
 * @dev Interface for ERC-998 Top-Down Composable Non-Fungible Tokens
 *
 * ERC-998 allows NFTs to own other NFTs and ERC-20 tokens, creating composable
 * token structures. This interface defines the top-down composable pattern where
 * a parent token can own child tokens.
 *
 * Based on ERC-998 specification: https://eips.ethereum.org/EIPS/eip-998
 */
interface IERC998ERC721TopDown {
    /**
     * @dev Emitted when a child token is received by a parent token
     * @param from The address that transferred the child token
     * @param tokenId The parent token ID receiving the child
     * @param childContract The contract address of the child token
     * @param childTokenId The token ID of the child token
     */
    event ReceivedChild(
        address indexed from,
        uint256 indexed tokenId,
        address indexed childContract,
        uint256 childTokenId
    );

    /**
     * @dev Emitted when a child token is transferred from a parent token
     * @param tokenId The parent token ID
     * @param to The address receiving the child token
     * @param childContract The contract address of the child token
     * @param childTokenId The token ID of the child token
     */
    event TransferChild(
        uint256 indexed tokenId,
        address indexed to,
        address indexed childContract,
        uint256 childTokenId
    );

    /**
     * @dev Get the root owner of a token (traverses up the ownership tree)
     * @param tokenId The token ID to query
     * @return rootOwner The address of the root owner
     */
    function rootOwnerOf(uint256 tokenId) external view returns (address rootOwner);

    /**
     * @dev Get the root owner and parent token ID of a token
     * @param tokenId The token ID to query
     * @return rootOwner The address of the root owner
     * @return parentTokenId The token ID of the parent (0 if no parent)
     * @return isParent Whether the root owner is a parent token
     */
    function rootOwnerOfChild(uint256 tokenId)
        external
        view
        returns (
            address rootOwner,
            uint256 parentTokenId,
            bool isParent
        );

    /**
     * @dev Get all child tokens owned by a parent token
     * @param parentTokenId The parent token ID
     * @param childContract The contract address of child tokens
     * @return childTokenIds Array of child token IDs
     */
    function childTokensOf(uint256 parentTokenId, address childContract)
        external
        view
        returns (uint256[] memory childTokenIds);

    /**
     * @dev Transfer child token from parent to address
     * @param fromTokenId The parent token ID
     * @param to The address to receive the child token
     * @param childContract The contract address of the child token
     * @param childTokenId The token ID of the child token
     */
    function transferChild(
        uint256 fromTokenId,
        address to,
        address childContract,
        uint256 childTokenId
    ) external;

    /**
     * @dev Transfer child token from parent to another parent token
     * @param fromTokenId The current parent token ID
     * @param toContract The contract address of the new parent token
     * @param toTokenId The new parent token ID
     * @param childContract The contract address of the child token
     * @param childTokenId The token ID of the child token
     * @param data Additional data for the transfer
     */
    function safeTransferChild(
        uint256 fromTokenId,
        address toContract,
        uint256 toTokenId,
        address childContract,
        uint256 childTokenId,
        bytes calldata data
    ) external;

    /**
     * @dev Get the owner of a child token
     * @param childContract The contract address of the child token
     * @param childTokenId The token ID of the child token
     * @return parentTokenOwner The address of the parent token's owner
     * @return parentTokenId The token ID of the parent
     */
    function ownerOfChild(address childContract, uint256 childTokenId)
        external
        view
        returns (address parentTokenOwner, uint256 parentTokenId);

    /**
     * @dev Callback for receiving child tokens via safeTransferFrom
     * @param operator The address which called safeTransferFrom
     * @param from The address which previously owned the token
     * @param childTokenId The token ID being transferred
     * @param data Additional data with no specified format
     * @return The function selector to confirm receipt
     */
    function onERC721Received(
        address operator,
        address from,
        uint256 childTokenId,
        bytes calldata data
    ) external returns (bytes4);
}
