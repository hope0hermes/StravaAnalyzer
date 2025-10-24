"""
Threshold estimation service.

This module provides FTP and FTHR estimation from activity data.
"""

import logging
from datetime import timedelta
from typing import Protocol

import pandas as pd

from ..constants import ThresholdFactors, TrainingLoadWindows
from ..exceptions import CalculationError, InvalidDataError
from ..models import ActivityStream
from ..settings import Settings

logger = logging.getLogger(__name__)


class ThresholdEstimatorProtocol(Protocol):
    """Protocol for threshold estimators."""

    def estimate(
        self, enriched_df: pd.DataFrame, historical_df: pd.DataFrame | None
    ) -> dict[str, float]:
        """Estimate current thresholds."""
        ...


class ThresholdEstimator:
    """
    Service for estimating FTP and FTHR thresholds.

    Provides methods for estimating thresholds from single activities
    or from historical data using rolling windows.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the threshold estimator service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def find_max_rolling_average(
        self, series: pd.Series, window_size: int
    ) -> float | None:
        """
        Find the maximum rolling average for a given series and window size.

        Args:
            series: Time series data
            window_size: Window size in seconds

        Returns:
            Maximum rolling average value, or None if series is too short
        """
        window_size = int(window_size)
        if window_size <= 0 or len(series) < window_size:
            return None
        return series.rolling(window=window_size, min_periods=window_size).mean().max()

    def estimate_from_activity(
        self,
        stream: ActivityStream,
        activity_date: pd.Timestamp,
        estimation_factor: float = ThresholdFactors.FTP_FROM_20MIN,
    ) -> dict[str, float | pd.Timestamp]:
        """
        Estimate FTP and FTHR from a single activity's stream data.

        The function looks for the highest 20-minute mean maximal power and derives
        FTP from it. FTHR is calculated as the average heart rate during that same
        20-minute effort.

        Args:
            stream: Activity stream containing power and heart rate data
            activity_date: Timestamp of the activity
            estimation_factor: Factor to multiply 20-min power by (default 0.95)

        Returns:
            Dictionary containing date, FTP, and FTHR estimates

        Raises:
            InvalidDataError: If required data is missing
            CalculationError: If calculation fails
        """
        try:
            if "watts" not in stream.columns or "heartrate" not in stream.columns:
                raise InvalidDataError(
                    "Both power and heart rate data required for FTP/FTHR estimation"
                )

            # Only consider positive power values for FTP estimation
            active_power_data = stream[stream["watts"] > 0]["watts"]
            active_hr_data = stream[stream["watts"] > 0]["heartrate"]

            if len(active_power_data) < 1200:  # 20 minutes
                raise InvalidDataError(
                    "Activity too short for FTP/FTHR estimation. "
                    "Need at least 20 minutes of active power data."
                )

            # Find the 20-minute MMP
            rolling_20min_avg_power = active_power_data.rolling(
                window=1200, min_periods=1200
            ).mean()
            max_20min_power = rolling_20min_avg_power.max()

            if pd.isna(max_20min_power):
                raise CalculationError("Failed to calculate 20-minute maximal power")

            # Calculate FTP estimate
            ftp_estimate = max_20min_power * estimation_factor

            # Find the start index of the 20-minute maximal effort
            max_20min_power_idx = rolling_20min_avg_power.idxmax()
            start_idx = max_20min_power_idx - 1200 + 1

            # Get the heart rate during that 20-minute window
            hr_during_ftp_effort = active_hr_data.loc[start_idx:max_20min_power_idx]
            fthr_estimate = hr_during_ftp_effort.mean()

            if pd.isna(fthr_estimate):
                raise CalculationError("Failed to calculate FTHR from effort period")

            return {
                "date": activity_date,
                "ftp": round(ftp_estimate),
                "fthr": round(fthr_estimate),
            }
        except Exception as e:
            raise CalculationError(f"Failed to estimate FTP/FTHR: {str(e)}") from e

    def get_rolling_thresholds(
        self,
        historical_thresholds: pd.DataFrame,
        activity_date: pd.Timestamp,
        window_days: int = TrainingLoadWindows.FTP_ROLLING_WINDOW_DAYS,
    ) -> dict[str, float | None]:
        """
        Retrieve the most relevant FTP and FTHR for a given activity date.

        Uses a rolling window to find the highest FTP (and corresponding FTHR)
        within a specified number of days before the activity date.

        Args:
            historical_thresholds: DataFrame containing historical threshold estimates
            activity_date: Date to get thresholds for
            window_days: Number of days to look back (default 42)

        Returns:
            Dictionary containing FTP and FTHR values, or None if no data available

        Raises:
            ValueError: If inputs are invalid
        """
        try:
            if historical_thresholds.empty:
                return {"ftp": None, "fthr": None}

            required_cols = {"date", "ftp", "fthr"}
            if not required_cols.issubset(historical_thresholds.columns):
                raise ValueError(
                    f"Missing required columns. Need: {', '.join(required_cols)}"
                )

            # Ensure 'date' is datetime and sorted
            df = historical_thresholds.copy()
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            # Filter thresholds within the rolling window before the activity date
            window_start = activity_date - timedelta(days=window_days)
            relevant_thresholds = df[
                (df["date"] >= window_start) & (df["date"] <= activity_date)
            ].copy()

            if relevant_thresholds.empty:
                return {"ftp": None, "fthr": None}

            # Find the most recent highest FTP within the window
            best_ftp_row = relevant_thresholds.sort_values(
                ["ftp", "date"], ascending=[False, False]
            ).iloc[0]

            return {
                "ftp": round(float(best_ftp_row["ftp"])),
                "fthr": round(float(best_ftp_row["fthr"])),
            }
        except Exception as e:
            raise ValueError(f"Error processing threshold data: {str(e)}") from e

    def estimate(
        self, enriched_df: pd.DataFrame, historical_df: pd.DataFrame | None = None
    ) -> dict[str, float]:
        """
        Estimate current FTP and FTHR from activity data.

        Args:
            enriched_df: DataFrame of enriched activities
            historical_df: Optional historical threshold data

        Returns:
            Dictionary with 'ftp' and 'fthr' keys
        """
        try:
            self.logger.info("Estimating thresholds from activity data")

            # For now, use the simple approach: get from the most recent activity
            # In future, could implement more sophisticated estimation
            if historical_df is not None and not historical_df.empty:
                latest_date = enriched_df["start_date"].max()
                thresholds = self.get_rolling_thresholds(
                    historical_df, latest_date, self.settings.ftp_rolling_window_days
                )

                if thresholds["ftp"] is not None:
                    return {
                        "ftp": thresholds["ftp"],
                        "fthr": thresholds["fthr"] or self.settings.fthr,
                    }

            # Fall back to settings defaults
            return {
                "ftp": self.settings.ftp,
                "fthr": self.settings.fthr,
            }

        except Exception as e:
            self.logger.warning(f"Threshold estimation failed: {e}. Using defaults.")
            return {
                "ftp": self.settings.ftp,
                "fthr": self.settings.fthr,
            }

    def get_default_thresholds(self) -> dict[str, float]:
        """
        Get default thresholds from settings.

        Returns:
            Dictionary with 'ftp' and 'fthr' keys
        """
        return {
            "ftp": self.settings.ftp,
            "fthr": self.settings.fthr,
        }
