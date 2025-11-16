// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2025 Adventurous Systems ltd. <https://www.adventurous.systems>
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/BuildingGraphNFT.sol";

/**
 * @title Deploy
 * @notice Deployment script for BuildingGraphNFT contract
 *
 * Usage:
 *   Local (Anvil):
 *     forge script contracts/script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast
 *
 *   Sepolia Testnet:
 *     forge script contracts/script/Deploy.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast --verify
 *
 *   Mainnet:
 *     forge script contracts/script/Deploy.s.sol --rpc-url $MAINNET_RPC_URL --broadcast --verify
 */
contract Deploy is Script {
    function run() external returns (BuildingGraphNFT) {
        // Get deployer private key from environment variable
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Start broadcasting transactions
        vm.startBroadcast(deployerPrivateKey);

        // Deploy BuildingGraphNFT contract
        BuildingGraphNFT buildingNFT = new BuildingGraphNFT();

        console.log("BuildingGraphNFT deployed at:", address(buildingNFT));

        // Stop broadcasting
        vm.stopBroadcast();

        return buildingNFT;
    }
}
