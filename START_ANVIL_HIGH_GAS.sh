#!/bin/bash
# Start Anvil with increased gas limit for minting large buildings

echo "Starting Anvil with 300M gas limit..."
echo "This allows minting of very large buildings (1000+ components)"
echo "Block gas limit: 300,000,000"
echo "Base fee per gas: 1 wei (minimal)"
echo ""

anvil --gas-limit 300000000 --block-base-fee-per-gas 1

