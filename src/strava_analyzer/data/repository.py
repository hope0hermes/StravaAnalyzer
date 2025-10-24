"""
Repository pattern for activity data access.

This module provides a high-level interface for querying and managing activities.
"""

import logging
from typing import Protocol

import pandas as pd

from ..models import ActivityType
from ..settings import Settings
from .loader import ActivityDataLoader

logger = logging.getLogger(__name__)


class RepositoryProtocol(Protocol):
    """Protocol for repositories."""

    def get_all_activities(self) -> pd.DataFrame:
        """Get all activities."""
        ...

    def get_activities_by_type(self, activity_type: ActivityType) -> pd.DataFrame:
        """Get activities of a specific type."""
        ...


class ActivityRepository:
    """
    Repository for activity data access.

    Provides high-level queries and business logic for activity data,
    abstracting away the underlying data loading and filtering logic.
    """

    def __init__(self, loader: ActivityDataLoader, settings: Settings):
        """
        Initialize the repository.

        Args:
            loader: Data loader instance
            settings: Application settings
        """
        self.loader = loader
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self._activities_cache: pd.DataFrame | None = None

    def get_all_activities(self) -> pd.DataFrame:
        """
        Get all activities.

        Returns:
            DataFrame of all activities
        """
        if self._activities_cache is None:
            self._activities_cache = self.loader.load_activities()
        return self._activities_cache.copy()

    def get_activities_by_type(self, activity_type: ActivityType) -> pd.DataFrame:
        """
        Get activities of a specific type.

        Args:
            activity_type: Type of activity to filter

        Returns:
            DataFrame of filtered activities
        """
        activities = self.get_all_activities()
        return activities[activities["type"] == activity_type.value].copy()

    def get_supported_activities(self) -> pd.DataFrame:
        """
        Get all supported activities (Ride, VirtualRide, Run).

        Returns:
            DataFrame of supported activities
        """
        activities = self.get_all_activities()
        supported_types = {
            ActivityType.RIDE.value,
            ActivityType.VIRTUAL_RIDE.value,
            ActivityType.RUN.value,
        }
        return activities[activities["type"].isin(supported_types)].copy()

    def get_activities_needing_processing(
        self, enriched_activities: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """
        Get activities that need processing.

        Args:
            enriched_activities: Previously enriched activities (optional)

        Returns:
            DataFrame of activities to process
        """
        supported = self.get_supported_activities()

        if enriched_activities is None:
            enriched_activities = self.loader.load_enriched_activities()

        if enriched_activities is None:
            return supported

        # Find activities not yet processed
        processed_ids = set(enriched_activities["id"].astype(str))
        to_process = supported[~supported["id"].astype(str).isin(processed_ids)]

        self.logger.info(f"Found {len(to_process)} activities needing processing")
        return to_process

    def get_activity_by_id(self, activity_id: int | str) -> pd.Series | None:
        """
        Get a specific activity by ID.

        Args:
            activity_id: ID of the activity

        Returns:
            Series containing activity data or None if not found
        """
        activities = self.get_all_activities()
        matches = activities[activities["id"] == int(activity_id)]
        return matches.iloc[0] if not matches.empty else None

    def get_recent_activities(self, n: int = 10) -> pd.DataFrame:
        """
        Get the N most recent activities.

        Args:
            n: Number of activities to retrieve

        Returns:
            DataFrame of recent activities
        """
        activities = self.get_all_activities()
        return activities.sort_values("start_date", ascending=False).head(n)

    def invalidate_cache(self) -> None:
        """Clear the activities cache, forcing reload on next access."""
        self._activities_cache = None
        self.logger.debug("Activities cache invalidated")
