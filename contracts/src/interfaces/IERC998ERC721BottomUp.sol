// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2025 Adventurous Systems ltd. <https://www.adventurous.systems>
pragma solidity ^0.8.24;

/**
 * @title IERC998ERC721BottomUp
 * @dev Interface for ERC-998 Bottom-Up Composable Non-Fungible Tokens
 *
 * This interface defines the bottom-up composable pattern where child tokens
 * know their parent and can be attached to/detached from parent tokens.
 *
 * Based on ERC-998 specification: https://eips.ethereum.org/EIPS/eip-998
 */
interface IERC998ERC721BottomUp {
    /**
     * @dev Emitted when a token is attached to a parent token
     * @param toContract The contract address of the parent token
     * @param toTokenId The token ID of the parent
     * @param tokenId The token ID being attached
     */
    event TransferToParent(
        address indexed toContract,
        uint256 indexed toTokenId,
        uint256 tokenId
    );

    /**
     * @dev Emitted when a token is detached from a parent token
     * @param fromContract The contract address of the parent token
     * @param fromTokenId The token ID of the parent
     * @param tokenId The token ID being detached
     */
    event TransferFromParent(
        address indexed fromContract,
        uint256 indexed fromTokenId,
        uint256 tokenId
    );

    /**
     * @dev Get the root owner of a token by traversing parent relationships
     * @param tokenId The token ID to query
     * @return rootOwner The address of the ultimate owner
     */
    function rootOwnerOf(uint256 tokenId) external view returns (address rootOwner);

    /**
     * @dev Get parent token information
     * @param tokenId The child token ID
     * @return parentContract The contract address of the parent token (address(0) if no parent)
     * @return parentTokenId The token ID of the parent (0 if no parent)
     */
    function parentOf(uint256 tokenId)
        external
        view
        returns (address parentContract, uint256 parentTokenId);

    /**
     * @dev Transfer token to a parent token
     * @param from The current owner address
     * @param toContract The contract address of the parent token
     * @param toTokenId The token ID of the parent
     * @param tokenId The token ID being transferred
     * @param data Additional data for the transfer
     */
    function transferToParent(
        address from,
        address toContract,
        uint256 toTokenId,
        uint256 tokenId,
        bytes calldata data
    ) external;

    /**
     * @dev Transfer token from parent to address
     * @param fromContract The contract address of the parent token
     * @param fromTokenId The token ID of the parent
     * @param to The address to receive the token
     * @param tokenId The token ID being transferred
     * @param data Additional data for the transfer
     */
    function transferFromParent(
        address fromContract,
        uint256 fromTokenId,
        address to,
        uint256 tokenId,
        bytes calldata data
    ) external;

    /**
     * @dev Transfer token from one parent to another parent
     * @param fromContract The contract address of the current parent
     * @param fromTokenId The token ID of the current parent
     * @param toContract The contract address of the new parent
     * @param toTokenId The token ID of the new parent
     * @param tokenId The token ID being transferred
     * @param data Additional data for the transfer
     */
    function transferAsChild(
        address fromContract,
        uint256 fromTokenId,
        address toContract,
        uint256 toTokenId,
        uint256 tokenId,
        bytes calldata data
    ) external;
}
