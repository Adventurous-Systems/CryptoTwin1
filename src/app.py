"""
Main Streamlit application for IFC TopologicPy Kuzu pipeline.

Provides a clean interface for uploading IFC files, processing them through
TopologicPy, storing in Kuzu database, and visualizing results.
"""

import streamlit as st
import tempfile
import os
from pathlib import Path
import pandas as pd

# Configure Streamlit page
st.set_page_config(
    page_title="IFC TopologicPy Kuzu",
    page_icon="🏗️",
    layout="wide"
)

# Import our services and models
import sys
from pathlib import Path

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from models.data_models import ProcessingConfig, ProcessingMethod
    from models.topologic_models import TopologicGraph
    from services.ifc_processor import IFCProcessorService
    from services.kuzu_service import KuzuService
    from services.topologic_viz_service import TopologicVisualizationService
    from services.blockchain_service import BlockchainExportService
    from ui.blockchain_ui import (
        render_blockchain_connection_panel,
        render_contract_management,
        render_minting_interface
    )
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error("Please ensure all dependencies are installed and you're running from the src directory")
    st.error(f"Current working directory: {os.getcwd()}")
    st.error(f"Python path: {sys.path[:3]}...")
    st.stop()


def initialize_services():
    """Initialize all application services in session state"""

    # IFC Processor Service
    if 'ifc_processor' not in st.session_state:
        st.session_state.ifc_processor = IFCProcessorService()

    # Kuzu Database Service
    if 'kuzu_service' not in st.session_state:
        try:
            st.session_state.kuzu_service = KuzuService()
            if st.session_state.kuzu_service.is_available:
                st.session_state.kuzu_status = "✅ Connected"
            else:
                st.session_state.kuzu_status = "⚠️ Available but not initialized"
        except Exception as e:
            st.session_state.kuzu_service = None
            st.session_state.kuzu_status = f"❌ Error: {str(e)}"

    # TopologicPy Visualization Service
    if 'viz_service' not in st.session_state:
        st.session_state.viz_service = TopologicVisualizationService()
        if st.session_state.viz_service.is_available:
            st.session_state.viz_status = "✅ TopologicPy Available"
        else:
            st.session_state.viz_status = "⚠️ TopologicPy Not Available"

    # Blockchain Export Service (only if Kuzu available)
    if 'blockchain_service' not in st.session_state:
        if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
            st.session_state.blockchain_service = BlockchainExportService(
                st.session_state.kuzu_service
            )
        else:
            st.session_state.blockchain_service = None

    # Initialize minted buildings tracker
    if 'minted_buildings' not in st.session_state:
        st.session_state.minted_buildings = {}  # {file_id: root_token_id}


def render_sidebar_enhanced():
    """Enhanced sidebar with blockchain integration

    Returns:
        Dictionary with sidebar values for use in tabs
    """

    sidebar_values = {}

    with st.sidebar:
        st.header("Configuration")

        # File upload
        uploaded_file = st.file_uploader(
            "Choose an IFC file",
            type=['ifc'],
            help="Upload an IFC (Industry Foundation Classes) file for processing"
        )
        sidebar_values['uploaded_file'] = uploaded_file

        # Processing configuration
        st.subheader("Processing Options")

        processing_method = st.selectbox(
            "Processing Method",
            options=[ProcessingMethod.DIRECT, ProcessingMethod.TRADITIONAL],
            format_func=lambda x: x.value.title(),
            help="Direct: Fast Graph.ByIFCPath | Traditional: IFC→Topology→Graph"
        )
        sidebar_values['processing_method'] = processing_method

        transfer_dictionaries = st.checkbox(
            "Transfer IFC Dictionaries",
            value=True,
            help="Preserve IFC metadata in graph vertices and edges"
        )
        sidebar_values['transfer_dictionaries'] = transfer_dictionaries

        tolerance = st.number_input(
            "Geometric Tolerance",
            min_value=0.001,
            max_value=1.0,
            value=0.001,
            step=0.001,
            help="Tolerance for geometric operations"
        )
        sidebar_values['tolerance'] = tolerance

        # IFC entity type filtering
        st.subheader("IFC Entity Types")
        use_type_filter = st.checkbox("Filter by IFC types", value=False)

        include_types = []
        if use_type_filter:
            default_types = [
                "IfcWall", "IfcSlab", "IfcBeam", "IfcColumn",
                "IfcDoor", "IfcWindow", "IfcSpace", "IfcRoom"
            ]
            include_types = st.multiselect(
                "Select IFC types to include:",
                options=default_types,
                default=default_types[:4]
            )
        sidebar_values['include_types'] = include_types

        # Visualization configuration
        st.subheader("Visualization Options")

        # TopologicPy renderer selection
        if st.session_state.viz_service.is_available:
            renderer = st.selectbox(
                "TopologicPy Renderer",
                options=st.session_state.viz_service.get_available_renderers(),
                index=0,  # Default to "browser"
                help="Choose renderer for TopologicPy visualization (browser recommended for Streamlit)"
            )

            # Centrality analysis option
            use_centrality = st.checkbox(
                "Calculate Closeness Centrality",
                value=True,
                help="Calculate and display closeness centrality for vertex sizing"
            )

            # Store in session state
            st.session_state.viz_renderer = renderer
            st.session_state.viz_centrality = use_centrality
        else:
            st.warning("TopologicPy visualization not available")

        # Building/File Selection
        st.subheader("File Management")
        if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
            files = st.session_state.kuzu_service.get_all_files()

            if files:
                st.write("**Loaded IFC Files:**")
                file_options = {f"{f['filename']} ({f['building_name']})": f['id'] for f in files}

                if 'selected_file_id' not in st.session_state:
                    st.session_state.selected_file_id = None

                selected_display = st.selectbox(
                    "Select IFC File to View:",
                    options=["All Files"] + list(file_options.keys()),
                    help="Choose a specific IFC file to filter the view"
                )

                if selected_display == "All Files":
                    st.session_state.selected_file_id = None
                else:
                    st.session_state.selected_file_id = file_options[selected_display]

                # Show file details
                if st.session_state.selected_file_id:
                    selected_file = next((f for f in files if f['id'] == st.session_state.selected_file_id), None)
                    if selected_file:
                        st.info(f"📁 **{selected_file['filename']}**\n\n🏢 {selected_file['building_name']}\n\n📅 {selected_file['upload_timestamp']}")
            else:
                st.info("No IFC files loaded yet")
        else:
            st.info("Database not available")

        # Database status
        st.subheader("Database Status")
        st.write(st.session_state.kuzu_status)
        st.write(st.session_state.viz_status)

        # Clear database button (only if Kuzu is available)
        if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
            if st.button("Clear Database", help="Remove all data from Kuzu database"):
                if st.session_state.kuzu_service.clear_database():
                    st.success("Database cleared successfully")
                    # Reset session state
                    if 'selected_file_id' in st.session_state:
                        del st.session_state.selected_file_id
                    st.rerun()
                else:
                    st.error("Failed to clear database")
        else:
            st.info("Database operations not available")

        # ============================================
        # NEW: BLOCKCHAIN SECTIONS
        # ============================================

        st.markdown("---")

        # Blockchain connection
        web3_service = render_blockchain_connection_panel()

        # Contract management (only if connected)
        if web3_service and web3_service.is_connected:
            contract_address = render_contract_management(web3_service)

    return sidebar_values


def render_ifc_processing_tab(sidebar_values):
    """Tab 1: IFC Processing (existing functionality)"""

    uploaded_file = sidebar_values['uploaded_file']
    processing_method = sidebar_values['processing_method']
    include_types = sidebar_values['include_types']
    transfer_dictionaries = sidebar_values['transfer_dictionaries']
    tolerance = sidebar_values['tolerance']

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Processing Status")

        # Show current database statistics (filtered by selected file if any)
        if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
            # Get statistics for selected file or all files
            if hasattr(st.session_state, 'selected_file_id') and st.session_state.selected_file_id:
                stats = st.session_state.kuzu_service.get_file_statistics(st.session_state.selected_file_id)
                selected_file = next((f for f in st.session_state.kuzu_service.get_all_files()
                                    if f['id'] == st.session_state.selected_file_id), None)
                context_msg = f"File: {selected_file['filename']}" if selected_file else "Selected File"
            else:
                stats = st.session_state.kuzu_service.get_graph_statistics()
                context_msg = "All Files"

            if stats.vertex_count > 0:
                st.info(f"{context_msg}: {stats.vertex_count} vertices, {stats.edge_count} edges")

                # Show IFC type breakdown
                if stats.ifc_types:
                    st.subheader(f"IFC Types - {context_msg}")
                    df_types = pd.DataFrame([
                        {"IFC Type": ifc_type, "Count": count}
                        for ifc_type, count in stats.ifc_types.items()
                    ])
                    st.dataframe(df_types, use_container_width=True)
            else:
                if hasattr(st.session_state, 'selected_file_id') and st.session_state.selected_file_id:
                    st.info("Selected file has no data")
                else:
                    st.info("Database is empty - upload and process an IFC file to get started")
        else:
            st.warning("Kuzu database not available - processing will work but data won't be stored")

        # File processing
        if uploaded_file is not None:
            if st.button("Process IFC File", type="primary"):
                process_ifc_file(
                    uploaded_file,
                    processing_method,
                    include_types,
                    transfer_dictionaries,
                    tolerance
                )

    with col2:
        st.header("Database Statistics")

        # Real-time stats (filtered by selected file if any)
        if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
            # Get statistics for selected file or all files
            if hasattr(st.session_state, 'selected_file_id') and st.session_state.selected_file_id:
                current_stats = st.session_state.kuzu_service.get_file_statistics(st.session_state.selected_file_id)
            else:
                current_stats = st.session_state.kuzu_service.get_graph_statistics()

            st.metric("Vertices", current_stats.vertex_count)
            st.metric("Edges", current_stats.edge_count)
            st.metric("IFC Types", len(current_stats.ifc_types))

            # File count metric
            files = st.session_state.kuzu_service.get_all_files()
            st.metric("IFC Files", len(files))
        else:
            st.metric("Database", "Not Available")
            st.write("📊 Statistics will appear here when Kuzu database is connected")

    # Visualization section
    if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
        current_stats = st.session_state.kuzu_service.get_graph_statistics()
        if current_stats.vertex_count > 0:
            st.header("Graph Visualization")
            render_graph_visualization()
    else:
        st.header("Graph Visualization")
        st.info("🎨 3D visualizations will appear here when data is processed and stored in Kuzu database")


def render_blockchain_minting_tab():
    """Tab 2: Blockchain Minting with prerequisite checking"""

    st.header("⛓️ Mint Building Graph as NFTs")

    # ============================================
    # Prerequisite Checks (with helpful guidance)
    # ============================================

    # Check 1: Kuzu Database
    if not st.session_state.kuzu_service or not st.session_state.kuzu_service.is_available:
        st.warning("⚠️ **Prerequisite 1/4**: Kuzu database not available")
        st.info("💡 The database needs to be running. Check the 'Database Status' section in the sidebar.")
        return
    else:
        st.success("✅ **Prerequisite 1/4**: Kuzu database connected")

    # Check 2: Building Data
    stats = st.session_state.kuzu_service.get_graph_statistics()
    if stats.vertex_count == 0:
        st.warning("⚠️ **Prerequisite 2/4**: No building data in database")
        st.info("💡 Go to the **'🏗️ IFC Processing'** tab to upload and process an IFC file first.")
        return
    else:
        st.success(f"✅ **Prerequisite 2/4**: {stats.vertex_count} components ready in database")

    # Check 3: Blockchain Connection
    if 'web3_service' not in st.session_state or not st.session_state.web3_service:
        st.warning("⚠️ **Prerequisite 3/4**: Not connected to blockchain")
        st.info("💡 Connect your wallet in the **'⛓️ Blockchain Connection'** section of the sidebar.")

        with st.expander("📖 Connection Instructions"):
            st.markdown("""
            **For Local Development (Anvil):**
            1. Start Anvil in a terminal: `anvil`
            2. In the sidebar, select "Anvil (Local)" network
            3. Click "🔌 Connect to Anvil" (uses default account #0)

            **For Testnet (Sepolia):**
            1. Install MetaMask browser extension
            2. Get Sepolia ETH from a faucet
            3. In the sidebar, select "Sepolia (Testnet)"
            4. Click "🦊 Connect MetaMask"
            """)
        return
    else:
        network = st.session_state.get('selected_network', 'Unknown')
        st.success(f"✅ **Prerequisite 3/4**: Connected to {network}")

    # Check 4: Smart Contract
    if 'contract_address' not in st.session_state or not st.session_state.contract_address:
        st.warning("⚠️ **Prerequisite 4/4**: Smart contract not loaded")
        st.info("💡 In the **'📜 Smart Contract'** section of the sidebar:")
        st.markdown("""
        - **Deploy New**: Create a new BuildingGraphNFT contract (requires gas)
        - **Connect Existing**: Load a previously deployed contract
        """)
        return
    else:
        contract_addr = st.session_state.contract_address
        st.success(f"✅ **Prerequisite 4/4**: Contract loaded at `{contract_addr[:10]}...`")

    # ============================================
    # All Prerequisites Met - Show Minting Interface
    # ============================================

    st.markdown("---")
    st.success("🎉 **All prerequisites met!** Ready to mint building graph as NFTs.")

    # Render the complete minting interface
    render_minting_interface(
        web3_service=st.session_state.web3_service,
        kuzu_service=st.session_state.kuzu_service,
        blockchain_service=st.session_state.blockchain_service
    )


def render_token_explorer_tab():
    """Tab 3: Token Explorer (placeholder for Task 1.6.4)"""

    st.header("🔍 Token Explorer")

    # Check if any buildings are minted
    minted_buildings = st.session_state.get('minted_buildings', {})

    if not minted_buildings:
        st.info("💡 No buildings have been minted yet")
        st.markdown("""
        **To mint your first building:**
        1. Go to the **'🏗️ IFC Processing'** tab
        2. Upload and process an IFC file
        3. Switch to the **'⛓️ Blockchain Minting'** tab
        4. Follow the minting workflow
        """)
        return

    # Show minted buildings
    st.subheader(f"📊 Minted Buildings ({len(minted_buildings)})")

    for file_id, root_token_id in minted_buildings.items():
        with st.expander(f"Building: {file_id[:20]}... (Root Token: {root_token_id})", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Root Token ID", root_token_id)

            with col2:
                # Get token count (if web3_service available)
                if st.session_state.get('web3_service'):
                    try:
                        children = st.session_state.web3_service.get_child_tokens(root_token_id)
                        st.metric("Total Tokens", len(children) + 1)
                    except:
                        st.metric("Total Tokens", "N/A")
                else:
                    st.metric("Total Tokens", "N/A")

            with col3:
                # Get building name from Kuzu
                try:
                    files = st.session_state.kuzu_service.get_all_files()
                    file_data = next((f for f in files if f['id'] == file_id), None)
                    if file_data:
                        st.write(f"**Building:** {file_data.get('building_name', 'Unknown')}")
                except:
                    pass

            st.info("🚧 **Full token explorer coming in Task 1.6.4**")
            st.markdown("""
            **Planned Features:**
            - 🌳 Token hierarchy tree visualization
            - 📋 Token details and metadata viewer
            - 🔗 Graph connections explorer
            - 🔍 Advanced query interface
            """)

    # Add refresh button
    if st.button("🔄 Refresh Token List"):
        st.rerun()


def main():
    """Main Streamlit application with tabbed interface"""

    st.title("🏗️ IFC TopologicPy Kuzu Pipeline")
    st.markdown("Process IFC files → Store in Kuzu → Mint as NFTs → Track construction")

    # ========================================
    # 1. Initialize Services
    # ========================================
    initialize_services()

    # ========================================
    # 2. Enhanced Sidebar
    # ========================================
    sidebar_values = render_sidebar_enhanced()

    # ========================================
    # 3. Main Content (Tabbed Interface)
    # ========================================
    tab1, tab2, tab3 = st.tabs([
        "🏗️ IFC Processing",
        "⛓️ Blockchain Minting",
        "🔍 Token Explorer"
    ])

    with tab1:
        render_ifc_processing_tab(sidebar_values)

    with tab2:
        render_blockchain_minting_tab()

    with tab3:
        render_token_explorer_tab()


def process_ifc_file(uploaded_file, method, include_types, transfer_dictionaries, tolerance):
    """Process uploaded IFC file through the complete pipeline"""
    
    # Create progress indicator
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Save uploaded file to temporary location
        status_text.text("Saving uploaded file...")
        progress_bar.progress(10)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            temp_file_path = tmp_file.name
        
        # Configure processing
        status_text.text("Configuring processing...")
        progress_bar.progress(20)
        
        config = ProcessingConfig(
            method=method,
            include_types=include_types if include_types else None,
            transfer_dictionaries=transfer_dictionaries,
            tolerance=tolerance
        )
        
        # Process IFC file
        status_text.text("Processing IFC file with TopologicPy...")
        progress_bar.progress(40)
        
        graph, result, original_graph = st.session_state.ifc_processor.process_ifc_file(temp_file_path, config)

        # Store original TopologicPy Graph for visualization
        if original_graph:
            st.session_state.original_topologic_graph = original_graph
        
        if result.success:
            # Try to store in Kuzu database
            if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
                status_text.text("Storing graph in Kuzu database...")
                progress_bar.progress(70)

                # Extract filename for building tracking
                filename = uploaded_file.name if uploaded_file else "unknown.ifc"

                if st.session_state.kuzu_service.store_graph(graph, filename=filename):
                    status_text.text("Processing completed successfully!")
                    progress_bar.progress(100)
                    st.success(f"✅ {result.message} and stored in database")

                    # Reset selected file to show all files after upload
                    if hasattr(st.session_state, 'selected_file_id'):
                        st.session_state.selected_file_id = None
                else:
                    status_text.text("Processing completed (database storage failed)")
                    progress_bar.progress(100)
                    st.warning("⚠️ Processing succeeded but failed to store in database")
            else:
                status_text.text("Processing completed (no database storage)")
                progress_bar.progress(100)
                st.success(f"✅ {result.message} (not stored - Kuzu database unavailable)")
            
            # Show results
            if result.stats:
                col1, col2, col3 = st.columns(3)
                col1.metric("Vertices", result.stats.vertex_count)
                col2.metric("Edges", result.stats.edge_count)
                col3.metric("Processing Time", f"{result.processing_time:.2f}s")
                
                # Show IFC types found
                if result.stats.ifc_types:
                    st.subheader("IFC Types Processed")
                    types_df = pd.DataFrame([
                        {"Type": ifc_type, "Count": count}
                        for ifc_type, count in result.stats.ifc_types.items()
                    ])
                    st.dataframe(types_df)
                
        else:
            status_text.text("")
            progress_bar.progress(0)
            st.error(f"❌ Processing failed: {result.message}")
            
            if result.error_details:
                st.error(f"Details: {result.error_details}")
    
    except Exception as e:
        status_text.text("")
        progress_bar.progress(0)
        st.error(f"Unexpected error: {str(e)}")
        
    finally:
        # Cleanup temporary file
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
        except:
            pass


def render_graph_visualization():
    """Render graph visualization using TopologicPy.Show"""

    # Check if we have original TopologicPy Graph in session state
    if 'original_topologic_graph' not in st.session_state:
        st.warning("No TopologicPy Graph available for native visualization")
        st.info("📝 TopologicPy visualization requires the original Graph object from processing")

        # Fallback: Show basic data from Kuzu if available
        if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
            # Get vertices filtered by selected file if any
            if hasattr(st.session_state, 'selected_file_id') and st.session_state.selected_file_id:
                vertices = st.session_state.kuzu_service.get_vertices_by_file(st.session_state.selected_file_id)
            else:
                vertices = st.session_state.kuzu_service.get_all_vertices_with_coordinates()

            if vertices:
                st.subheader("📊 Vertex Data from Database")
                vertices_df = pd.DataFrame(vertices)
                st.dataframe(vertices_df, use_container_width=True)
            else:
                st.info("No data available - process an IFC file first")
        return

    # Get visualization configuration
    renderer = getattr(st.session_state, 'viz_renderer', 'browser')
    use_centrality = getattr(st.session_state, 'viz_centrality', True)

    try:
        original_graph = st.session_state.original_topologic_graph

        # Use TopologicPy visualization service
        if st.session_state.viz_service.is_available:
            st.subheader("🎨 TopologicPy Native Visualization")

            # Display visualization options
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"Renderer: {renderer}")
            with col2:
                st.info(f"Centrality Analysis: {'Enabled' if use_centrality else 'Disabled'}")

            # Choose visualization method based on centrality setting
            if use_centrality:
                success = st.session_state.viz_service.show_graph_with_centrality(
                    original_graph,
                    renderer=renderer
                )
            else:
                success = st.session_state.viz_service.show_graph_visualization(
                    original_graph,
                    renderer=renderer,
                    vertex_size_key="closeness_centrality",
                    vertex_label_key="IFC_name",
                    vertex_group_key="IFC_type"
                )

            if not success:
                st.error("TopologicPy visualization failed - check console for details")

        else:
            st.error("TopologicPy visualization service not available")

        # Show complementary data from database
        if st.session_state.kuzu_service and st.session_state.kuzu_service.is_available:
            st.subheader("📊 Vertex Details from Database")

            # Get vertices filtered by selected file if any
            if hasattr(st.session_state, 'selected_file_id') and st.session_state.selected_file_id:
                vertices = st.session_state.kuzu_service.get_vertices_by_file(st.session_state.selected_file_id)
            else:
                vertices = st.session_state.kuzu_service.get_all_vertices_with_coordinates()

            if vertices:
                vertices_df = pd.DataFrame(vertices)
                st.dataframe(
                    vertices_df,
                    column_config={
                        "id": st.column_config.TextColumn("ID", width="small"),
                        "ifc_type": st.column_config.TextColumn("IFC Type"),
                        "name": st.column_config.TextColumn("Name"),
                        "x": st.column_config.NumberColumn("X", format="%.3f"),
                        "y": st.column_config.NumberColumn("Y", format="%.3f"),
                        "z": st.column_config.NumberColumn("Z", format="%.3f"),
                        "ifc_guid": st.column_config.TextColumn("IFC GUID", width="medium"),
                        "file_id": st.column_config.TextColumn("File ID", width="small"),
                        "building_id": st.column_config.TextColumn("Building ID", width="small")
                    },
                    use_container_width=True
                )

    except Exception as e:
        st.error(f"TopologicPy visualization error: {e}")
        st.error("Ensure TopologicPy is properly installed and the renderer is supported")


if __name__ == "__main__":
    main()