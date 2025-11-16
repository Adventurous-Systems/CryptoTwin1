"""
Quick fix for blockchain UI to load deployed contract address automatically
"""

import streamlit as st
import logging
from pathlib import Path
from services.web3_service import Web3Service

logger = logging.getLogger(__name__)


def render_contract_connection_fix(web3_service: Web3Service):
    """
    Render contract connection with automatic address loading
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("📜 Smart Contract")

    # Try to load contract address from file
    contract_address = None
    try:
        contract_file = Path(__file__).parent.parent.parent / "contract_address.txt"
        if contract_file.exists():
            with open(contract_file, "r") as f:
                contract_address = f.read().strip()
                st.sidebar.success(
                    f"✅ Found deployed contract: {contract_address[:10]}..."
                )
        else:
            st.sidebar.warning("⚠️ No contract address found")
    except Exception as e:
        logger.error(f"Error loading contract address: {e}")
        st.sidebar.error("❌ Failed to load contract address")

    # Manual address input
    contract_address_input = st.sidebar.text_input(
        "Contract Address:",
        value=contract_address or "",
        help="BuildingGraphNFT contract address",
        placeholder="0x...",
    )

    if st.sidebar.button("🔗 Load Contract", use_container_width=True):
        if not contract_address_input:
            st.sidebar.error("❌ Please enter a contract address")
            return

        if (
            not contract_address_input.startswith("0x")
            or len(contract_address_input) != 42
        ):
            st.sidebar.error("❌ Invalid address format")
            return

        try:
            with st.spinner("Loading contract..."):
                # Check if contract artifacts exist
                artifacts_path = (
                    Path(__file__).parent.parent.parent / "contracts" / "out"
                )
                abi_file = (
                    artifacts_path / "BuildingGraphNFT.sol" / "BuildingGraphNFT.json"
                )

                if not abi_file.exists():
                    st.sidebar.error("❌ Contract artifacts not found")
                    st.sidebar.info("Run `cd contracts && forge build` first")
                    return

                # Load contract
                web3_service.load_deployed_contract(contract_address_input)

                # Store in session state
                st.session_state.contract_address = contract_address_input

                st.sidebar.success("✅ Contract loaded!")

        except Exception as e:
            st.sidebar.error(f"❌ Failed to load contract")
            with st.sidebar.expander("🔍 Error Details"):
                st.error(str(e))
            logger.error(f"Contract loading failed: {e}", exc_info=True)

    # Show contract info if loaded
    if "contract_address" in st.session_state:
        st.sidebar.success("✅ Contract Loaded")
        with st.sidebar.expander("📋 Contract Details", expanded=True):
            st.text("Address:")
            st.code(st.session_state.contract_address)
            st.text("Network:")
            st.code("Anvil (Local)")
            st.text("Type:")
            st.code("BuildingGraphNFT (ERC-998)")

        if st.sidebar.button("🔄 Change Contract", use_container_width=True):
            del st.session_state.contract_address
            st.rerun()
