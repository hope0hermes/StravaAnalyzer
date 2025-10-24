"""
Activity analysis orchestration.

This module coordinates the analysis of individual activities.
"""

import logging
from typing import Protocol

import numpy as np
import pandas as pd

from ..exceptions import ActivityTypeError, ProcessingError
from ..metrics import MetricsCalculator
from ..models import ActivityType
from ..settings import Settings

logger = logging.getLogger(__name__)


class AnalyzerProtocol(Protocol):
    """Protocol for analyzers."""

    def analyze(
        self, activity_row: pd.Series, stream_df: pd.DataFrame
    ) -> dict[str, float]:
        """Analyze an activity and return metrics."""
        ...


class ActivityAnalyzer:
    """
    Analyzes individual activities to compute metrics.

    This class coordinates metric calculation and handles activity-specific logic.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the analyzer.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.metrics_calculator = MetricsCalculator(settings)
        self.logger = logging.getLogger(__name__)

    def analyze(
        self, activity_row: pd.Series, stream_df: pd.DataFrame
    ) -> dict[str, float]:
        """
        Analyze a single activity and compute all metrics.

        Args:
            activity_row: Series containing activity metadata
            stream_df: DataFrame containing activity stream data

        Returns:
            Dictionary of calculated metrics

        Raises:
            ActivityTypeError: If activity type is not supported
            ProcessingError: If there's an error during analysis
        """
        try:
            activity_type = ActivityType(activity_row["type"])

            # Validate supported activity types
            if activity_type not in [
                ActivityType.RIDE,
                ActivityType.VIRTUAL_RIDE,
                ActivityType.RUN,
            ]:
                raise ActivityTypeError(f"Unsupported activity type: {activity_type}")

            # Calculate metrics using the metrics calculator
            metrics = self.metrics_calculator.compute_all_metrics(
                stream_df, activity_type.value.lower()
            )

            # Convert numpy types to Python native types for serialization
            metrics = self._convert_numpy_types(metrics)

            self.logger.debug(
                f"Analyzed activity {activity_row['id']} ({activity_type.value})"
            )

            return metrics

        except ActivityTypeError:
            raise
        except Exception as e:
            raise ProcessingError(
                f"Error analyzing activity {activity_row['id']}: {e}"
            ) from e

    def _convert_numpy_types(self, metrics: dict) -> dict:
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
