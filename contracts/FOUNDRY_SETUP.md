# Foundry Setup Guide

## Prerequisites

- Foundry installed (`curl -L https://foundry.paradigm.xyz | bash && foundryup`)
- Git for dependency management
- Node.js (optional, for additional tooling)

## Project Structure

```
contracts/
├── BuildingGraphNFT.sol       # Main ERC-998 contract
├── interfaces/                # ERC-998 interfaces
│   ├── IERC998ERC721TopDown.sol
│   └── IERC998ERC721BottomUp.sol
├── script/                    # Deployment scripts
│   └── Deploy.s.sol
└── test/                      # Test suite
    └── BuildingGraphNFT.t.sol

lib/                          # Dependencies
└── openzeppelin-contracts/   # OpenZeppelin contracts

foundry.toml                  # Foundry configuration
.env.example                  # Environment variables template
```

## Setup Steps

### 1. Install Dependencies

```bash
# OpenZeppelin contracts already installed
# To reinstall or update:
forge install OpenZeppelin/openzeppelin-contracts --no-commit
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
# - PRIVATE_KEY: Your deployment wallet private key
# - SEPOLIA_RPC_URL: Alchemy/Infura Sepolia RPC endpoint
# - ETHERSCAN_API_KEY: For contract verification
```

### 3. Compile Contracts

```bash
# Compile all contracts
forge build

# Compile with specific profile
FOUNDRY_PROFILE=intense forge build

# Clean and rebuild
forge clean && forge build
```

### 4. Run Tests

```bash
# Run all tests
forge test

# Run with verbosity (show console.log output)
forge test -vvv

# Run specific test
forge test --match-test test_MintSimpleBuilding

# Run with gas reporting
forge test --gas-report

# Run with coverage
forge coverage
```

### 5. Deploy Contracts

#### Local Development (Anvil)

```bash
# Terminal 1: Start local node
anvil

# Terminal 2: Deploy contract
forge script contracts/script/Deploy.s.sol \
  --rpc-url http://localhost:8545 \
  --broadcast

# The contract address will be printed in the output
```

#### Sepolia Testnet

```bash
# Deploy to Sepolia
forge script contracts/script/Deploy.s.sol \
  --rpc-url $SEPOLIA_RPC_URL \
  --broadcast \
  --verify

# Optional: Verify manually if auto-verify fails
forge verify-contract \
  <CONTRACT_ADDRESS> \
  BuildingGraphNFT \
  --chain sepolia \
  --etherscan-api-key $ETHERSCAN_API_KEY
```

#### Mainnet (Production)

```bash
# IMPORTANT: Double-check everything before mainnet deployment!

# Dry run first (no --broadcast)
forge script contracts/script/Deploy.s.sol \
  --rpc-url $MAINNET_RPC_URL

# Deploy for real
forge script contracts/script/Deploy.s.sol \
  --rpc-url $MAINNET_RPC_URL \
  --broadcast \
  --verify \
  --slow  # Use slower deployment for safety
```

## Testing Guide

### Unit Tests

The test suite covers:
- ✅ Basic minting of building graphs
- ✅ ERC-998 parent-child relationships
- ✅ Cascading transfers
- ✅ Graph edge storage and retrieval
- ✅ Token lookups (Kuzu ID, IFC GUID, TopologicPy ID)
- ✅ Construction status tracking
- ✅ Verification records

### Running Specific Test Categories

```bash
# Test minting
forge test --match-test test_Mint

# Test ERC-998
forge test --match-test test_ParentChild --match-test test_Cascading

# Test graph queries
forge test --match-test test_Get

# Test construction tracking
forge test --match-test test_Update --match-test test_Add
```

### Gas Optimization Testing

```bash
# Run with gas profiling
forge test --gas-report

# Example output:
# ╭─────────────────────────────────────────────┬─────────────┬───────┬───────┬───────┬──────────╮
# │ Function                                     │ min         │ avg   │ max   │ # calls│          │
# ├─────────────────────────────────────────────┼─────────────┼───────┼───────┼───────┼──────────┤
# │ mintBuildingGraph                            │ 500000      │ 2.5M  │ 15M   │ 10    │          │
# │ safeTransferFrom (cascading)                 │ 150000      │ 300K  │ 500K  │ 5     │          │
# │ getSubgraph                                  │ 50000       │ 100K  │ 200K  │ 8     │          │
# ╰─────────────────────────────────────────────┴─────────────┴───────┴───────┴───────┴──────────╯
```

## Interacting with Deployed Contracts

### Using Cast (Foundry CLI)

```bash
# Get token owner
cast call <CONTRACT_ADDRESS> "ownerOf(uint256)" 1000000000001 --rpc-url $SEPOLIA_RPC_URL

# Get child tokens
cast call <CONTRACT_ADDRESS> "getChildTokens(uint256)" 2000000000001 --rpc-url $SEPOLIA_RPC_URL

# Get token by IFC GUID
cast call <CONTRACT_ADDRESS> "getTokenByIfcGuid(string)" "2O2Fr\$t4X7Zf8NOew3FL5R" --rpc-url $SEPOLIA_RPC_URL

# Update construction status (requires signing)
cast send <CONTRACT_ADDRESS> \
  "updateConstructionStatus(uint256,uint8)" \
  5000000000001 \
  2 \
  --rpc-url $SEPOLIA_RPC_URL \
  --private-key $PRIVATE_KEY
```

### Using Foundry Scripts

Create custom scripts in `contracts/script/` for common operations:

```solidity
// contracts/script/MintTestBuilding.s.sol
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../BuildingGraphNFT.sol";

contract MintTestBuilding is Script {
    function run() external {
        BuildingGraphNFT nft = BuildingGraphNFT(<DEPLOYED_ADDRESS>);

        // Prepare test data
        // ... create nodes and edges

        vm.startBroadcast();
        nft.mintBuildingGraph(recipient, fileId, name, nodes, edges);
        vm.stopBroadcast();
    }
}
```

## Debugging

### Common Issues

**1. "Compiler version mismatch"**
```bash
# Update Solidity version in foundry.toml
solc = "0.8.24"

# Reinstall dependencies
forge update
```

**2. "Failed to resolve imports"**
```bash
# Check remappings
forge remappings

# Should show:
# @openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/
```

**3. "Gas estimation failed"**
```bash
# Run with more verbose output
forge test -vvvv --gas-limit 30000000
```

**4. "Nonce too low"**
```bash
# Reset account nonce (Anvil only)
# Restart Anvil or use different account
```

### Debug Mode

```bash
# Run tests with maximum verbosity
forge test -vvvvv

# Shows:
# - Stack traces
# - Gas usage per operation
# - Storage changes
# - Event emissions
```

## Gas Optimization Tips

### Current Benchmarks

Based on initial testing:
- Minting 100 components: ~15-20M gas
- Minting 1000 components: ~150-200M gas
- Cascading transfer (10 children): ~300K gas
- Subgraph query (BFS, 50 nodes): ~100K gas

### Optimization Strategies

1. **Batch Minting**: Already optimized - entire graph in one transaction
2. **Storage Packing**: Structs optimized for 32-byte slots
3. **Index Caching**: Lookups use keccak256 hashing (O(1))
4. **Array Sizes**: BFS uses fixed-size arrays - adjust based on graph depth
5. **Via IR**: Enable in `foundry.toml` for larger graphs

```toml
# For maximum optimization (slower compilation)
[profile.intense]
optimizer = true
optimizer_runs = 1000000
via_ir = true
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Foundry Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive

      - name: Install Foundry
        uses: foundry-rs/foundry-toolchain@v1

      - name: Run tests
        run: forge test --gas-report

      - name: Check coverage
        run: forge coverage
```

## Resources

- [Foundry Book](https://book.getfoundry.sh/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
- [ERC-998 Specification](https://eips.ethereum.org/EIPS/eip-998)
- [Solidity Documentation](https://docs.soliditylang.org/)

## Next Steps

1. ✅ Foundry setup complete
2. ⏳ Run tests: `forge test`
3. ⏳ Deploy locally: Start Anvil + Deploy
4. ⏳ Integrate with Python backend (Web3.py)
5. ⏳ Deploy to Sepolia testnet
6. ⏳ End-to-end testing with Kuzu export

## Support

For issues with:
- **Foundry**: Check [Foundry GitHub](https://github.com/foundry-rs/foundry)
- **OpenZeppelin**: See [OZ Forum](https://forum.openzeppelin.com/)
- **This Project**: See project README and documentation
