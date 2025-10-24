"""
High-level service for activity processing.

This service coordinates data loading, processing, analysis, and storage
for activity data.
"""

import logging
from typing import Protocol

import pandas as pd

from ..analysis import ActivityAnalyzer
from ..data import ActivityDataLoader, ActivityRepository, StreamDataProcessor
from ..exceptions import DataLoadError, ProcessingError, StreamDataError
from ..settings import Settings

logger = logging.getLogger(__name__)


class ActivityServiceProtocol(Protocol):
    """Protocol for activity services."""

    def process_activity(
        self, activity_row: pd.Series
    ) -> tuple[dict[str, float], pd.DataFrame]:
        """Process a single activity."""
        ...


class ActivityService:
    """
    High-level service for activity data operations.

    This service coordinates multiple components to provide complete
    activity processing workflows.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the activity service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.loader = ActivityDataLoader(settings)
        self.processor = StreamDataProcessor(settings)
        self.repository = ActivityRepository(self.loader, settings)
        self.analyzer = ActivityAnalyzer(settings)

    def process_activity(
        self, activity_row: pd.Series
    ) -> tuple[dict[str, float], pd.DataFrame]:
        """
        Process a single activity through the complete pipeline.

        This method:
        1. Loads stream data
        2. Processes and cleans it
        3. Analyzes and computes metrics
        4. Returns both metrics and processed stream

        Args:
            activity_row: Series containing activity metadata

        Returns:
            Tuple of (metrics dict, processed stream DataFrame)

        Raises:
            DataLoadError: If data loading fails
            StreamDataError: If stream processing fails
            ProcessingError: If analysis fails
        """
        activity_id = activity_row["id"]

        try:
            # Load stream data
            self.logger.debug(f"Loading stream for activity {activity_id}")
            raw_stream = self.loader.load_stream(activity_id)

            if raw_stream.empty:
                raise StreamDataError(f"Empty stream data for activity {activity_id}")

            # Process stream data
            self.logger.debug(f"Processing stream for activity {activity_id}")
            processed_stream = self.processor.process(raw_stream)

            # Analyze activity
            self.logger.debug(f"Analyzing activity {activity_id}")
            metrics = self.analyzer.analyze(activity_row, processed_stream)

            return metrics, processed_stream

        except DataLoadError:
            raise
        except Exception as e:
            raise ProcessingError(
                f"Failed to process activity {activity_id}: {e}"
            ) from e

    def get_activities_to_process(self) -> pd.DataFrame:
        """
        Get activities that need processing.

        Returns:
            DataFrame of activities to process
        """
        return self.repository.get_activities_needing_processing()

    def activity_has_stream(self, activity_id: int | str) -> bool:
        """
        Check if stream data exists for an activity.

        Args:
            activity_id: ID of the activity

        Returns:
            True if stream exists, False otherwise
        """
        return self.loader.stream_exists(activity_id)

    def get_activity(self, activity_id: int | str) -> pd.Series | None:
        """
        Get activity metadata by ID.

        Args:
            activity_id: ID of the activity

        Returns:
            Series with activity data or None if not found
        """
        return self.repository.get_activity_by_id(activity_id)

    def get_recent_activities(self, n: int = 10) -> pd.DataFrame:
        """
        Get the N most recent activities.

        Args:
            n: Number of activities to retrieve

        Returns:
            DataFrame of recent activities
        """
        return self.repository.get_recent_activities(n)
