"""
Data loading functionality.

This module provides a clean interface for loading activity and stream data.
"""

import logging
from typing import Protocol

import pandas as pd

from ..constants import CSVConstants
from ..exceptions import DataLoadError
from ..settings import Settings

logger = logging.getLogger(__name__)


class DataLoaderProtocol(Protocol):
    """Protocol for data loaders."""

    def load_activities(self) -> pd.DataFrame:
        """Load activities DataFrame."""
        ...

    def load_stream(self, activity_id: int | str) -> pd.DataFrame:
        """Load stream data for a specific activity."""
        ...


class ActivityDataLoader:
    """
    Handles loading of activity and stream data from files.

    This class encapsulates all file I/O operations for activity data,
    providing a clean interface for the rest of the application.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the data loader.

        Args:
            settings: Application settings containing data paths
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def load_activities(self) -> pd.DataFrame:
        """
        Load activities from CSV file.

        Returns:
            DataFrame containing activity metadata

        Raises:
            DataLoadError: If loading fails
        """
        try:
            activities_file = self.settings.activities_file
            if not activities_file.exists():
                raise DataLoadError(f"Activities file not found: {activities_file}")

            self.logger.info(f"Loading activities from {activities_file}")
            df = pd.read_csv(
                activities_file,
                parse_dates=["start_date"],
                sep=CSVConstants.DEFAULT_SEPARATOR,
            )
            self.logger.info(f"Loaded {len(df)} activities")
            return df

        except Exception as e:
            raise DataLoadError(f"Failed to load activities: {e}") from e

    def load_stream(self, activity_id: int | str) -> pd.DataFrame:
        """
        Load stream data for a specific activity.

        Args:
            activity_id: ID of the activity

        Returns:
            DataFrame containing stream data

        Raises:
            DataLoadError: If loading fails
        """
        try:
            stream_file = self.settings.streams_dir / f"stream_{activity_id}.csv"

            if not stream_file.exists():
                raise DataLoadError(f"Stream file not found: {stream_file}")

            self.logger.debug(f"Loading stream data from {stream_file}")
            df = pd.read_csv(stream_file, sep=CSVConstants.DEFAULT_SEPARATOR)
            return df

        except Exception as e:
            raise DataLoadError(
                f"Failed to load stream for activity {activity_id}: {e}"
            ) from e

    def load_enriched_activities(self) -> pd.DataFrame | None:
        """
        Load previously enriched activities if available.

        Returns:
            DataFrame of enriched activities or None if not found
        """
        try:
            enriched_file = self.settings.activities_enriched_file
            if enriched_file is not None:
                if not enriched_file.exists():
                    self.logger.info("No existing enriched activities file found")
                    return None

            self.logger.info(f"Loading enriched activities from {enriched_file}")
            df = pd.read_csv(
                enriched_file,
                parse_dates=["start_date"],
                sep=CSVConstants.DEFAULT_SEPARATOR,
            )
            self.logger.info(f"Loaded {len(df)} enriched activities")
            return df

        except Exception as e:
            self.logger.warning(f"Failed to load enriched activities: {e}")
            return None

    def load_historical_thresholds(self) -> pd.DataFrame | None:
        """
        Load historical FTP/FTHR thresholds if available.

        Returns:
            DataFrame of historical thresholds or None if not found
        """
        try:
            threshold_file = (
                self.settings.processed_data_dir / "historical_thresholds.csv"
            )
            if not threshold_file.exists():
                self.logger.info("No historical thresholds file found")
                return None

            self.logger.info(f"Loading historical thresholds from {threshold_file}")
            df = pd.read_csv(
                threshold_file, parse_dates=["date"], sep=CSVConstants.DEFAULT_SEPARATOR
            )
            return df

        except Exception as e:
            self.logger.warning(f"Failed to load historical thresholds: {e}")
            return None

    def stream_exists(self, activity_id: int | str) -> bool:
        """
        Check if stream data exists for an activity.

        Args:
            activity_id: ID of the activity

        Returns:
            True if stream file exists, False otherwise
        """
        stream_file = self.settings.streams_dir / f"stream_{activity_id}.csv"
        return stream_file.exists()
