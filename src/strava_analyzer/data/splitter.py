"""
Stream data splitting for raw and moving analysis.

This module handles the creation of separate DataFrames for
raw and moving-only analysis, with proper time handling.

The split happens BEFORE metrics computation:
1. Raw DataFrame: Copy of original data (all points)
2. Moving DataFrame: Filtered to moving=True, with contiguous time

Both DataFrames are then processed independently through the metrics pipeline.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SplitResult:
    """Result of splitting stream data into raw and moving DataFrames."""

    raw_df: pd.DataFrame
    moving_df: pd.DataFrame
    raw_duration_seconds: float
    moving_duration_seconds: float


class StreamSplitterProtocol(Protocol):
    """Protocol for stream splitters."""

    def split(self, stream_df: pd.DataFrame) -> SplitResult:
        """Split stream into raw and moving DataFrames."""
        ...


class StreamSplitter:
    """
    Splits stream data into raw and moving DataFrames.

    This class creates two independent DataFrames from the input stream:
    - Raw: All data points with original timestamps
    - Moving: Only moving points with contiguous time (reset to 0, 1, 2, ...)

    The moving DataFrame's time reset ensures that rolling calculations
    (Normalized Power, MMP, etc.) work correctly without gaps.
    """

    def __init__(self) -> None:
        """Initialize the stream splitter."""
        self.logger = logging.getLogger(__name__)

    def split(self, stream_df: pd.DataFrame) -> SplitResult:
        """
        Split stream into raw and moving DataFrames.

        Args:
            stream_df: Processed stream DataFrame with 'time' and 'moving' columns

        Returns:
            SplitResult containing both DataFrames and duration information
        """
        if stream_df.empty:
            self.logger.warning("Empty stream DataFrame provided")
            return SplitResult(
                raw_df=pd.DataFrame(),
                moving_df=pd.DataFrame(),
                raw_duration_seconds=0.0,
                moving_duration_seconds=0.0,
            )

        # Create raw DataFrame (copy of original)
        raw_df = self._create_raw_dataframe(stream_df)

        # Create moving DataFrame with contiguous time
        moving_df = self._create_moving_dataframe(stream_df)

        # Calculate durations
        raw_duration = self._calculate_duration(raw_df)
        moving_duration = self._calculate_moving_duration(stream_df)

        self.logger.debug(
            f"Split stream: raw={len(raw_df)} points ({raw_duration:.1f}s), "
            f"moving={len(moving_df)} points ({moving_duration:.1f}s)"
        )

        return SplitResult(
            raw_df=raw_df,
            moving_df=moving_df,
            raw_duration_seconds=raw_duration,
            moving_duration_seconds=moving_duration,
        )

    def _create_raw_dataframe(self, stream_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create the raw DataFrame (all data points).

        Args:
            stream_df: Original stream DataFrame

        Returns:
            Copy of the stream with all data points
        """
        raw_df = stream_df.copy()
        raw_df = raw_df.reset_index(drop=True)
        return raw_df

    def _create_moving_dataframe(self, stream_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create the moving DataFrame with contiguous time.

        Filters to only moving points and resets time to be contiguous
        (0, 1, 2, ...) to ensure rolling calculations work correctly.

        Args:
            stream_df: Original stream DataFrame

        Returns:
            Filtered DataFrame with contiguous time
        """
        # Filter to moving data
        if "moving" in stream_df.columns:
            moving_df = stream_df[stream_df["moving"]].copy()
        else:
            # If no moving column, assume all data is moving
            self.logger.warning("No 'moving' column found, using all data")
            moving_df = stream_df.copy()

        if moving_df.empty:
            self.logger.warning("No moving data points found")
            return pd.DataFrame()

        # Store original time for reference (useful for debugging)
        if "time" in moving_df.columns:
            moving_df["original_time"] = moving_df["time"].copy()
            # Reset time to contiguous integers (simulating 1-second intervals)
            moving_df["time"] = np.arange(len(moving_df), dtype=float)

        # Reset index
        moving_df = moving_df.reset_index(drop=True)

        return moving_df

    def _calculate_duration(self, df: pd.DataFrame) -> float:
        """
        Calculate total duration from a DataFrame.

        Args:
            df: DataFrame with 'time' column

        Returns:
            Duration in seconds
        """
        if df.empty or "time" not in df.columns:
            return 0.0

        return float(df["time"].iloc[-1] - df["time"].iloc[0])

    def _calculate_moving_duration(self, stream_df: pd.DataFrame) -> float:
        """
        Calculate actual moving duration from original timestamps.

        This accounts for the actual time spent moving, not just
        the number of moving points.

        Args:
            stream_df: Original stream DataFrame

        Returns:
            Moving duration in seconds
        """
        if stream_df.empty or "time" not in stream_df.columns:
            return 0.0

        if "moving" not in stream_df.columns:
            return self._calculate_duration(stream_df)

        moving_mask = stream_df["moving"]
        if not moving_mask.any():
            return 0.0

        # Calculate time deltas for moving points only
        # Use the actual time differences, clipping large gaps (>2s)
        moving_indices = stream_df.index[moving_mask]
        if len(moving_indices) < 2:
            return float(len(moving_indices))

        time_at_moving = stream_df.loc[moving_indices, "time"]
        time_diffs = time_at_moving.diff()
        time_diffs.iloc[0] = 1.0  # First point counts as 1 second

        # Clip large gaps (these represent non-moving periods that were filtered)
        time_diffs = time_diffs.clip(upper=2.0)

        return float(time_diffs.sum())


def create_splitter() -> StreamSplitter:
    """Factory function to create a StreamSplitter."""
    return StreamSplitter()
