"""
Web3 Integration Service for Ethereum Blockchain Interaction.

Handles connection to Ethereum nodes, contract deployment, and transaction
management for minting building graphs as ERC-998 composable NFTs.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal

from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt, Wei
from eth_account import Account
from eth_account.signers.local import LocalAccount


class Web3Service:
    """
    Web3 service for Ethereum blockchain interaction.

    Manages connections to Ethereum nodes (Anvil/Ganache/Sepolia/Mainnet),
    contract deployment, transaction signing, and event monitoring.
    """

    def __init__(
        self,
        rpc_url: str = "http://127.0.0.1:8545",
        private_key: Optional[str] = None,
        chain_id: int = 31337,  # Default to Anvil
    ):
        """
        Initialize Web3 service.

        Args:
            rpc_url: Ethereum node RPC URL
            private_key: Private key for transaction signing (without 0x prefix)
            chain_id: Network chain ID (31337=Anvil, 11155111=Sepolia, 1=Mainnet)
        """
        self.logger = logging.getLogger(__name__)
        self.rpc_url = rpc_url
        self.chain_id = chain_id

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.is_connected = False

        # Account management
        self.account: Optional[LocalAccount] = None
        if private_key:
            self.account = Account.from_key(private_key)
            self.logger.info(f"Account loaded: {self.account.address}")

        # Contract references
        self.building_graph_nft: Optional[Contract] = None
        self.contract_address: Optional[str] = None

        # Check connection
        self._check_connection()

    def _check_connection(self) -> bool:
        """Check if connected to Ethereum node"""
        try:
            self.is_connected = self.w3.is_connected()
            if self.is_connected:
                block_number = self.w3.eth.block_number
                chain_id = self.w3.eth.chain_id
                self.logger.info(
                    f"Connected to Ethereum node: chain_id={chain_id}, "
                    f"block={block_number}, rpc={self.rpc_url}"
                )
            else:
                self.logger.warning(f"Failed to connect to {self.rpc_url}")
            return self.is_connected
        except Exception as e:
            self.logger.error(f"Connection check failed: {e}")
            self.is_connected = False
            return False

    def load_contract_abi(
        self,
        contract_name: str = "BuildingGraphNFT",
        artifacts_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Load contract ABI from Foundry build artifacts.

        Args:
            contract_name: Name of the contract
            artifacts_path: Path to Foundry out/ directory

        Returns:
            Contract ABI dict

        Raises:
            FileNotFoundError: If ABI file not found
        """
        if artifacts_path is None:
            # Default to project contracts/out/ directory
            artifacts_path = Path(__file__).parent.parent.parent / "contracts" / "out"

        abi_file = artifacts_path / f"{contract_name}.sol" / f"{contract_name}.json"

        if not abi_file.exists():
            raise FileNotFoundError(
                f"Contract ABI not found: {abi_file}\n"
                f"Run 'forge build' to generate contract artifacts"
            )

        with open(abi_file, "r") as f:
            contract_json = json.load(f)

        self.logger.info(f"Loaded contract ABI: {contract_name}")
        return contract_json

    def deploy_contract(
        self,
        contract_name: str = "BuildingGraphNFT",
        constructor_args: Optional[List[Any]] = None,
        gas_limit: Optional[int] = None,
    ) -> Tuple[str, TxReceipt]:
        """
        Deploy BuildingGraphNFT contract to blockchain.

        Args:
            contract_name: Name of contract to deploy
            constructor_args: Constructor arguments (BuildingGraphNFT has none)
            gas_limit: Optional gas limit override

        Returns:
            Tuple of (contract_address, transaction_receipt)

        Raises:
            ValueError: If no account configured
            Exception: If deployment fails
        """
        if not self.account:
            raise ValueError("No account configured for deployment")

        if not self.is_connected:
            raise ValueError("Not connected to Ethereum node")

        # Load contract artifacts
        contract_json = self.load_contract_abi(contract_name)
        abi = contract_json["abi"]
        bytecode = contract_json["bytecode"]["object"]

        # Create contract factory
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)

        # Build constructor transaction
        constructor_args = constructor_args or []

        # Estimate gas if not provided
        if gas_limit is None:
            gas_limit = (
                Contract.constructor(*constructor_args).estimate_gas(
                    {"from": self.account.address}
                )
                + 100000
            )  # Add buffer

        # Get current gas price
        gas_price = self.w3.eth.gas_price

        # Build and sign transaction
        nonce = self.w3.eth.get_transaction_count(self.account.address)

        transaction = Contract.constructor(*constructor_args).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": self.chain_id,
            }
        )

        # Sign transaction
        signed_txn = self.account.sign_transaction(transaction)

        # Send transaction
        self.logger.info(f"Deploying {contract_name}...")
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] == 1:
            self.contract_address = receipt["contractAddress"]
            self.logger.info(
                f"Contract deployed successfully at {self.contract_address}"
            )

            # Load contract instance
            self.building_graph_nft = self.w3.eth.contract(
                address=self.contract_address, abi=abi
            )

            return (self.contract_address, receipt)
        else:
            raise Exception(f"Contract deployment failed: {receipt}")

    def load_deployed_contract(
        self, contract_address: str, contract_name: str = "BuildingGraphNFT"
    ) -> Contract:
        """
        Load already-deployed contract instance.

        Args:
            contract_address: Address of deployed contract
            contract_name: Name of contract

        Returns:
            Contract instance
        """
        contract_json = self.load_contract_abi(contract_name)
        abi = contract_json["abi"]

        self.contract_address = contract_address
        self.building_graph_nft = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )

        self.logger.info(f"Loaded contract at {contract_address}")
        return self.building_graph_nft

    def mint_building_graph(
        self,
        to_address: str,
        file_id_bytes32: str,
        project_name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        gas_limit: Optional[int] = None,
    ) -> Tuple[int, TxReceipt]:
        """
        Mint complete building graph as ERC-998 composable NFTs.

        Calls BuildingGraphNFT.mintBuildingGraph() with graph data.

        Args:
            to_address: Address to receive tokens
            file_id_bytes32: IFC file ID as bytes32
            project_name: Name of the building project
            nodes: List of GraphNodeMetadata dicts
            edges: List of GraphEdge dicts
            gas_limit: Optional gas limit override

        Returns:
            Tuple of (project_token_id, transaction_receipt)

        Raises:
            ValueError: If contract not loaded or account not configured
        """
        if not self.building_graph_nft:
            raise ValueError("Contract not loaded. Deploy or load contract first.")

        if not self.account:
            raise ValueError("No account configured for minting")

        # Convert nodes to tuples for contract call
        node_tuples = [
            (
                node["tokenType"],
                node["kuzuElementId"],
                node["topologicVertexId"],
                node["ifcGuid"],
                node["ifcType"],
                node["name"],
                node["x"],
                node["y"],
                node["z"],
                node["fileId"],
                node["buildingId"],
                node["parentTokenId"],
                node["childTokenIds"],
                node["status"],
                node["mintedAt"],
                node["exists"],
            )
            for node in nodes
        ]

        # Convert edges to tuples (8 fields now with fromIndex/toIndex)
        edge_tuples = [
            (
                edge.get("fromTokenId", 0),
                edge.get("toTokenId", 0),
                edge.get("fromIndex", 0),       # Array index for from node
                edge.get("toIndex", 0),         # Array index for to node
                edge["connectionType"],
                edge["edgeProperties"],
                edge["kuzuEdgeId"],
                edge["bidirectional"],
            )
            for edge in edges
        ]

        # Estimate gas if not provided
        if gas_limit is None:
            try:
                estimated_gas = self.building_graph_nft.functions.mintBuildingGraph(
                    Web3.to_checksum_address(to_address),
                    file_id_bytes32,
                    project_name,
                    node_tuples,
                    edge_tuples,
                ).estimate_gas({"from": self.account.address})

                gas_limit = estimated_gas + 500000  # Add buffer
                self.logger.info(f"Gas estimation succeeded: {estimated_gas:,} + 500k buffer = {gas_limit:,}")
            except Exception as e:
                self.logger.warning(f"Gas estimation failed: {e}. Using default formula.")
                # Default gas limit based on node count
                gas_limit = 200000 + (len(nodes) * 150000) + (len(edges) * 50000)
                self.logger.info(f"Using default gas calculation: {gas_limit:,}")

        # Log detailed minting parameters
        self.logger.info(
            f"Minting building graph: {len(nodes)} nodes, {len(edges)} edges, gas_limit={gas_limit:,}"
        )

        # Check block gas limit
        try:
            latest_block = self.w3.eth.get_block('latest')
            block_gas_limit = latest_block['gasLimit']
            self.logger.info(f"Block gas limit: {block_gas_limit:,}")

            if gas_limit > block_gas_limit:
                self.logger.error(
                    f"WARNING: Transaction gas limit ({gas_limit:,}) exceeds block gas limit ({block_gas_limit:,})"
                )
                self.logger.error("This transaction will fail! Reduce building size or increase Anvil gas limit.")
        except Exception as e:
            self.logger.warning(f"Could not check block gas limit: {e}")

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.eth.gas_price

        transaction = self.building_graph_nft.functions.mintBuildingGraph(
            Web3.to_checksum_address(to_address),
            file_id_bytes32,
            project_name,
            node_tuples,
            edge_tuples,
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": self.chain_id,
            }
        )

        self.logger.info(f"Transaction built with gas={transaction['gas']:,}")

        # Sign and send
        signed_txn = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] == 1:
            # Parse BuildingGraphMinted event to get project token ID
            project_token_id = self._parse_building_graph_minted_event(receipt)

            self.logger.info(
                f"Building graph minted successfully. Project token ID: {project_token_id}"
            )
            self.logger.info(f"Gas used: {receipt['gasUsed']:,} / {gas_limit:,} ({receipt['gasUsed']/gas_limit*100:.1f}%)")
            return (project_token_id, receipt)
        else:
            # Log detailed failure information
            self.logger.error(f"Minting transaction FAILED (status=0)")
            self.logger.error(f"Transaction hash: {receipt['transactionHash'].hex()}")
            self.logger.error(f"Gas used: {receipt['gasUsed']:,} / {gas_limit:,}")
            self.logger.error(f"Block number: {receipt['blockNumber']}")

            # Save error details to file
            import json
            from pathlib import Path
            from datetime import datetime

            error_file = Path.cwd() / "minting_error_details.json"
            error_data = {
                'timestamp': datetime.now().isoformat(),
                'transaction_hash': receipt['transactionHash'].hex(),
                'status': receipt['status'],
                'gas_used': receipt['gasUsed'],
                'gas_limit': gas_limit,
                'block_number': receipt['blockNumber'],
                'num_nodes': len(nodes),
                'num_edges': len(edges),
                'from': receipt['from'],
                'to': receipt['to'],
                'receipt': str(receipt)
            }

            try:
                existing_errors = []
                if error_file.exists():
                    with open(error_file, 'r') as f:
                        existing_errors = json.load(f)

                existing_errors.append(error_data)

                with open(error_file, 'w') as f:
                    json.dump(existing_errors, f, indent=2)

                self.logger.error(f"Error details saved to {error_file}")
            except Exception as log_error:
                self.logger.warning(f"Could not save error details: {log_error}")

            raise Exception(f"Minting transaction failed: {receipt}")

    def _parse_building_graph_minted_event(self, receipt: TxReceipt) -> int:
        """
        Parse BuildingGraphMinted event from transaction receipt.

        Args:
            receipt: Transaction receipt

        Returns:
            Project token ID
        """
        # Get BuildingGraphMinted event logs
        logs = self.building_graph_nft.events.BuildingGraphMinted().process_receipt(
            receipt
        )

        if not logs:
            raise ValueError("BuildingGraphMinted event not found in receipt")

        # Extract project token ID from first event
        event = logs[0]
        project_token_id = event["args"]["projectTokenId"]

        return project_token_id

    def get_token_by_kuzu_id(self, kuzu_element_id: str) -> int:
        """
        Query token ID by Kuzu element ID.

        Args:
            kuzu_element_id: Kuzu database element ID

        Returns:
            Token ID (0 if not found)
        """
        if not self.building_graph_nft:
            raise ValueError("Contract not loaded")

        token_id = self.building_graph_nft.functions.getTokenByKuzuId(
            kuzu_element_id
        ).call()

        return token_id

    def get_token_by_ifc_guid(self, ifc_guid: str) -> int:
        """
        Query token ID by IFC GUID.

        Args:
            ifc_guid: IFC GlobalId

        Returns:
            Token ID (0 if not found)
        """
        if not self.building_graph_nft:
            raise ValueError("Contract not loaded")

        token_id = self.building_graph_nft.functions.getTokenByIfcGuid(ifc_guid).call()

        return token_id

    def get_node_metadata(self, token_id: int) -> Dict[str, Any]:
        """
        Get graph node metadata for a token.

        Args:
            token_id: Token ID

        Returns:
            Node metadata dict
        """
        if not self.building_graph_nft:
            raise ValueError("Contract not loaded")

        metadata = self.building_graph_nft.functions.nodeMetadata(token_id).call()

        # Convert tuple to dict
        return {
            "tokenType": metadata[0],
            "kuzuElementId": metadata[1],
            "topologicVertexId": metadata[2],
            "ifcGuid": metadata[3],
            "ifcType": metadata[4],
            "name": metadata[5],
            "x": metadata[6],
            "y": metadata[7],
            "z": metadata[8],
            "fileId": metadata[9],
            "buildingId": metadata[10],
            "parentTokenId": metadata[11],
            "childTokenIds": metadata[12],
            "status": metadata[13],
            "mintedAt": metadata[14],
            "exists": metadata[15],
        }

    def get_child_tokens(self, parent_token_id: int) -> List[int]:
        """
        Get all child token IDs for a parent token.

        Args:
            parent_token_id: Parent token ID

        Returns:
            List of child token IDs
        """
        if not self.building_graph_nft:
            raise ValueError("Contract not loaded")

        child_ids = self.building_graph_nft.functions.getChildTokens(
            parent_token_id
        ).call()

        return list(child_ids)

    def estimate_gas_cost(self, node_count: int, edge_count: int) -> Dict[str, Any]:
        """
        Estimate gas cost for minting a building graph.

        Args:
            node_count: Number of nodes
            edge_count: Number of edges

        Returns:
            Dict with gas estimate, cost in ETH, and USD estimate
        """
        # Rough estimation formula based on contract operations
        base_gas = 200000  # Base transaction cost + project token
        per_node_gas = 150000  # Per node minting + metadata storage
        per_edge_gas = 50000  # Per edge storage

        estimated_gas = (
            base_gas + (node_count * per_node_gas) + (edge_count * per_edge_gas)
        )

        # Get current gas price
        gas_price_wei = self.w3.eth.gas_price
        gas_price_gwei = self.w3.from_wei(gas_price_wei, "gwei")

        # Calculate cost
        cost_wei = estimated_gas * gas_price_wei
        cost_eth = self.w3.from_wei(cost_wei, "ether")

        return {
            "gas_units": estimated_gas,
            "estimated_gas": estimated_gas,  # Keep for compatibility
            "gas_price_wei": gas_price_wei,
            "gas_price_gwei": float(gas_price_gwei),
            "total_cost_wei": cost_wei,
            "cost_wei": cost_wei,  # Keep for compatibility
            "total_cost_eth": float(cost_eth),
            "cost_eth": float(cost_eth),  # Keep for compatibility
            "node_count": node_count,
            "edge_count": edge_count,
        }

    def get_balance(self, address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ETH balance for an address.

        Args:
            address: Address to check (defaults to current account)

        Returns:
            Dict with balance in Wei and ETH
        """
        if address is None:
            if not self.account:
                raise ValueError("No address provided and no account configured")
            address = self.account.address

        balance_wei = self.w3.eth.get_balance(address)
        balance_eth = self.w3.from_wei(balance_wei, "ether")

        return {
            "address": address,
            "balance_wei": balance_wei,
            "balance_eth": float(balance_eth),
        }

    def close(self):
        """Clean up resources"""
        self.logger.info("Web3 service closed")
