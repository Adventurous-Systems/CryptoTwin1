# 🚀 Blockchain Minting - Quick Start

**Get from zero to minting in 5 minutes!**

---

## The 3-Terminal Workflow

### Terminal 1: Anvil (Blockchain)
```bash
cd ~/CryptoTwin1
./START_ANVIL_HIGH_GAS.sh
```
**Keep running!** Should show `gas_limit 100000000`

### Terminal 2: Deploy Contract
```bash
cd ~/CryptoTwin1contracts
forge clean && forge build
forge script script/Deploy.s.sol --rpc-url http://127.0.0.1:8545 --broadcast

# Copy the address and save:
echo "0xCONTRACT_ADDRESS" > ../contract_address.txt
```

### Terminal 3: Streamlit App  
```bash
cd ~/CryptoTwin1
streamlit run src/app.py
```

---

## In Browser: 5 Steps to Mint

### 1. Upload IFC File
- Tab: **"IFC Processing"**
- Upload: `Ifc2x3_Duplex_Architecture.ifc`
- Wait for ✅ Processing complete

### 2. Connect Blockchain
- **Sidebar** → "Blockchain Connection"
- Select: **"Anvil (Local)"**
- Click: **"Connect"**
- See: ✅ Connected, ~10,000 ETH

### 3. Load Contract
- **Sidebar** → "Smart Contract"  
- Mode: **"Connect Existing"**
- Paste address from `contract_address.txt`
- Click: **"Load Contract"**
- See: ✅ Contract Loaded

### 4. Select Building
- Tab: **"Blockchain Minting"**
- Select your building
- See: ✅ Validation passed
- See: ✅ Gas estimate

### 5. MINT! 🚀
- **Scroll down**
- Click: **"🚀 Mint Building Graph NFT"**
- Wait ~30 seconds
- 🎉 Success + Balloons!

---

## All Fixes Applied ✅

1. **Foundry compilation** - Fixed (excludes OZ test files)
2. **Gas limit** - Fixed (100M vs 30M default)
3. **Balance display** - Fixed (correct dict keys)
4. **Gas estimation** - Fixed (correct return keys)

---

## Quick Diagnostics

```bash
# Anvil running?
curl -s http://127.0.0.1:8545 -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","id":1}' | grep result

# Contract deployed?
cast call $(cat contract_address.txt) "name()(string)"

# Should return: "Building Graph NFT"
```

---

## If Something Fails

### "Compilation errors"
```bash
cd contracts && forge clean && forge build
```

### "Out of gas"
```bash
# Restart Anvil with high gas:
killall anvil
./START_ANVIL_HIGH_GAS.sh
# Then redeploy contract
```

### "No mint button"
Check:
- IFC file uploaded? ✓
- Connected to Anvil? ✓
- Contract loaded? ✓
- Building selected? ✓
- **Scrolled down?** ← Button is at bottom!

---

## Documentation

- `GAS_LIMIT_FIX.md` - Out of gas solution
- `BALANCE_FIX.md` - Balance display fix  
- `FOUNDRY_QUICK_REFERENCE.md` - Foundry commands
- `MINTING_GUIDE.md` - Detailed step-by-step
- `MINTING_TROUBLESHOOTING.md` - Problem solving

---

**That's it! Follow the workflow above and you're minting! 🎉**
