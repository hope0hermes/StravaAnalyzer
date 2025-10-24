"""
Stream data processing and cleaning.

This module handles all data cleaning, validation, and preprocessing operations.
"""

import logging
from ast import literal_eval
from typing import Protocol

import numpy as np
import pandas as pd

from ..constants import TimeConstants
from ..exceptions import ValidationError
from ..settings import Settings

logger = logging.getLogger(__name__)


class DataProcessorProtocol(Protocol):
    """Protocol for data processors."""

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean data."""
        ...


class StreamDataProcessor:
    """
    Processes and cleans activity stream data.

    Handles validation, type conversion, missing data, and GPS processing.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the processor.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process stream data through the complete cleaning pipeline.

        Args:
            df: Raw stream DataFrame

        Returns:
            Cleaned and processed DataFrame

        Raises:
            ValidationError: If essential data is missing or invalid
        """
        # Create a copy to avoid modifying the original
        processed_df = df.copy()

        # Validate essential columns
        self._validate_essential_columns(processed_df)

        # Log warnings for optional columns
        self._check_optional_columns(processed_df)

        # Process each data type
        processed_df = self._process_temporal_data(processed_df)
        processed_df = self._process_physiological_data(processed_df)
        processed_df = self._process_power_data(processed_df)
        processed_df = self._process_motion_data(processed_df)
        processed_df = self._process_gps_data(processed_df)
        processed_df = self._infer_moving_state(processed_df)

        return processed_df

    def _validate_essential_columns(self, df: pd.DataFrame) -> None:
        """Validate that essential columns exist."""
        missing = [
            col
            for col in self.settings.stream_essential_columns
            if col not in df.columns
        ]
        if missing:
            raise ValidationError(f"Missing essential columns: {missing}")

    def _check_optional_columns(self, df: pd.DataFrame) -> None:
        """Log warnings for missing optional columns."""
        for metric, columns in self.settings.stream_optional_columns.items():
            missing = [col for col in columns if col not in df.columns]
            if missing:
                self.logger.warning(
                    f"Optional columns for {metric} metrics missing: {missing}. "
                    f"Related calculations will be skipped."
                )

    def _process_temporal_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process time-related columns."""
        if "time" in df.columns:
            df["time"] = pd.to_numeric(df["time"], errors="coerce")
            df["time"] = df["time"].ffill().bfill().fillna(0)
        return df

    def _process_physiological_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process heart rate data with forward/backward fill."""
        if "heartrate" in df.columns:
            df["heartrate"] = pd.to_numeric(df["heartrate"], errors="coerce")
            df["heartrate"] = df["heartrate"].ffill().bfill().fillna(0)
        return df

    def _process_power_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process power and cadence data with zero-fill."""
        for col in ["watts", "cadence"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].fillna(0)
        return df

    def _process_motion_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process velocity, grade, distance, and altitude with fwd/bwd fills."""
        motion_cols = ["velocity_smooth", "grade_smooth", "distance", "altitude"]
        for col in motion_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].ffill().bfill().fillna(0)
        return df

    def _process_gps_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process GPS coordinates from latlng column."""
        if "latlng" not in df.columns:
            return df

        try:
            # Parse string representations if needed
            if df["latlng"].apply(lambda x: isinstance(x, str)).any():
                df["latlng"] = df["latlng"].apply(literal_eval)

            # Extract lat/lng if data exists
            if not df["latlng"].isna().all():
                latlan = np.asarray(df["latlng"].to_list())
                df["lat"] = latlan[:, 0]
                df["lng"] = latlan[:, 1]
                df.drop(columns=["latlng"], inplace=True)
            else:
                self.logger.warning("No GPS data found in 'latlng' column")
                df["lat"] = np.nan
                df["lng"] = np.nan

        except (ValueError, SyntaxError, IndexError) as e:
            self.logger.warning(
                f"Error processing GPS data: {e}. Skipping lat/lng extraction."
            )
            df["lat"] = np.nan
            df["lng"] = np.nan

        return df

    def _infer_moving_state(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Determine moving state from available data.

        Detects idle periods by identifying large time gaps (>GAP_DETECTION_THRESHOLD).
        These gaps indicate auto-pause or manual stops where no data was recorded.

        The row immediately after a gap is marked as stopped since it represents
        the boundary point where recording resumed (typically with 0W/0 velocity).
        """
        # Start with all points assumed to be moving
        if "moving" not in df.columns:
            df["moving"] = True

        # Detect stopped periods from time gaps
        if "time" in df.columns and len(df) > 1:
            # Calculate time deltas between consecutive points
            time_diffs = df["time"].diff()

            # Mark points after large gaps as stopped
            # These represent the moment when recording resumed after a pause
            # The threshold catches most auto-pause events while allowing
            # for minor recording variations (normal 1Hz sampling)
            large_gaps = time_diffs > TimeConstants.GAP_DETECTION_THRESHOLD

            # Mark these points as not moving
            df.loc[large_gaps, "moving"] = False

            # Log detection results
            num_stopped = large_gaps.sum()
            if num_stopped > 0:
                total_stopped_time = time_diffs[large_gaps].sum()
                self.logger.debug(
                    f"Detected {num_stopped} stopped periods "
                    f"(total {total_stopped_time:.0f}s from time gaps)"
                )
        elif "velocity_smooth" in df.columns:
            # Fallback: infer from velocity if no time data
            df["moving"] = df["velocity_smooth"] > 0.5  # >0.5 m/s = 1.8 km/h
            self.logger.info("Inferred moving state from velocity data")
        else:
            self.logger.warning(
                "No time or velocity data available. Assuming all points are moving."
            )

        return df
