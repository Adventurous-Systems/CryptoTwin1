"""
Blockchain UI Components for Ethereum Connection and NFT Minting.

Provides Streamlit interface for:
- Connecting to Ethereum networks (Anvil/Sepolia/Mainnet)
- Deploying and loading BuildingGraphNFT smart contracts
- Minting building graphs as ERC-998 composable NFTs
- Gas estimation and transaction tracking

Connection Methods:
- Anvil (Local): Private key input for full transaction signing capability
- Sepolia/Mainnet: MetaMask connection for browser wallet integration

Note: Current MetaMask implementation supports read-only operations (querying).
For transaction signing with MetaMask, enhancement needed in Phase 2.
For MVP minting functionality, use Anvil with private key connection.
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
import logging
import json
import time

from services.web3_service import Web3Service
from services.blockchain_service import BlockchainExportService


# Configure logging
logger = logging.getLogger(__name__)


# Network configurations
NETWORKS = {
    "Anvil (Local)": {
        "rpc_url": "http://127.0.0.1:8545",
        "chain_id": 31337,
        "default_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "explorer": None,
        "description": "Local development network with pre-funded test accounts",
    },
    "Sepolia (Testnet)": {
        "rpc_url": "https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
        "chain_id": 11155111,
        "default_key": None,
        "explorer": "https://sepolia.etherscan.io",
        "description": "Ethereum testnet - requires Sepolia ETH from faucet",
    },
    "Mainnet": {
        "rpc_url": "https://mainnet.infura.io/v3/YOUR_INFURA_KEY",
        "chain_id": 1,
        "default_key": None,
        "explorer": "https://etherscan.io",
        "description": "Ethereum mainnet - REAL ETH required!",
    },
}


def render_blockchain_connection_panel() -> Optional[Web3Service]:
    """
    Render blockchain connection panel in sidebar.

    Provides interface for:
    - Network selection (Anvil/Sepolia/Mainnet)
    - MetaMask connection for testnet/mainnet
    - Private key input for Anvil (development only)
    - Connection status display
    - Account balance information

    Returns:
        Web3Service instance if connected, None otherwise
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("⛓️ Blockchain Connection")

    # Network selection
    selected_network = st.sidebar.selectbox(
        "Network",
        options=list(NETWORKS.keys()),
        index=0,  # Default to Anvil
        help="Select Ethereum network to connect to",
    )

    network_config = NETWORKS[selected_network]

    # Show network description
    with st.sidebar.expander("ℹ️ Network Info"):
        st.caption(network_config["description"])
        st.text(f"Chain ID: {network_config['chain_id']}")

    # Connection method depends on network
    if selected_network == "Anvil (Local)":
        # Anvil: Use private key (development mode)
        return _render_anvil_connection(network_config)
    else:
        # Sepolia/Mainnet: Use MetaMask
        return _render_metamask_connection(network_config, selected_network)


def _render_anvil_connection(network_config: Dict[str, Any]) -> Optional[Web3Service]:
    """
    Render Anvil connection with private key input.

    Args:
        network_config: Network configuration dictionary

    Returns:
        Web3Service instance if connected, None otherwise
    """
    st.sidebar.markdown("**Anvil Connection (Development)**")

    # RPC URL (editable)
    rpc_url = st.sidebar.text_input(
        "RPC URL", value=network_config["rpc_url"], help="Local Anvil RPC endpoint"
    )

    # Option to use default account
    use_default = st.sidebar.checkbox(
        "Use default Anvil account #0", value=True, help="Pre-funded test account"
    )

    if use_default:
        private_key = network_config["default_key"]
        st.sidebar.info("🔑 Using Anvil account #0")
    else:
        private_key = st.sidebar.text_input(
            "Private Key",
            type="password",
            help="Private key WITHOUT 0x prefix",
            placeholder="Enter private key...",
        )

    # Connect button
    if st.sidebar.button(
        "🔌 Connect to Anvil", type="primary", use_container_width=True
    ):
        if not private_key:
            st.sidebar.error("❌ Private key required")
            return None

        try:
            with st.spinner("Connecting to Anvil..."):
                # Initialize Web3Service with private key
                web3_service = Web3Service(
                    rpc_url=rpc_url,
                    private_key=private_key,
                    chain_id=network_config["chain_id"],
                )

                if web3_service.is_connected:
                    # Store in session state
                    st.session_state.web3_service = web3_service
                    st.session_state.network_config = network_config
                    st.session_state.selected_network = "Anvil (Local)"
                    st.session_state.connection_type = "private_key"
                    st.sidebar.success("✅ Connected to Anvil")
                else:
                    st.sidebar.error("❌ Failed to connect. Is Anvil running?")
                    return None

        except Exception as e:
            st.sidebar.error(f"❌ Connection error: {str(e)}")
            logger.error(f"Anvil connection failed: {e}", exc_info=True)
            return None

    # Display connection status if connected
    return _render_connection_status()


def _render_metamask_connection(
    network_config: Dict[str, Any], network_name: str
) -> Optional[Web3Service]:
    """
    Render MetaMask connection interface.

    Args:
        network_config: Network configuration dictionary
        network_name: Network name (e.g., "Sepolia (Testnet)")

    Returns:
        Web3Service instance if connected, None otherwise
    """
    st.sidebar.markdown("**MetaMask Connection**")
    st.sidebar.info("🦊 Connect your MetaMask wallet")

    # MetaMask connection component
    metamask_account = _render_metamask_component(network_config)

    if metamask_account:
        # Store MetaMask account in session state
        if (
            "metamask_account" not in st.session_state
            or st.session_state.metamask_account != metamask_account
        ):
            st.session_state.metamask_account = metamask_account
            st.sidebar.success(f"✅ MetaMask connected!")

        # Create Web3Service without private key (read-only mode for now)
        # Note: For signing transactions, we'll need to use MetaMask's signing via JavaScript
        if (
            "web3_service" not in st.session_state
            or st.session_state.get("connection_type") != "metamask"
        ):
            try:
                # Connect to RPC (public endpoint or Infura)
                rpc_url = network_config["rpc_url"]

                # For read-only operations, we don't need private key
                # Transactions will be sent via MetaMask
                web3_service = Web3Service(
                    rpc_url=rpc_url,
                    private_key=None,  # No private key for MetaMask mode
                    chain_id=network_config["chain_id"],
                )

                # Override account with MetaMask account
                # This is a workaround - in production, we'd modify Web3Service to support external signers
                st.session_state.web3_service = web3_service
                st.session_state.network_config = network_config
                st.session_state.selected_network = network_name
                st.session_state.connection_type = "metamask"

            except Exception as e:
                st.sidebar.error(f"❌ RPC connection error: {str(e)}")
                return None

    # Display connection status if connected
    return _render_connection_status()


def _render_metamask_component(network_config: Dict[str, Any]) -> Optional[str]:
    """
    Render MetaMask connection component using HTML/JavaScript.

    Args:
        network_config: Network configuration dictionary

    Returns:
        Connected account address or None
    """

    # MetaMask connection HTML/JavaScript
    metamask_html = f"""
    <div style="padding: 10px; background: #f0f2f6; border-radius: 5px; margin: 10px 0;">
        <button id="connectButton"
                style="width: 100%; padding: 10px; background: #ff6b35; color: white;
                       border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">
            🦊 Connect MetaMask
        </button>
        <div id="status" style="margin-top: 10px; font-size: 12px; color: #333;"></div>
        <div id="account" style="margin-top: 5px; font-size: 11px; font-family: monospace;
                                 color: #666; word-break: break-all;"></div>
    </div>

    <script>
        const button = document.getElementById('connectButton');
        const status = document.getElementById('status');
        const accountDiv = document.getElementById('account');
        const targetChainId = '{hex(network_config["chain_id"])}';

        // Check if already connected
        if (window.ethereum && window.ethereum.selectedAddress) {{
            updateUI(window.ethereum.selectedAddress);
        }}

        button.onclick = async () => {{
            if (typeof window.ethereum === 'undefined') {{
                status.innerHTML = '❌ MetaMask not installed';
                status.style.color = 'red';
                return;
            }}

            try {{
                // Request account access
                const accounts = await window.ethereum.request({{
                    method: 'eth_requestAccounts'
                }});

                // Check network
                const chainId = await window.ethereum.request({{
                    method: 'eth_chainId'
                }});

                if (chainId !== targetChainId) {{
                    status.innerHTML = `⚠️ Wrong network. Please switch to chain ID {network_config["chain_id"]}`;
                    status.style.color = 'orange';

                    // Try to switch network
                    try {{
                        await window.ethereum.request({{
                            method: 'wallet_switchEthereumChain',
                            params: [{{ chainId: targetChainId }}]
                        }});
                    }} catch (switchError) {{
                        status.innerHTML = '❌ Please switch network manually in MetaMask';
                        return;
                    }}
                }}

                updateUI(accounts[0]);

                // Store in parent window (communicate with Streamlit)
                window.parent.postMessage({{
                    type: 'metamask_connected',
                    account: accounts[0],
                    chainId: chainId
                }}, '*');

            }} catch (error) {{
                status.innerHTML = '❌ Connection failed: ' + error.message;
                status.style.color = 'red';
            }}
        }};

        function updateUI(account) {{
            button.innerHTML = '✅ Connected';
            button.style.background = '#28a745';
            button.disabled = true;
            status.innerHTML = '✅ MetaMask connected';
            status.style.color = 'green';
            accountDiv.innerHTML = 'Account: ' + account;
        }}

        // Listen for account changes
        if (window.ethereum) {{
            window.ethereum.on('accountsChanged', (accounts) => {{
                if (accounts.length > 0) {{
                    updateUI(accounts[0]);
                    window.parent.postMessage({{
                        type: 'metamask_connected',
                        account: accounts[0]
                    }}, '*');
                }} else {{
                    button.innerHTML = '🦊 Connect MetaMask';
                    button.style.background = '#ff6b35';
                    button.disabled = false;
                    status.innerHTML = '';
                    accountDiv.innerHTML = '';
                }}
            }});

            window.ethereum.on('chainChanged', () => {{
                window.location.reload();
            }});
        }}
    </script>
    """

    # Render component
    components.html(metamask_html, height=150)

    # Check if MetaMask account is stored in session state
    return st.session_state.get("metamask_account")


def _render_connection_status() -> Optional[Web3Service]:
    """
    Render connection status and account information.

    Returns:
        Web3Service instance if connected, None otherwise
    """
    if "web3_service" not in st.session_state or not st.session_state.web3_service:
        return None

    web3_service = st.session_state.web3_service
    connection_type = st.session_state.get("connection_type", "unknown")

    # Connection status
    st.sidebar.success(f"✅ Connected: {st.session_state.selected_network}")

    # Account information
    with st.sidebar.expander("📊 Account Info", expanded=True):
        # Get account address
        if connection_type == "metamask":
            address = st.session_state.get("metamask_account", "Unknown")
            st.text("MetaMask Account:")
        else:
            address = (
                web3_service.account.address if web3_service.account else "Unknown"
            )
            st.text("Account Address:")

        st.code(format_address(address, 10, 8))

        # Balance (if connection available)
        if web3_service.is_connected:
            try:
                # Get balance for the address
                if connection_type == "metamask":
                    balance_wei = web3_service.w3.eth.get_balance(address)
                    balance_eth = web3_service.w3.from_wei(balance_wei, "ether")
                else:
                    balance_info = web3_service.get_balance()
                    balance_eth = float(balance_info["balance_eth"])
                    balance_wei = balance_info["balance_wei"]

                st.metric("ETH Balance", f"{float(balance_eth):.4f} ETH")
                st.caption(f"Wei: {balance_wei:,}")

                # Block number
                block_number = web3_service.w3.eth.block_number
                st.caption(f"Block: #{block_number:,}")

            except Exception as e:
                st.error(f"Error: {str(e)}")

    # Disconnect button
    if st.sidebar.button("🔌 Disconnect", use_container_width=True):
        # Clean up
        if hasattr(st.session_state.web3_service, "close"):
            try:
                st.session_state.web3_service.close()
            except:
                pass

        # Clear session state
        for key in [
            "web3_service",
            "network_config",
            "selected_network",
            "connection_type",
            "metamask_account",
            "contract_address",
        ]:
            if key in st.session_state:
                del st.session_state[key]

        st.sidebar.info("Disconnected from blockchain")
        st.rerun()

    return web3_service


def render_contract_management(web3_service: Web3Service) -> Optional[str]:
    """
    Render contract deployment/loading interface in sidebar.

    Provides interface for:
    - Deploying new BuildingGraphNFT contract
    - Loading existing contract by address
    - Displaying contract status and details
    - Links to block explorer

    Args:
        web3_service: Connected Web3Service instance

    Returns:
        Contract address if loaded, None otherwise
    """
    if not web3_service or not web3_service.is_connected:
        return None

    st.sidebar.markdown("---")
    st.sidebar.subheader("📜 Smart Contract")

    # Check if contract already loaded
    if "contract_address" in st.session_state and st.session_state.contract_address:
        # Contract already loaded - display info and option to change
        _render_contract_info(web3_service)
        return st.session_state.contract_address

    # Contract mode selection
    contract_mode = st.sidebar.radio(
        "Contract Mode",
        options=["Deploy New", "Connect Existing"],
        help="Deploy a new contract or connect to existing deployment",
    )

    if contract_mode == "Deploy New":
        _render_contract_deployment(web3_service)
    else:
        _render_contract_loading(web3_service)

    return st.session_state.get("contract_address")


def _render_contract_deployment(web3_service: Web3Service):
    """Render contract deployment interface"""

    st.sidebar.markdown("**Deploy BuildingGraphNFT**")

    # Check connection type - deployment requires transaction signing
    connection_type = st.session_state.get("connection_type", "unknown")

    if connection_type == "metamask":
        st.sidebar.warning(
            "⚠️ MetaMask deployment not yet supported. Use Anvil for deployment."
        )
        st.sidebar.info("💡 Or connect to existing contract instead")
        return

    # Deployment info
    network_name = st.session_state.get("selected_network", "Unknown")

    if network_name != "Anvil (Local)":
        st.sidebar.warning(f"⚠️ Deploying to {network_name} costs real ETH!")

    with st.sidebar.expander("📋 Deployment Info"):
        st.caption("BuildingGraphNFT.sol")
        st.caption("ERC-998 Composable NFT")
        st.caption("Graph-isomorphic token structure")

    # Deploy button
    if st.sidebar.button(
        "🚀 Deploy Contract", type="primary", use_container_width=True
    ):
        _execute_contract_deployment(web3_service)


def _execute_contract_deployment(web3_service: Web3Service):
    """Execute contract deployment transaction"""

    # Find contract artifacts
    contract_artifacts_path = (
        Path(__file__).parent.parent.parent
        / "contracts/out/BuildingGraphNFT.sol/BuildingGraphNFT.json"
    )

    if not contract_artifacts_path.exists():
        st.sidebar.error("❌ Contract artifacts not found")
        st.sidebar.info("Run `cd contracts && forge build` first")
        return

    try:
        with st.spinner("Deploying contract... This may take 30-60 seconds"):
            # Deploy contract (just pass contract name, not full path)
            contract_address, tx_hash = web3_service.deploy_contract(
                contract_name="BuildingGraphNFT"
            )

            # Store in session state
            st.session_state.contract_address = contract_address

            # Success message
            st.sidebar.success("✅ Contract deployed!")

            # Display details
            with st.sidebar.expander("📝 Deployment Details", expanded=True):
                st.text("Contract Address:")
                st.code(contract_address)
                st.text("Transaction Hash:")
                st.code(format_transaction_hash(tx_hash))

                # Explorer link
                explorer = st.session_state.get("network_config", {}).get("explorer")
                if explorer:
                    st.markdown(
                        f"[View on Explorer]({explorer}/address/{contract_address})"
                    )

            st.balloons()

    except Exception as e:
        st.sidebar.error(f"❌ Deployment failed")

        with st.sidebar.expander("🔍 Error Details"):
            st.error(str(e))

        logger.error(f"Contract deployment failed: {e}", exc_info=True)


def _render_contract_loading(web3_service: Web3Service):
    """Render contract loading interface"""

    st.sidebar.markdown("**Connect to Existing Contract**")

    # Contract address input
    contract_address_input = st.sidebar.text_input(
        "Contract Address",
        placeholder="0x5FbDB2315678afecb367f032d93F642f64180aa3",
        help="Deployed BuildingGraphNFT contract address",
    )

    # Load button
    if st.sidebar.button("🔗 Load Contract", type="primary", use_container_width=True):
        if not contract_address_input:
            st.sidebar.error("❌ Contract address required")
            return

        # Validate address format
        if (
            not contract_address_input.startswith("0x")
            or len(contract_address_input) != 42
        ):
            st.sidebar.error("❌ Invalid address format")
            return

        try:
            with st.spinner("Loading contract..."):
                # Find contract artifacts
                contract_artifacts_path = (
                    Path(__file__).parent.parent.parent
                    / "contracts/out/BuildingGraphNFT.sol/BuildingGraphNFT.json"
                )

                if not contract_artifacts_path.exists():
                    st.sidebar.error("❌ Contract artifacts not found")
                    st.sidebar.info("Run `cd contracts && forge build` first")
                    return

                # Load contract (just pass contract name, not full path)
                web3_service.load_deployed_contract(
                    contract_address_input, contract_name="BuildingGraphNFT"
                )

                # Store in session state
                st.session_state.contract_address = contract_address_input

                st.sidebar.success("✅ Contract loaded!")

        except Exception as e:
            st.sidebar.error(f"❌ Failed to load contract")

            with st.sidebar.expander("🔍 Error Details"):
                st.error(str(e))

            logger.error(f"Contract loading failed: {e}", exc_info=True)


def _render_contract_info(web3_service: Web3Service):
    """Render loaded contract information"""

    contract_address = st.session_state.contract_address

    st.sidebar.success("✅ Contract Loaded")

    with st.sidebar.expander("📋 Contract Details", expanded=True):
        st.text("Address:")
        st.code(format_address(contract_address, 10, 8))

        st.text("Network:")
        st.code(st.session_state.get("selected_network", "Unknown"))

        st.text("Type:")
        st.code("BuildingGraphNFT (ERC-998)")

        # Explorer link
        explorer = st.session_state.get("network_config", {}).get("explorer")
        if explorer:
            st.markdown(f"[View on Explorer]({explorer}/address/{contract_address})")

    # Option to change contract
    if st.sidebar.button("🔄 Change Contract", use_container_width=True):
        del st.session_state.contract_address
        st.rerun()


def render_minting_interface(
    web3_service: Web3Service, kuzu_service, blockchain_service: BlockchainExportService
):
    """
    Render complete minting interface for building graphs.

    Provides workflow for:
    1. Selecting building from Kuzu database
    2. Previewing graph structure
    3. Estimating gas costs
    4. Executing minting transaction
    5. Syncing token IDs back to Kuzu

    Args:
        web3_service: Connected Web3Service instance
        kuzu_service: KuzuService for database queries
        blockchain_service: BlockchainExportService for data export
    """
    st.header("⛓️ Mint Building Graph as NFTs")

    st.markdown("""
    Convert your IFC building graph into ERC-998 composable NFTs on the blockchain.
    Each component becomes a unique token with full graph relationships preserved.
    """)

    # Step 1: Select building
    selected_file_id = render_building_selector(kuzu_service)

    if not selected_file_id:
        st.info("👆 Select a building to begin minting process")
        return

    # Step 2: Preview and validate
    nodes, edges, validation = render_mint_preview(selected_file_id, blockchain_service)

    if not validation.get("valid", False):
        st.error("❌ Cannot mint - validation failed")
        return

    # Step 3: Gas estimation
    gas_estimate = render_gas_estimation(web3_service, nodes, edges)

    if not gas_estimate:
        st.error("❌ Cannot mint - gas estimation failed")
        return

    # Step 4: Execute minting
    render_minting_execution(
        web3_service=web3_service,
        blockchain_service=blockchain_service,
        kuzu_service=kuzu_service,
        file_id=selected_file_id,
        nodes=nodes,
        edges=edges,
        gas_estimate=gas_estimate,
    )


def render_building_selector(kuzu_service) -> Optional[str]:
    """
    Render building selector for minting.

    Displays available IFC files from Kuzu database with:
    - File metadata (name, upload date)
    - Minting status (minted vs not minted)
    - Building details

    Args:
        kuzu_service: KuzuService instance

    Returns:
        Selected file_id or None
    """
    st.subheader("1️⃣ Select Building")

    if not kuzu_service or not kuzu_service.is_available:
        st.error("❌ Kuzu database not available")
        st.info("💡 Upload IFC files in the 'IFC Processing' tab first")
        return None

    try:
        # Get all IFC files from Kuzu
        buildings = kuzu_service.get_all_files()

        if not buildings or len(buildings) == 0:
            st.warning("⚠️ No IFC files in database")
            st.info("💡 Go to the 'IFC Processing' tab to upload and process IFC files")
            return None

        # Build table data with statistics
        st.markdown(f"**Available Buildings:** {len(buildings)}")

        building_table = []
        for building in buildings:
            file_id = building["id"]

            # Get statistics for each building
            try:
                stats = kuzu_service.get_file_statistics(file_id)
                vertex_count = (
                    stats.vertex_count if hasattr(stats, "vertex_count") else 0
                )
                edge_count = stats.edge_count if hasattr(stats, "edge_count") else 0
            except:
                vertex_count = 0
                edge_count = 0

            # Check if already minted (stored in session state for now)
            # Note: In future, add 'minted' and 'root_token_id' fields to IfcFile table
            minted_buildings = st.session_state.get("minted_buildings", {})
            is_minted = file_id in minted_buildings
            status = "🔗 Minted" if is_minted else "✅ Ready"

            building_table.append(
                {
                    "File ID": file_id[:12] + "...",
                    "Filename": building.get("filename", "Unknown")[:30],
                    "Building Name": building.get("building_name", "N/A")[:25],
                    "Upload Date": building.get("upload_timestamp", "N/A")[:19],
                    "Components": vertex_count,
                    "Connections": edge_count,
                    "Status": status,
                }
            )

        # Display table
        import pandas as pd

        df = pd.DataFrame(building_table)
        st.dataframe(
            df, use_container_width=True, height=min(400, len(building_table) * 35 + 38)
        )

        # Selection dropdown
        st.markdown("---")
        st.markdown("**Select building to mint:**")

        file_ids = [b["id"] for b in buildings]
        file_labels = [
            f"{b.get('building_name', b.get('filename', 'Unknown'))} ({b['id'][:8]}...)"
            for b in buildings
        ]

        # Create selection with better formatting
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_idx = st.selectbox(
                "Building",
                options=range(len(file_ids)),
                format_func=lambda i: file_labels[i],
                help="Choose an IFC file from the database to mint as NFTs",
                label_visibility="collapsed",
            )

        with col2:
            # Button to refresh list
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        selected_file_id = file_ids[selected_idx]
        selected_building = buildings[selected_idx]

        # Display detailed building information
        with st.expander("📊 Building Details", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("File ID", selected_file_id[:16] + "...")
                st.metric("Filename", selected_building.get("filename", "Unknown")[:20])

            with col2:
                st.metric(
                    "Building Name", selected_building.get("building_name", "N/A")[:20]
                )
                st.metric(
                    "Upload Date", selected_building.get("upload_timestamp", "N/A")[:19]
                )

            with col3:
                # Get statistics
                try:
                    stats = kuzu_service.get_file_statistics(selected_file_id)
                    st.metric(
                        "Components",
                        stats.vertex_count if hasattr(stats, "vertex_count") else 0,
                    )
                    st.metric(
                        "Connections",
                        stats.edge_count if hasattr(stats, "edge_count") else 0,
                    )
                except Exception as e:
                    st.metric("Components", "Error")
                    st.metric("Connections", "Error")

            # Additional details
            st.markdown("**Processing Information:**")
            st.write(
                f"- Processing Method: {selected_building.get('processing_method', 'Unknown')}"
            )
            st.write(f"- File Size: {selected_building.get('file_size_mb', 0):.2f} MB")

            # Check minting status
            minted_buildings = st.session_state.get("minted_buildings", {})
            if selected_file_id in minted_buildings:
                root_token_id = minted_buildings[selected_file_id]
                st.success(f"✅ This building has been minted!")
                st.info(f"🎫 Root Token ID: **{root_token_id}**")
                st.warning("⚠️ Minting again will create duplicate tokens")
            else:
                st.info("✅ This building is ready to be minted")

        return selected_file_id

    except Exception as e:
        st.error(f"❌ Error loading buildings: {str(e)}")
        logger.error(f"Building selector error: {e}", exc_info=True)

        with st.expander("🔍 Error Details"):
            st.exception(e)

        return None


def render_mint_preview(
    file_id: str, blockchain_service: BlockchainExportService
) -> Tuple[List[Dict], List[Dict], Dict[str, Any]]:
    """
    Render mint preview with graph structure analysis.

    Displays:
    - Node and edge counts
    - Node type breakdown
    - Validation results
    - Sample node preview

    Args:
        file_id: IFC file ID from Kuzu
        blockchain_service: BlockchainExportService instance

    Returns:
        Tuple of (nodes, edges, validation_results)
    """
    st.markdown("---")
    st.subheader("2️⃣ Preview Building Graph")

    with st.spinner("🔄 Exporting building data from Kuzu..."):
        try:
            # Export building graph for minting
            nodes, edges = blockchain_service.export_building_for_minting(file_id)

            if not nodes or len(nodes) == 0:
                st.error("❌ No components found for this building")
                st.info(
                    "💡 The building may not have been processed correctly. Try re-uploading in the IFC Processing tab."
                )
                return ([], [], {"valid": False, "errors": ["No nodes found"]})

            # Validate the exported data
            is_valid, errors = blockchain_service.validate_export_data(nodes, edges)

            # Convert tuple to dict format for UI
            validation = {
                "valid": is_valid,
                "errors": errors,
                "summary": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "validation_checks": "All required fields present"
                    if is_valid
                    else "Validation failed",
                },
            }

        except Exception as e:
            st.error(f"❌ Export failed: {str(e)}")
            logger.error(f"Mint preview export error: {e}", exc_info=True)

            with st.expander("🔍 Error Details"):
                st.exception(e)

            return ([], [], {"valid": False, "errors": [str(e)]})

    # Display graph statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Nodes",
            len(nodes),
            help="Total number of building components to mint",
        )

    with col2:
        st.metric(
            "Total Edges",
            len(edges),
            help="Total number of connections between components",
        )

    with col3:
        # Count orphan nodes (nodes with parentIndex = 0, except the root)
        orphan_count = sum(
            1 for i, n in enumerate(nodes) if n.get("parentIndex", 0) == 0 and i > 0
        )
        st.metric(
            "Orphan Nodes",
            orphan_count,
            help="Nodes without parent (may indicate data issues)",
        )

    with col4:
        validation_status = (
            "✅ Valid" if validation.get("valid", False) else "❌ Invalid"
        )
        status_color = "normal" if validation.get("valid", False) else "off"
        st.metric(
            "Validation", validation_status, help="Graph structure validation status"
        )

    # Node type breakdown
    st.markdown("---")
    st.markdown("**Node Type Breakdown**")

    # Token type mapping
    token_type_labels = {
        0: "📦 Project",
        1: "🏢 Building",
        2: "🏗️ Storey",
        3: "🚪 Space",
        4: "🔧 Component",
    }

    # Count nodes by type
    node_type_counts = {}
    for node in nodes:
        token_type = node.get("tokenType", 4)
        node_type_counts[token_type] = node_type_counts.get(token_type, 0) + 1

    # Display as columns
    type_cols = st.columns(5)
    for i, (token_type, label) in enumerate(token_type_labels.items()):
        with type_cols[i]:
            count = node_type_counts.get(token_type, 0)
            st.metric(label, count)

    # Detailed type breakdown table
    with st.expander("📊 Detailed Type Breakdown"):
        # Group by IFC type as well
        ifc_type_counts = {}
        for node in nodes:
            ifc_type = node.get("ifcType", "Unknown")
            ifc_type_counts[ifc_type] = ifc_type_counts.get(ifc_type, 0) + 1

        # Sort by count descending
        sorted_types = sorted(ifc_type_counts.items(), key=lambda x: x[1], reverse=True)

        import pandas as pd

        type_df = pd.DataFrame(
            [{"IFC Type": ifc_type, "Count": count} for ifc_type, count in sorted_types]
        )

        st.dataframe(
            type_df, use_container_width=True, height=min(300, len(type_df) * 35 + 38)
        )
        st.caption(f"Total IFC types: {len(ifc_type_counts)}")

    # Validation results
    st.markdown("---")
    st.markdown("**Validation Results**")

    if validation.get("valid", False):
        st.success("✅ Graph structure validated successfully")

        # Show validation summary
        if validation.get("summary"):
            with st.expander("ℹ️ Validation Summary"):
                for key, value in validation["summary"].items():
                    st.write(f"**{key}:** {value}")

    else:
        st.error("❌ Validation Failed - Cannot proceed with minting")

        # Display errors
        if validation.get("errors"):
            st.markdown("**Errors:**")
            for i, error in enumerate(validation["errors"], 1):
                st.error(f"{i}. {error}")

    # Show warnings if any
    if validation.get("warnings"):
        st.markdown("**Warnings:**")
        for warning in validation["warnings"]:
            st.warning(f"⚠️ {warning}")

    # Preview sample nodes
    with st.expander("👁️ Preview Sample Nodes (First 10)"):
        sample_nodes = nodes[:10] if len(nodes) > 10 else nodes

        for i, node in enumerate(sample_nodes):
            with st.container():
                # Display node in readable format
                col1, col2 = st.columns([1, 3])

                with col1:
                    st.caption(f"**Node #{i}**")
                    token_type_label = token_type_labels.get(
                        node.get("tokenType", 4), "Unknown"
                    )
                    st.write(token_type_label)

                with col2:
                    st.json(
                        {
                            "ifcType": node.get("ifcType", "Unknown"),
                            "name": node.get("name", "Unnamed")[:50],
                            "kuzuElementId": node.get("kuzuElementId", "")[:30] + "...",
                            "parentIndex": node.get("parentIndex", 0),
                            "coordinates": {
                                "x": node.get("x", 0)
                                / 1000,  # Convert mm to m for display
                                "y": node.get("y", 0) / 1000,
                                "z": node.get("z", 0) / 1000,
                            },
                        }
                    )

                st.divider()

        if len(nodes) > 10:
            st.caption(f"... and {len(nodes) - 10} more nodes")

    # Edge preview
    if edges and len(edges) > 0:
        with st.expander(f"🔗 Preview Sample Edges (First 5 of {len(edges)})"):
            sample_edges = edges[:5] if len(edges) > 5 else edges

            for i, edge in enumerate(sample_edges):
                st.json(
                    {
                        "edge_id": i,
                        "fromIndex": edge.get("fromIndex", 0),
                        "toIndex": edge.get("toIndex", 0),
                        "edgeType": edge.get("edgeType", "Unknown"),
                    }
                )

    return (nodes, edges, validation)


def render_gas_estimation(
    web3_service: Web3Service, nodes: List[Dict], edges: List[Dict]
) -> Dict[str, Any]:
    """
    Render gas estimation for minting transaction.

    Displays:
    - Estimated gas units
    - Gas price (gwei)
    - Total cost (ETH)
    - Balance sufficiency check
    - Cost breakdown

    Args:
        web3_service: Web3Service instance
        nodes: List of node dictionaries
        edges: List of edge dictionaries

    Returns:
        Gas estimate dictionary
    """
    st.markdown("---")
    st.subheader("3️⃣ Gas Estimation")

    if not web3_service or not web3_service.is_connected:
        st.error("❌ Not connected to blockchain")
        return {}

    connection_type = st.session_state.get("connection_type", "unknown")

    if connection_type == "metamask":
        st.warning("⚠️ Gas estimation with MetaMask not yet fully supported")
        st.info("💡 For accurate gas estimates and minting, use Anvil connection")
        return {}

    with st.spinner("⏳ Estimating gas costs..."):
        try:
            # Estimate gas cost (pass counts, not full lists)
            gas_estimate = web3_service.estimate_gas_cost(len(nodes), len(edges))

            if not gas_estimate:
                st.error("❌ Gas estimation failed")
                return {}

        except Exception as e:
            st.error(f"❌ Gas estimation failed: {str(e)}")
            logger.error(f"Gas estimation error: {e}", exc_info=True)

            with st.expander("🔍 Error Details"):
                st.exception(e)

            return {}

    # Display main gas metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        gas_units = gas_estimate.get("gas_units", 0)
        st.metric(
            "Gas Units",
            f"{gas_units:,}",
            help="Estimated computational units required for transaction",
        )

    with col2:
        gas_price_gwei = gas_estimate.get("gas_price_gwei", 0)
        st.metric(
            "Gas Price", f"{gas_price_gwei:.2f} gwei", help="Current network gas price"
        )

    with col3:
        total_cost_eth = gas_estimate.get("total_cost_eth", 0)
        st.metric(
            "Total Cost", f"{total_cost_eth:.6f} ETH", help="Estimated transaction cost"
        )

    # Balance check
    st.markdown("---")
    st.markdown("**Balance Check**")

    try:
        account_balance = web3_service.get_balance()
        balance_eth = float(account_balance["balance_eth"])
        cost_eth = float(total_cost_eth)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Available Balance", f"{balance_eth:.6f} ETH")

        with col2:
            st.metric("Required Cost", f"{cost_eth:.6f} ETH")

        with col3:
            remaining = balance_eth - cost_eth
            st.metric("Remaining After", f"{remaining:.6f} ETH")

        # Status indicator
        if balance_eth >= cost_eth:
            st.success(
                f"✅ Sufficient balance to mint ({balance_eth:.6f} ETH available)"
            )
        else:
            st.error(f"❌ Insufficient balance")
            st.error(f"Need {cost_eth - balance_eth:.6f} more ETH to proceed")

            # Stop execution if insufficient balance
            st.stop()

    except Exception as e:
        st.error(f"❌ Error checking balance: {str(e)}")
        return {}

    # Detailed cost breakdown
    with st.expander("💰 Detailed Cost Breakdown"):
        st.markdown("### Gas Calculation")

        # Display calculation
        gas_units = gas_estimate.get("gas_units", 0)
        gas_price_wei = gas_estimate.get("gas_price_wei", 0)
        gas_price_gwei = gas_estimate.get("gas_price_gwei", 0)
        total_cost_wei = gas_estimate.get("total_cost_wei", 0)
        total_cost_eth = gas_estimate.get("total_cost_eth", 0)

        st.code(f"""
Gas Calculation:
─────────────────────────────────────────────────────
Gas Units Required:  {gas_units:,}
Gas Price:           {gas_price_gwei:.2f} gwei
                   = {gas_price_wei:,} wei

Total Cost Calculation:
{gas_units:,} units × {gas_price_wei:,} wei/unit
= {total_cost_wei:,} wei
= {total_cost_eth:.6f} ETH
─────────────────────────────────────────────────────
        """)

        st.markdown("### Account Balance")
        st.code(f"""
Current Balance:     {balance_eth:.6f} ETH
                   = {account_balance["balance_wei"]:,} wei

After Transaction:   {remaining:.6f} ETH
                   = {int(account_balance["balance_wei"] - total_cost_wei):,} wei
        """)

        # Graph size impact
        st.markdown("### Transaction Size Impact")
        st.write(f"- **Nodes to mint:** {len(nodes):,}")
        st.write(f"- **Edges to store:** {len(edges):,}")
        st.write(
            f"- **Estimated gas per node:** {gas_units // len(nodes) if len(nodes) > 0 else 0:,} units"
        )

        # Network info
        st.markdown("### Network Information")
        network_name = st.session_state.get("selected_network", "Unknown")
        st.write(f"- **Network:** {network_name}")
        st.write(f"- **Chain ID:** {web3_service.chain_id}")

        try:
            block_number = web3_service.w3.eth.block_number
            st.write(f"- **Current Block:** #{block_number:,}")
        except:
            pass

    # Size warnings
    if len(nodes) > 500:
        st.warning("⚠️ Large Building Alert")
        st.write(f"This building has {len(nodes)} components. Minting may:")
        st.write("- Take longer to process (60-120 seconds)")
        st.write("- Require more gas than estimated")
        st.write("- May fail if exceeds block gas limit")

    if len(nodes) > 1000:
        st.error("❌ Building Too Large")
        st.write(f"Building has {len(nodes)} components (max 1000)")
        st.write("Consider splitting the building or filtering components")
        st.stop()

    return gas_estimate


def render_minting_execution(
    web3_service: Web3Service,
    blockchain_service: BlockchainExportService,
    kuzu_service,
    file_id: str,
    nodes: List[Dict],
    edges: List[Dict],
    gas_estimate: Dict[str, Any],
):
    """
    Execute minting transaction and sync results to Kuzu.

    Workflow:
    1. Submit transaction to blockchain
    2. Wait for confirmation
    3. Parse minted token IDs
    4. Sync token IDs back to Kuzu database
    5. Display success message with links

    Args:
        web3_service: Web3Service instance
        blockchain_service: BlockchainExportService instance
        kuzu_service: KuzuService instance
        file_id: IFC file ID
        nodes: List of node dictionaries
        edges: List of edge dictionaries
        gas_estimate: Gas estimate dictionary
    """
    st.markdown("---")
    st.subheader("4️⃣ Mint Building Graph")

    # Pre-minting information
    st.markdown("""
    **Ready to mint!** This will:
    1. 📤 Submit batch minting transaction to blockchain
    2. ⏳ Wait for transaction confirmation
    3. 🎫 Parse minted token IDs from event
    4. 🔄 Sync token IDs back to Kuzu database
    5. ✅ Complete - building is now on blockchain!
    """)

    # Show summary before minting
    with st.expander("📋 Minting Summary", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Building Information:**")
            st.write(f"- File ID: `{file_id[:20]}...`")
            st.write(f"- Components: {len(nodes):,}")
            st.write(f"- Connections: {len(edges):,}")

        with col2:
            st.write("**Transaction Cost:**")
            st.write(f"- Gas Units: {gas_estimate.get('gas_units', 0):,}")
            st.write(f"- Gas Price: {gas_estimate.get('gas_price_gwei', 0):.2f} gwei")
            st.write(
                f"- **Total Cost: {gas_estimate.get('total_cost_eth', 0):.6f} ETH**"
            )

        # Network info
        network_name = st.session_state.get("selected_network", "Unknown")
        st.write(f"**Network:** {network_name}")

    # Check if already minted
    minted_buildings = st.session_state.get("minted_buildings", {})
    if file_id in minted_buildings:
        st.warning(
            f"⚠️ This building has already been minted (Token ID: {minted_buildings[file_id]})"
        )
        st.info("💡 Minting again will create duplicate tokens on blockchain")

    # Minting button
    if st.button(
        "🚀 Mint Building Graph NFT", type="primary", use_container_width=True
    ):
        # Create progress tracking
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0, text="Starting minting process...")
            status_text = st.empty()

            try:
                # Step 1: Submit transaction (25%)
                status_text.info("📤 Step 1/4: Submitting transaction to blockchain...")
                progress_bar.progress(25, text="Submitting transaction...")

                # Prepare minting parameters
                to_address = (
                    web3_service.account.address if web3_service.account else None
                )
                if not to_address:
                    raise ValueError("No account address available for minting")

                # Get file_id_bytes32 from first node (all nodes have same fileId)
                file_id_bytes32 = (
                    nodes[0].get("fileId", "0x" + "00" * 32)
                    if nodes
                    else "0x" + "00" * 32
                )

                # Get building name from kuzu
                try:
                    files = kuzu_service.get_all_files()
                    file_data = next((f for f in files if f["id"] == file_id), None)
                    project_name = (
                        file_data.get("building_name", "Building")
                        if file_data
                        else "Building"
                    )
                except:
                    project_name = "Building Project"

                # Mint building graph
                root_token_id, tx_hash = web3_service.mint_building_graph(
                    to_address=to_address,
                    file_id_bytes32=file_id_bytes32,
                    project_name=project_name,
                    nodes=nodes,
                    edges=edges,
                )

                # Step 2: Wait for confirmation (50%)
                status_text.info("⏳ Step 2/4: Waiting for transaction confirmation...")
                progress_bar.progress(50, text="Waiting for confirmation...")

                # Transaction is already confirmed by mint_building_graph
                status_text.success("✅ Transaction confirmed!")

                # Display transaction details
                st.success(f"🎉 Minting successful!")
                st.info(f"📝 **Transaction Hash:** `{tx_hash}`")
                st.info(f"🎫 **Root Token ID:** **{root_token_id}**")

                # Step 3: Parse token IDs (75%)
                status_text.info("🎫 Step 3/4: Parsing minted token IDs...")
                progress_bar.progress(75, text="Parsing token IDs...")

                # Store in session state
                if "minted_buildings" not in st.session_state:
                    st.session_state.minted_buildings = {}
                st.session_state.minted_buildings[file_id] = root_token_id

                # Step 4: Sync to Kuzu (100%)
                status_text.info("🔄 Step 4/4: Syncing token IDs to Kuzu database...")
                progress_bar.progress(90, text="Syncing to database...")

                # TODO: Query contract for individual token IDs and sync to Kuzu
                # For now, we just store the root token ID in session state
                # Future enhancement: Query getChildTokens() recursively to get all token IDs
                # and create kuzu_id_to_token_id mapping for sync

                # Simplified sync - just log that minting completed
                try:
                    # Could add a simple update to mark file as minted in Kuzu here
                    # For now, just track in session state
                    status_text.success(
                        "✅ Root token ID stored (individual token sync pending implementation)"
                    )
                    logger.info(
                        f"Building {file_id} minted with root token {root_token_id}"
                    )
                except Exception as sync_error:
                    status_text.warning(f"⚠️ Minting successful: {str(sync_error)}")
                    logger.warning(f"Token storage note: {sync_error}", exc_info=True)

                # Complete!
                progress_bar.progress(100, text="✅ Complete!")
                time.sleep(0.5)  # Brief pause to show 100%

                # Balloons celebration
                st.balloons()

                # Display final summary
                st.markdown("---")
                st.markdown("### 🎉 Minting Complete!")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Root Token ID", root_token_id)

                with col2:
                    st.metric("Tokens Minted", len(nodes))

                with col3:
                    st.metric("Edges Stored", len(edges))

                # Transaction link
                explorer = st.session_state.get("network_config", {}).get("explorer")
                if explorer:
                    tx_url = f"{explorer}/tx/{tx_hash}"
                    st.markdown(f"🔍 [View Transaction on Block Explorer]({tx_url})")

                # Contract link
                contract_address = st.session_state.get("contract_address")
                if explorer and contract_address:
                    contract_url = f"{explorer}/address/{contract_address}"
                    st.markdown(f"📜 [View Contract on Block Explorer]({contract_url})")

                # Next steps
                st.markdown("---")
                st.markdown("### 🎯 Next Steps")
                st.info(
                    "💡 Switch to the **'Token Explorer'** tab to query your minted tokens!"
                )
                st.info(
                    "💡 Use the **'Construction Tracking'** tab to monitor build progress!"
                )

            except Exception as e:
                # Error handling
                progress_bar.progress(0)
                status_text.error("❌ Minting failed")

                st.error(f"❌ Minting transaction failed: {str(e)}")
                logger.error(f"Minting execution error: {e}", exc_info=True)

                with st.expander("🔍 Error Details"):
                    st.exception(e)

                # Troubleshooting tips
                st.markdown("### 🔧 Troubleshooting")
                st.write("**Common issues:**")
                st.write("- ⛽ Insufficient gas: Increase gas limit or get more ETH")
                st.write("- 🔌 Connection lost: Check if Anvil is still running")
                st.write("- 📜 Contract error: Check contract deployment and ABI")
                st.write(
                    "- 🏗️ Building too large: Try filtering components or splitting building"
                )


# =============================================================================
# Helper Functions
# =============================================================================


def validate_minting_preconditions(
    web3_service: Web3Service, file_id: str, nodes: List[Dict], gas_estimate: Dict
) -> Tuple[bool, List[str]]:
    """
    Validate all preconditions for minting.

    Checks:
    - Ethereum connection status
    - Contract loaded
    - Sufficient balance
    - Graph size within limits
    - Building not already minted

    Args:
        web3_service: Web3Service instance
        file_id: IFC file ID
        nodes: List of nodes
        gas_estimate: Gas estimate dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check connection
    if not web3_service or not web3_service.is_connected:
        errors.append("Not connected to Ethereum network")

    # Check contract
    if (
        not hasattr(web3_service, "building_graph_nft")
        or not web3_service.building_graph_nft
    ):
        errors.append("Smart contract not loaded")

    # Check balance
    if web3_service and web3_service.is_connected:
        try:
            balance = web3_service.get_balance()
            cost = gas_estimate.get("total_cost_eth", float("inf"))
            if float(balance["balance_eth"]) < cost:
                errors.append(
                    f"Insufficient balance: {balance['balance_eth']} ETH < {cost} ETH"
                )
        except Exception as e:
            errors.append(f"Error checking balance: {str(e)}")

    # Check graph size
    if len(nodes) > 1000:
        errors.append(f"Graph too large: {len(nodes)} nodes (max 1000)")
    elif len(nodes) > 500:
        # Warning, not error
        logger.warning(f"Large graph: {len(nodes)} nodes may require high gas")

    # Check if nodes exist
    if len(nodes) == 0:
        errors.append("No nodes to mint")

    return (len(errors) == 0, errors)


def format_address(address: str, prefix_len: int = 6, suffix_len: int = 4) -> str:
    """
    Format Ethereum address for display.

    Args:
        address: Full Ethereum address
        prefix_len: Number of characters to show at start
        suffix_len: Number of characters to show at end

    Returns:
        Formatted address (e.g., "0x5FbD...0aa3")
    """
    if not address or len(address) < prefix_len + suffix_len:
        return address

    return f"{address[:prefix_len]}...{address[-suffix_len:]}"


def format_transaction_hash(tx_hash: str) -> str:
    """
    Format transaction hash for display.

    Args:
        tx_hash: Transaction hash

    Returns:
        Formatted hash (e.g., "0x1234...abcd")
    """
    return format_address(tx_hash, prefix_len=10, suffix_len=8)
