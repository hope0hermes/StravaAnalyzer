"""
Base classes and protocols for metric calculators.

Defines the interface that all metric calculators should follow.
"""

from abc import ABC, abstractmethod
from typing import Protocol

import pandas as pd

from ..constants import TimeConstants
from ..settings import Settings


class MetricCalculatorProtocol(Protocol):
    """Protocol defining the interface for metric calculators."""

    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """
        Calculate metrics from stream data.

        Args:
            stream_df: DataFrame containing activity stream data
            moving_only: If True, only use data where moving=True

        Returns:
            Dictionary of calculated metrics
        """
        ...


class BaseMetricCalculator(ABC):
    """
    Abstract base class for metric calculators.

    Provides common functionality and enforces interface consistency.
    """

    def __init__(self, settings: Settings):
        """
        Initialize calculator with settings.

        Args:
            settings: Application settings containing thresholds and configuration
        """
        self.settings = settings

    @abstractmethod
    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """
        Calculate metrics from stream data.

        Args:
            stream_df: DataFrame containing activity stream data
            moving_only: If True, only use data where moving=True

        Returns:
            Dictionary of calculated metrics
        """
        raise NotImplementedError("Subclasses must implement calculate()")

    def _filter_moving(
        self, stream_df: pd.DataFrame, moving_only: bool
    ) -> pd.DataFrame:
        """
        Filter dataframe to moving data if requested.

        Args:
            stream_df: Input dataframe
            moving_only: Whether to filter to moving-only data

        Returns:
            Filtered or original dataframe
        """
        if moving_only and "moving" in stream_df.columns:
            return stream_df[stream_df["moving"]].copy()
        return stream_df.copy()

    def _get_prefix(self, moving_only: bool) -> str:
        """
        Get metric name prefix based on data type.

        Args:
            moving_only: Whether metrics are from moving-only data

        Returns:
            Prefix string ('raw_' or 'moving_')
        """
        return "moving_" if moving_only else "raw_"

    def _calculate_time_deltas(
        self, stream_df: pd.DataFrame, clip_gaps: bool = False
    ) -> pd.Series:
        """
        Calculate time differences between consecutive data points.

        Args:
            stream_df: DataFrame containing 'time' column
            clip_gaps: If True, clip large deltas (>GAP_DETECTION_THRESHOLD) to
                prevent filtered gaps from affecting moving metrics. Use False
                for raw metrics.

        Returns:
            Series of time deltas in seconds
        """
        if "time" not in stream_df.columns or len(stream_df) == 0:
            # Fallback: assume 1-second intervals
            return pd.Series([1.0] * len(stream_df), index=stream_df.index)

        # Calculate differences between consecutive time points
        time_diffs = stream_df["time"].diff()
        # First point gets the value from second point, or 1.0 if single point
        time_diffs.iloc[0] = time_diffs.iloc[1] if len(time_diffs) > 1 else 1.0

        # Handle any negative or zero deltas
        time_diffs = time_diffs.clip(lower=1.0)

        # For moving metrics, clip large deltas that span filtered-out gaps
        if clip_gaps:
            time_diffs = time_diffs.clip(upper=TimeConstants.GAP_DETECTION_THRESHOLD)

        return time_diffs

    def _time_weighted_mean(
        self, values: pd.Series, stream_df: pd.DataFrame, clip_gaps: bool = False
    ) -> float:
        """
        Calculate time-weighted mean of a series.

        Args:
            values: Series of values to average
            stream_df: DataFrame containing 'time' column for weighting
            clip_gaps: If True, clip time deltas >2s (for moving metrics)

        Returns:
            Time-weighted mean
        """
        if values.empty:
            return 0.0

        # Get time deltas
        time_deltas = self._calculate_time_deltas(
            stream_df.loc[values.index], clip_gaps=clip_gaps
        )

        # Calculate weighted mean: Σ(value × Δt) / Σ(Δt)
        weighted_sum = (values * time_deltas).sum()
        total_time = time_deltas.sum()

        return float(weighted_sum / total_time) if total_time > 0 else 0.0

    def _get_total_duration(self, stream_df: pd.DataFrame) -> float:
        """
        Get total duration of activity in seconds.

        Args:
            stream_df: DataFrame containing 'time' column

        Returns:
            Total duration in seconds
        """
        if "time" not in stream_df.columns or len(stream_df) == 0:
            return float(len(stream_df))

        # Total duration is the time deltas sum
        return float(self._calculate_time_deltas(stream_df).sum())
