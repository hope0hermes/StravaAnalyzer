"""
Activity analysis orchestration.

This module coordinates the analysis of individual activities.

NOTE: Data is pre-split into raw/moving DataFrames upstream. The analyzer
uses StreamSplitter to create separate DataFrames and computes metrics
for each mode independently.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

from ..data import StreamSplitter
from ..exceptions import ActivityTypeError, ProcessingError
from ..metrics import MetricsCalculator
from ..models import ActivityType
from ..settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """
    Result of activity analysis containing metrics for both modes.

    Attributes:
        raw_metrics: Metrics computed from all data points
        moving_metrics: Metrics computed from moving-only data points
        activity_id: ID of the analyzed activity
        activity_type: Type of activity (ride, run, etc.)
    """

    raw_metrics: dict[str, float | str]
    moving_metrics: dict[str, float | str]
    activity_id: int
    activity_type: str


class AnalyzerProtocol(Protocol):
    """Protocol for analyzers."""

    def analyze(
        self, activity_row: pd.Series, stream_df: pd.DataFrame
    ) -> AnalysisResult:
        """Analyze an activity and return metrics."""
        ...


class ActivityAnalyzer:
    """
    Analyzes individual activities to compute metrics.

    This class coordinates metric calculation and handles activity-specific logic.
    Data is split into raw and moving DataFrames before metric computation.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the analyzer.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.metrics_calculator = MetricsCalculator(settings)
        self.stream_splitter = StreamSplitter()
        self.logger = logging.getLogger(__name__)

    def analyze(
        self, activity_row: pd.Series, stream_df: pd.DataFrame
    ) -> AnalysisResult:
        """
        Analyze a single activity and compute all metrics.

        Splits data into raw and moving DataFrames first, then computes
        metrics independently for each mode.

        Args:
            activity_row: Series containing activity metadata
            stream_df: DataFrame containing activity stream data

        Returns:
            AnalysisResult containing metrics for both raw and moving modes

        Raises:
            ActivityTypeError: If activity type is not supported
            ProcessingError: If there's an error during analysis
        """
        try:
            activity_type = ActivityType(activity_row["type"])
            activity_id = int(activity_row["id"])

            # Validate supported activity types
            if activity_type not in [
                ActivityType.RIDE,
                ActivityType.VIRTUAL_RIDE,
                ActivityType.RUN,
            ]:
                raise ActivityTypeError(f"Unsupported activity type: {activity_type}")

            # Split data into raw and moving DataFrames
            split_result = self.stream_splitter.split(stream_df)

            # Calculate metrics for raw data (includes power curve and interval analysis)
            raw_metrics = self.metrics_calculator.compute_all_metrics(
                split_result.raw_df,
                activity_type.value.lower(),
                include_power_curve=True,
            )
            raw_metrics = self._convert_numpy_types(raw_metrics)

            # Calculate metrics for moving data (same as raw - includes all metrics)
            moving_metrics = self.metrics_calculator.compute_all_metrics(
                split_result.moving_df,
                activity_type.value.lower(),
                include_power_curve=True,
            )
            moving_metrics = self._convert_numpy_types(moving_metrics)

            self.logger.debug(
                f"Analyzed activity {activity_id} ({activity_type.value})"
            )

            return AnalysisResult(
                raw_metrics=raw_metrics,
                moving_metrics=moving_metrics,
                activity_id=activity_id,
                activity_type=activity_type.value,
            )

        except ActivityTypeError:
            raise
        except Exception as e:
            raise ProcessingError(
                f"Error analyzing activity {activity_row['id']}: {e}"
            ) from e

    def _convert_numpy_types(
        self, metrics: dict[str, float | str]
    ) -> dict[str, float | str]:
        """
        Convert numpy types to Python native types.

        Args:
            metrics: Dictionary potentially containing numpy types

        Returns:
            Dictionary with converted types
        """
        return {
            k: (float(v) if isinstance(v, (np.integer, np.floating)) else v)
            for k, v in metrics.items()
        }

    def supports_activity_type(self, activity_type: ActivityType) -> bool:
        """
        Check if an activity type is supported for analysis.

        Args:
            activity_type: Type of activity

        Returns:
            True if supported, False otherwise
        """
        return activity_type in [
            ActivityType.RIDE,
            ActivityType.VIRTUAL_RIDE,
            ActivityType.RUN,
        ]
