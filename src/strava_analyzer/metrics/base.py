"""
Base classes and protocols for metric calculators.

Defines the interface that all metric calculators should follow.

NOTE: As of the refactoring (December 2025), the data is split into raw and moving
DataFrames BEFORE metric calculation. Calculators no longer need to filter or
apply prefixes - they receive pre-split data and return unprefixed metric names.
"""

from abc import ABC, abstractmethod
from typing import Protocol

import pandas as pd

from ..settings import Settings


class MetricCalculatorProtocol(Protocol):
    """Protocol defining the interface for metric calculators."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate metrics from stream data.

        Args:
            stream_df: DataFrame containing activity stream data (already split)

        Returns:
            Dictionary of calculated metrics (no prefix needed)
        """
        ...


class BaseMetricCalculator(ABC):
    """
    Abstract base class for metric calculators.

    Provides common functionality and enforces interface consistency.

    NOTE: Calculators receive pre-split DataFrames (either raw or moving).
    The splitting is done upstream by StreamSplitter, so calculators don't
    need to filter data or apply prefixes.
    """

    def __init__(self, settings: Settings):
        """
        Initialize calculator with settings.

        Args:
            settings: Application settings containing thresholds and configuration
        """
        self.settings = settings

    @abstractmethod
    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate metrics from stream data.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of calculated metrics (no prefix)
        """
        raise NotImplementedError("Subclasses must implement calculate()")

    def _calculate_time_deltas(self, stream_df: pd.DataFrame) -> pd.Series:
        """
        Calculate time differences between consecutive data points.

        Since the data is pre-split (raw or moving with contiguous time),
        we no longer need gap clipping logic. The moving DataFrame already
        has contiguous time (0, 1, 2, ...).

        Args:
            stream_df: DataFrame containing 'time' column

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

        # For moving data with contiguous time, deltas will naturally be ~1.0
        # For raw data, larger deltas represent stopped periods
        # No special handling needed anymore since data is pre-split

        return time_diffs

    def _time_weighted_mean(self, values: pd.Series, stream_df: pd.DataFrame) -> float:
        """
        Calculate time-weighted mean of a series.

        Args:
            values: Series of values to average
            stream_df: DataFrame containing 'time' column for weighting

        Returns:
            Time-weighted mean
        """
        if values.empty:
            return 0.0

        # Get time deltas
        time_deltas = self._calculate_time_deltas(stream_df.loc[values.index])

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
