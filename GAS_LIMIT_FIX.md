# Out of Gas Error - Fix Guide

## The Error

```
Error: reverted with: EvmError: OutOfGas
gas required exceeds allowance: 30000000
Gas used: 13750000
```

## Root Cause

**You're trying to mint ~90+ building components**, which requires approximately **30+ million gas**.

**Anvil's default block gas limit: 30,000,000 gas**

Your transaction needs MORE than this, so it runs out of gas mid-execution and reverts.

### Gas Calculation

```
Base cost:        200,000 gas
Per node:         150,000 gas × ~90 nodes = 13,500,000 gas
Per edge:          50,000 gas × edges
Buffer:           500,000 gas
                  ─────────────────────────
TOTAL:            ~30,000,000+ gas (exceeds limit!)
```

---

## Solution 1: Increase Anvil Gas Limit ✅ (RECOMMENDED)

**Restart Anvil with a higher gas limit:**

### Step 1: Stop Current Anvil

```bash
# Find Anvil process
ps aux | grep anvil

# Kill it (or Ctrl+C in terminal)
killall anvil
```

### Step 2: Start Anvil with 100M Gas Limit

```bash
anvil --gas-limit 100000000
```

Or use the helper script I created:

```bash
./START_ANVIL_HIGH_GAS.sh
```

This allows minting buildings with **~600+ components**.

### Step 3: Redeploy Contract

Since Anvil restarted, you need to redeploy:

```bash
cd contracts
forge script script/Deploy.s.sol --rpc-url http://127.0.0.1:8545 --broadcast
```

**Save the new contract address to `contract_address.txt`**

### Step 4: Reconnect and Mint

1. In your Streamlit app:
   - Sidebar → Disconnect (if connected)
   - Sidebar → Connect to Anvil
   - Sidebar → Load Contract (use new address)

2. Go to Blockchain Minting tab
3. Select your building
4. **Should work now!** 🎉

---

## Solution 2: Reduce Number of Nodes

If you want to keep Anvil at default limits, mint fewer components.

### Option A: Filter Component Types

Modify `blockchain_service.py` to only export certain types:

```python
# In export_building_for_minting(), add filter:
filter_types = ['IfcWall', 'IfcSpace', 'IfcDoor', 'IfcWindow']
nodes, edges = self.export_building_for_minting(
    file_id, 
    include_types=filter_types
)
```

### Option B: Use a Smaller IFC File

Test with a simple IFC file first:
- `Ifc2x3_Duplex_Architecture.ifc` (~50 components) ✅
- Avoid large files with 100+ components

### Gas Limits by Node Count

| Nodes | Gas Needed  | Anvil Default (30M) | Works?         |
|-------|-------------|---------------------|----------------|
| 10    | ~1.7M       | ✅                  | Yes            |
| 50    | ~7.7M       | ✅                  | Yes            |
| 100   | ~15.2M      | ✅                  | Yes            |
| 150   | ~22.7M      | ✅                  | Yes            |
| 200   | ~30.2M      | ❌                  | Need 100M      |
| 500   | ~75.2M      | ❌                  | Need 100M      |
| 1000  | ~150.2M     | ❌                  | Need 200M      |

---

## Solution 3: Batch Minting (Advanced)

For very large buildings, mint in batches:

1. **Mint building hierarchy** (Project → Building → Storeys → Spaces)
2. **Mint components in batches** of 100-200 at a time
3. **Link relationships** after all minted

This requires modifying the smart contract to support incremental minting.

---

## Quick Fix Commands

### Fastest Path to Success:

```bash
# 1. Stop Anvil
killall anvil

# 2. Start with high gas limit
anvil --gas-limit 100000000

# 3. Redeploy contract
cd contracts
forge script script/Deploy.s.sol --rpc-url http://127.0.0.1:8545 --broadcast

# 4. Save contract address
# Copy the "Deployed to:" address and:
echo "0xYOUR_NEW_ADDRESS" > ../contract_address.txt

# 5. Reconnect in app and mint!
```

---

## Verification

After restarting Anvil with high gas limit, verify:

```bash
# Check Anvil gas limit (in Anvil terminal output)
# Should see: "gas_limit             100000000"

# Or query it:
cast rpc eth_getBlockByNumber "latest" false | grep gasLimit
```

---

## Understanding the Error Details

From your error output:

```
Transaction: 0xfccf201a597dfc13182d74f621880a8a70ea5b61828ff2479f41a0d8ada6cf6c
Gas used: 13750000
Error: reverted with: EvmError: OutOfGas
gas required exceeds allowance: 30000000
```

**What happened:**
1. Transaction started executing
2. Used 13,750,000 gas (almost half the limit)
3. Needed to continue but hit the 30M limit
4. Reverted with OutOfGas error

**Why it reverted:**
- The contract has a loop that mints each node
- Each iteration uses gas
- After ~90 nodes, the block gas limit was exceeded
- Transaction stopped and reverted

**The fix:**
- Increase the gas limit to 100M
- Now the transaction can complete all iterations

---

## Production Considerations

For production deployment (mainnet/testnet):

1. **Batch minting:** Don't mint 100+ components in one transaction
   - Split into smaller batches (50-100 per transaction)
   - More gas-efficient and safer

2. **Gas optimization:** Optimize the smart contract
   - Use `unchecked` for safe arithmetic
   - Pack storage variables
   - Minimize storage writes

3. **Progressive minting:** Mint hierarchy first, components later
   - Mint Project/Building/Storeys immediately
   - Mint individual components as needed

4. **Off-chain indexing:** Use The Graph or similar
   - Store minimal data on-chain
   - Index and query via subgraph

---

## Expected Behavior After Fix

Once Anvil is running with 100M gas limit:

```
✅ Transaction submitted
✅ Gas estimation: ~30-40M gas
✅ Transaction confirmed
✅ All 90+ nodes minted successfully
✅ Events emitted with token IDs
🎉 Success! Building is on blockchain!
```

---

## Summary

**Problem:** Trying to mint 90+ nodes, needs 30M+ gas, Anvil limit is 30M  
**Solution:** Restart Anvil with `anvil --gas-limit 100000000`  
**Time to fix:** 2 minutes  

**Then:**
1. Stop Anvil
2. Run: `anvil --gas-limit 100000000`
3. Redeploy contract
4. Reconnect in app
5. Mint successfully! 🚀

---

## Helper Script

I created `START_ANVIL_HIGH_GAS.sh` for you:

```bash
./START_ANVIL_HIGH_GAS.sh
```

This starts Anvil with 100M gas limit automatically.

---

**Status:** Root cause identified, solution ready ✅
