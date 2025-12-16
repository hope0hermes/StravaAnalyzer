"""
Data access and processing layer.

This package contains modules for loading, cleaning, and managing activity data.
"""

from .loader import ActivityDataLoader
from .processor import StreamDataProcessor
from .repository import ActivityRepository
from .splitter import SplitResult, StreamSplitter, create_splitter

__all__ = [
    "ActivityDataLoader",
    "ActivityRepository",
    "SplitResult",
    "StreamDataProcessor",
    "StreamSplitter",
    "create_splitter",
]
