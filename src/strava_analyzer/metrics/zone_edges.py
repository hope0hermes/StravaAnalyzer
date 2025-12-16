"""
Zone edges management with backpropagation logic.

This module handles tracking and backpropagating zone edges
(power and heart rate zone boundaries) across activities based on
configuration change timestamps.
"""

import logging
from datetime import datetime

import pandas as pd

from ..settings import Settings

logger = logging.getLogger(__name__)


class ZoneEdgesManager:
    """Manages zone edges and backpropagation logic."""

    def __init__(self, settings: Settings):
        """
        Initialize the zone edges manager.

        Args:
            settings: Application settings containing zone configuration
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def extract_zone_right_edges(
        self, zones: dict[str, tuple[float, float]]
    ) -> list[float]:
        """
        Extract only the right edges from zone definitions.

        Args:
            zones: Dictionary of zones with (left, right) edges

        Returns:
            List of right edges sorted in ascending order
        """
        right_edges = []
        for zone_name, (left, right) in zones.items():
            # Skip infinity (last zone upper bound)
            if right != float("inf"):
                right_edges.append(right)

        return sorted(right_edges)

    def get_zone_column_names(self) -> dict[str, list[str]]:
        """
        Get the list of zone column names that will be created.

        Returns:
            Dictionary with 'power_zone_cols' and 'hr_zone_cols' lists
        """
        # Use the methods from settings which compute zones dynamically based on FTP/FTHR
        power_edges = self.settings.get_power_zone_edges()
        hr_edges = self.settings.get_hr_zone_edges()

        # Enumerate starting from 1
        power_cols = [f"power_zone_{i+1}" for i in range(len(power_edges))]
        hr_cols = [f"hr_zone_{i+1}" for i in range(len(hr_edges))]

        return {"power_zone_cols": power_cols, "hr_zone_cols": hr_cols}

    def get_current_zone_edges(self) -> dict[str, list[float]]:
        """
        Get current zone edges based on active settings.

        Returns:
            Dictionary with 'power_edges' and 'hr_edges' lists of right edges
        """
        return {
            "power_edges": self.settings.get_power_zone_edges(),
            "hr_edges": self.settings.get_hr_zone_edges(),
        }

    def apply_zone_edges_with_backpropagation(
        self, enriched_df: pd.DataFrame, config_timestamp: datetime | None = None
    ) -> pd.DataFrame:
        """
        Apply zone edges to activities with backpropagation logic.

        This function:
        1. Ensures dataframe is sorted by start_date_local descending
        2. Finds the closest activity to the configuration timestamp
        3. Sets zone edge columns on that activity
        4. Backpropagates zone edge columns to older activities (earlier dates)

        Creates individual columns for each zone boundary (right edges only):
        - power_zone_1, power_zone_2, etc.
        - hr_zone_1, hr_zone_2, etc.

        Args:
            enriched_df: Enriched activities DataFrame
            config_timestamp: Timestamp when zones were configured.
                            If None, uses current time.

        Returns:
            Updated DataFrame with zone edge columns applied
        """
        if enriched_df.empty:
            return enriched_df

        df = enriched_df.copy()

        # Ensure start_date_local column exists and is datetime
        if "start_date_local" not in df.columns:
            self.logger.warning(
                "No start_date_local column found. Skipping zone edges application."
            )
            return df

        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(df["start_date_local"]):
            df["start_date_local"] = pd.to_datetime(df["start_date_local"], format='ISO8601', utc=True)

        # Sort by start_date_local in descending order (most recent first)
        df = df.sort_values("start_date_local", ascending=False).reset_index(drop=True)

        # Get zone column names and create them if they don't exist
        zone_cols = self.get_zone_column_names()
        for col in zone_cols["power_zone_cols"] + zone_cols["hr_zone_cols"]:
            if col not in df.columns:
                df[col] = None

        # Check if all zone edge columns are already filled
        all_cols = zone_cols["power_zone_cols"] + zone_cols["hr_zone_cols"]
        if all(df[col].notna().all() for col in all_cols):
            self.logger.debug("All activities already have zone edges set")
            return df

        # Use current time if no config timestamp provided
        if config_timestamp is None:
            config_timestamp = datetime.now()

        # Handle timezone awareness mismatch
        start_date_tz = df["start_date_local"].dt.tz
        if start_date_tz is not None and config_timestamp.tzinfo is None:
            # start_date_local is tz-aware, make config_timestamp tz-aware (UTC)
            config_timestamp = pd.Timestamp(config_timestamp, tz="UTC").to_pydatetime()
        elif start_date_tz is None and config_timestamp.tzinfo is not None:
            # start_date_local is tz-naive, make config_timestamp tz-naive
            config_timestamp = config_timestamp.replace(tzinfo=None)

        # Get current zone edges from settings
        current_edges = self.get_current_zone_edges()
        power_edges = current_edges["power_edges"]
        hr_edges = current_edges["hr_edges"]

        # Find closest activity by date to config timestamp
        df["date_diff"] = (df["start_date_local"] - config_timestamp).abs()
        closest_idx = df["date_diff"].idxmin()
        closest_date = df.loc[closest_idx, "start_date_local"]

        self.logger.debug(
            f"Config timestamp: {config_timestamp}, "
            f"Closest activity: {closest_date} at index {closest_idx}"
        )

        # Set zone edge columns on the closest activity
        for i, power_edge in enumerate(power_edges):
            df.at[closest_idx, zone_cols["power_zone_cols"][i]] = float(power_edge)

        for i, hr_edge in enumerate(hr_edges):
            df.at[closest_idx, zone_cols["hr_zone_cols"][i]] = float(hr_edge)

        # Backpropagate to older activities (lower indices after sorting desc)
        # In descending date order, older activities are at higher indices
        for i in range(closest_idx + 1, len(df)):
            # Only fill if not already set
            for col_idx, col in enumerate(zone_cols["power_zone_cols"]):
                if pd.isna(df.at[i, col]):
                    df.at[i, col] = float(power_edges[col_idx])

            for col_idx, col in enumerate(zone_cols["hr_zone_cols"]):
                if pd.isna(df.at[i, col]):
                    df.at[i, col] = float(hr_edges[col_idx])

        self.logger.info(
            f"Applied {len(power_edges)} power zone edges and {len(hr_edges)} HR zone edges "
            f"to {len(df)} activities. "
            f"Closest activity at index {closest_idx}. "
            f"Backpropagated to {len(df) - closest_idx - 1} older activities."
        )

        # Drop temporary date_diff column
        df = df.drop(columns=["date_diff"])

        return df
