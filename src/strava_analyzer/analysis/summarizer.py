"""
Activity summary and aggregation.

This module provides comprehensive activity summarization and longitudinal analysis.
"""

import logging
from datetime import datetime
from typing import Protocol

import pandas as pd

from ..constants import TrainingLoadWindows
from ..models import ActivityType, LongitudinalSummary, TrainingLoadSummary
from ..settings import Settings

logger = logging.getLogger(__name__)


class SummarizerProtocol(Protocol):
    """Protocol for summarizers."""

    def summarize(self, enriched_df: pd.DataFrame) -> LongitudinalSummary:
        """Create summary from enriched activities."""
        ...


class ActivitySummarizer:
    """
    Service for creating activity summaries and aggregations.

    Generates comprehensive summaries including training load metrics,
    performance trends, and zone distributions.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the summarizer service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def _calculate_training_load(
        self, activities_df: pd.DataFrame, as_of_date: datetime | None = None
    ) -> TrainingLoadSummary:
        """Calculate training load metrics up to a specific date."""
        if as_of_date is None:
            as_of_date = pd.Timestamp.now()

        # Ensure start_date is datetime for comparison
        df = activities_df.copy()
        if "start_date" not in df.columns and "start_date_local" in df.columns:
            df["start_date"] = pd.to_datetime(df["start_date_local"])
        elif "start_date" in df.columns:
            df["start_date"] = pd.to_datetime(df["start_date"])

        # Filter activities up to as_of_date
        mask = df["start_date"] <= as_of_date
        df = df[mask].copy()

        # Use moving TSS if available, otherwise fall back to raw TSS
        tss_column = (
            "moving_training_stress_score"
            if "moving_training_stress_score" in df.columns
            else "raw_training_stress_score"
        )
        if tss_column not in df.columns or df[tss_column].isna().all():
            return TrainingLoadSummary(
                chronic_training_load=0.0,
                acute_training_load=0.0,
                training_stress_balance=0.0,
                acwr=0.0,
            )

        # Sort by date ASCENDING (oldest first) for proper EWM calculation
        df = df.sort_values("start_date", ascending=True).reset_index(drop=True)
        
        # Fill NaN TSS values with 0 for EWM calculation
        df[tss_column] = df[tss_column].fillna(0)

        # Calculate CTL (chronic training load - 42-day exponential average)
        df["ctl_score"] = df[tss_column].ewm(span=TrainingLoadWindows.CTL_DAYS, adjust=False).mean()

        # Calculate ATL (acute training load - 7-day exponential average)
        df["atl_score"] = df[tss_column].ewm(span=TrainingLoadWindows.ATL_DAYS, adjust=False).mean()

        # Get most recent values (last row after ascending sort)
        if len(df) > 0:
            latest = df.iloc[-1]
            ctl = float(latest["ctl_score"])
            atl = float(latest["atl_score"])
            tsb = ctl - atl
            acwr = atl / ctl if ctl > 0 else 0.0
        else:
            ctl = atl = tsb = acwr = 0.0

        return TrainingLoadSummary(
            chronic_training_load=ctl,
            acute_training_load=atl,
            training_stress_balance=tsb,
            acwr=acwr,
        )

    def _calculate_performance_trends(
        self, activities_df: pd.DataFrame, rolling_window: str = "28D"
    ) -> dict[str, float]:
        """Calculate performance trends for key metrics."""
        trends = {}

        metrics = [
            "normalized_power",
            "average_power",
            "training_stress_score",
            "intensity_factor",
            "efficiency_factor",
        ]

        for metric in metrics:
            if metric in activities_df.columns:
                rolling_avg = (
                    activities_df.set_index("start_date")[metric]
                    .rolling(rolling_window)
                    .mean()
                )
                if not rolling_avg.empty and len(rolling_avg) > 1:
                    start_val = rolling_avg.iloc[0]
                    end_val = rolling_avg.iloc[-1]
                    if start_val != 0:
                        trend = ((end_val - start_val) / start_val) * 100
                        trends[f"{metric}_trend"] = trend

        return trends

    def calculate_rolling_ef(
        self, activities_df: pd.DataFrame, window_days: int = 28
    ) -> dict[str, float]:
        """
        Calculate rolling average Efficiency Factor.

        Args:
            activities_df: DataFrame with activity metrics
            window_days: Rolling window size in days

        Returns:
            Dictionary with rolling EF metrics
        """
        ef_metrics = {}

        # Check for both raw and moving EF
        for prefix in ["raw_", "moving_"]:
            ef_col = f"{prefix}efficiency_factor"
            if ef_col not in activities_df.columns:
                continue

            # Filter out invalid EF values (NaN, inf, negative)
            valid_ef = activities_df[
                activities_df[ef_col].notna()
                & (activities_df[ef_col] > 0)
                & (activities_df[ef_col] < 10)  # Remove outliers
            ].copy()

            if len(valid_ef) == 0:
                continue

            # Calculate rolling averages
            df_sorted = valid_ef.sort_values("start_date").set_index("start_date")

            # 4-week (28-day) rolling average
            ef_4week = df_sorted[ef_col].rolling(f"{window_days}D").mean()
            if not ef_4week.empty:
                ef_metrics[f"{prefix}ef_4week_avg"] = ef_4week.iloc[-1]

            # 52-week (364-day) rolling average
            ef_52week = df_sorted[ef_col].rolling("364D").mean()
            if not ef_52week.empty:
                ef_metrics[f"{prefix}ef_52week_avg"] = ef_52week.iloc[-1]

            # Overall average for comparison
            ef_metrics[f"{prefix}ef_overall_avg"] = df_sorted[ef_col].mean()

        return ef_metrics

    def _calculate_zone_distributions(
        self, activities_df: pd.DataFrame, activity_type: ActivityType | None = None
    ) -> dict[str, dict[str, float]]:
        """Calculate time distribution across different training zones."""
        zone_distributions = {}

        # Filter by activity type if specified
        if activity_type:
            df = activities_df[activities_df["type"] == activity_type.value]
        else:
            df = activities_df

        # Calculate distributions for power, heart rate, and pace zones
        zone_types = [
            ("power", "power_zone_"),
            ("heart_rate", "hr_zone_"),
            ("pace", "pace_zone_"),
        ]

        for zone_type, prefix in zone_types:
            zone_cols = [col for col in df.columns if col.startswith(prefix)]
            if zone_cols:
                zone_data = {}
                for zone_col in zone_cols:
                    zone_data[zone_col] = df[zone_col].mean() if not df.empty else 0.0
                zone_distributions[zone_type] = zone_data

        return zone_distributions

    def summarize(self, enriched_df: pd.DataFrame) -> LongitudinalSummary:
        """
        Create a longitudinal summary from enriched activities.

        Args:
            enriched_df: DataFrame of enriched activities with metrics

        Returns:
            LongitudinalSummary object

        Raises:
            Exception: If summary creation fails
        """
        try:
            self.logger.info(f"Creating summary from {len(enriched_df)} activities")
            summary = self.generate_summary(enriched_df)
            self.logger.info("Summary created successfully")
            return summary

        except Exception as e:
            self.logger.error(f"Failed to create summary: {e}")
            raise

    def generate_summary(
        self,
        activities_df: pd.DataFrame,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        activity_type: ActivityType | None = None,
    ) -> LongitudinalSummary:
        """
        Generate comprehensive activity summary.

        Args:
            activities_df: DataFrame of enriched activities
            start_date: Optional start date filter
            end_date: Optional end date filter
            activity_type: Optional activity type filter

        Returns:
            LongitudinalSummary with all metrics
        """
        # Apply date filters if provided
        df = activities_df.copy()
        if start_date:
            df = df[df["start_date"] >= start_date]
        if end_date:
            df = df[df["start_date"] <= end_date]

        # Apply activity type filter if provided
        if activity_type:
            df = df[df["type"] == activity_type.value]

        # Calculate period metrics
        period_start = (
            df["start_date"].min() if not df.empty else start_date or pd.Timestamp.now()
        )
        period_end = (
            df["start_date"].max() if not df.empty else end_date or pd.Timestamp.now()
        )

        # Basic totals
        total_activities = len(df)
        total_distance = df["distance"].sum() if "distance" in df.columns else 0
        total_elevation = (
            df["total_elevation_gain"].sum()
            if "total_elevation_gain" in df.columns
            else 0
        )
        total_time = df["moving_time"].sum() if "moving_time" in df.columns else 0

        # Calculate training load
        training_load = self._calculate_training_load(df, period_end)

        # Calculate performance trends
        performance_trends = self._calculate_performance_trends(df)

        # Calculate zone distributions
        zone_distributions = self._calculate_zone_distributions(df, activity_type)

        # Calculate rolling EF averages
        rolling_ef = self.calculate_rolling_ef(df)
        performance_trends.update(rolling_ef)

        return LongitudinalSummary(
            period_start=period_start,
            period_end=period_end,
            total_activities=total_activities,
            total_distance=total_distance,
            total_elevation=total_elevation,
            total_time=total_time,
            training_load=training_load,
            performance_trends=performance_trends,
            zone_distributions=zone_distributions,
        )

    def create_weekly_summary(self, enriched_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create a weekly aggregation of activities.

        Args:
            enriched_df: DataFrame of enriched activities

        Returns:
            DataFrame with weekly summaries
        """
        self.logger.info("Creating weekly summary")
        return enriched_df.groupby(pd.Grouper(key="start_date", freq="W")).agg(
            {
                "distance": "sum",
                "moving_time": "sum",
                "elevation_gain": "sum",
                "moving_training_stress_score": "sum",
            }
        )

    def create_monthly_summary(self, enriched_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create a monthly aggregation of activities.

        Args:
            enriched_df: DataFrame of enriched activities

        Returns:
            DataFrame with monthly summaries
        """
        self.logger.info("Creating monthly summary")
        return enriched_df.groupby(pd.Grouper(key="start_date", freq="M")).agg(
            {
                "distance": "sum",
                "moving_time": "sum",
                "elevation_gain": "sum",
                "moving_training_stress_score": "sum",
            }
        )
