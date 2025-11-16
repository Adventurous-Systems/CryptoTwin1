"""
Core data models for IFC TopologicPy Kuzu application.

These models define the structure for data passing between services and UI components.
Based on patterns from adventurous_topologic with enhancements for Kuzu integration.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import time
from pydantic import BaseModel, Field


class ProcessingMethod(Enum):
    """IFC processing method enumeration"""
    DIRECT = "direct"
    TRADITIONAL = "traditional"


class ProcessingStatus(Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    LOADING_FILE = "loading_file"
    EXTRACTING_GRAPH = "extracting_graph"
    PROCESSING_VERTICES = "processing_vertices"
    PROCESSING_EDGES = "processing_edges"
    STORING_DATABASE = "storing_database"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingConfig:
    """Configuration for IFC processing"""
    method: ProcessingMethod = ProcessingMethod.DIRECT
    include_types: List[str] = None
    transfer_dictionaries: bool = True
    tolerance: float = 0.001
    max_file_size_mb: int = 100


class GraphStats(BaseModel):
    """Basic graph statistics"""
    vertex_count: int = 0
    edge_count: int = 0
    ifc_types: Dict[str, int] = Field(default_factory=dict)
    processing_time: float = 0.0
    file_size_mb: float = 0.0


class ProcessingResult(BaseModel):
    """Result of IFC processing operation"""
    success: bool
    message: str
    stats: Optional[GraphStats] = None
    error_details: Optional[str] = None
    processing_time: float = 0.0