"""
High-level service for coordinating full analysis workflows.

This service orchestrates the complete analysis process including
data loading, processing, threshold estimation, and summarization.
"""

import json
import logging
from datetime import datetime
from typing import Protocol

import pandas as pd

from ..analysis import ActivitySummarizer, ThresholdEstimator
from ..constants import CSVConstants, TrainingLoadWindows
from ..data import ActivityDataLoader
from ..exceptions import DataLoadError, ProcessingError
from ..metrics import ZoneEdgesManager
from ..models import LongitudinalSummary
from ..settings import Settings
from .activity_service import ActivityService

logger = logging.getLogger(__name__)


class AnalysisServiceProtocol(Protocol):
    """Protocol for analysis services."""

    def run_analysis(self) -> tuple[pd.DataFrame, LongitudinalSummary]:
        """Run complete analysis workflow."""
        ...


class AnalysisService:
    """
    High-level service coordinating the complete analysis workflow.

    This service orchestrates:
    - Loading existing data
    - Identifying activities to process
    - Processing activities
    - Estimating thresholds
    - Creating summaries
    - Saving results
    """

    def __init__(self, settings: Settings):
        """
        Initialize the analysis service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # Initialize sub-services
        self.activity_service = ActivityService(settings)
        self.loader = ActivityDataLoader(settings)
        self.threshold_estimator = ThresholdEstimator(settings)
        self.summarizer = ActivitySummarizer(settings)
        self.zone_edges_manager = ZoneEdgesManager(settings)

    def run_analysis(self) -> tuple[pd.DataFrame, LongitudinalSummary]:
        """
        Run the complete analysis workflow.

        Returns:
            Tuple of (enriched activities DataFrame, longitudinal summary)

        Raises:
            DataLoadError: If data loading fails
            ProcessingError: If processing fails
        """
        try:
            # Load existing data
            self.logger.info("Starting analysis workflow")
            enriched_df, historical_thresholds = self._load_existing_data()

            # Get activities to process
            activities_to_process = self.activity_service.get_activities_to_process()

            if activities_to_process.empty:
                self.logger.info("No new activities to process")
                if enriched_df is None:
                    raise DataLoadError("No activities to analyze")
            else:
                # Process new activities
                new_enriched = self._process_activities(
                    activities_to_process, historical_thresholds
                )

                # Merge with existing data
                if enriched_df is not None:
                    enriched_df = pd.concat(
                        [enriched_df, new_enriched], ignore_index=True
                    )
                else:
                    enriched_df = new_enriched

            # STEP 1: Sort by start_date_local in descending order (most recent first)
            if enriched_df is not None and not enriched_df.empty:
                if "start_date_local" in enriched_df.columns:
                    enriched_df = enriched_df.sort_values(
                        "start_date_local", ascending=False
                    ).reset_index(drop=True)
                    self.logger.info("Sorted activities by start_date_local (descending)")

                # STEP 2: Apply zone edges with backpropagation as FIRST metric step
                enriched_df = self.zone_edges_manager.apply_zone_edges_with_backpropagation(
                    enriched_df, config_timestamp=datetime.now()
                )
                self.logger.info("Applied zone edges with backpropagation")

            # Create summary
            summary = self.summarizer.summarize(enriched_df)

            self.logger.info("Analysis workflow completed successfully")
            return enriched_df, summary

        except Exception as e:
            self.logger.error(f"Analysis workflow failed: {e}")
            raise ProcessingError(f"Error in analysis workflow: {e}") from e

    def _load_existing_data(
        self,
    ) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        """Load existing enriched activities and historical thresholds."""
        self.logger.info("Loading existing data")

        enriched_df = self.loader.load_enriched_activities()
        historical_thresholds = self.loader.load_historical_thresholds()

        return enriched_df, historical_thresholds

    def _process_activities(
        self, activities_df: pd.DataFrame, historical_thresholds: pd.DataFrame | None
    ) -> pd.DataFrame:
        """
        Process a set of activities.

        Args:
            activities_df: DataFrame of activities to process
            historical_thresholds: Historical threshold data

        Returns:
            DataFrame of enriched activities
        """
        self.logger.info(f"Processing {len(activities_df)} activities")

        enriched_rows = []

        for idx, activity_row in activities_df.iterrows():
            activity_id = activity_row["id"]

            try:
                # Check if stream exists
                if not self.activity_service.activity_has_stream(activity_id):
                    self.logger.warning(f"No stream data for activity {activity_id}")
                    continue

                # Process activity
                metrics, _ = self.activity_service.process_activity(activity_row)

                # Combine metadata and metrics
                enriched_row = {**activity_row.to_dict(), **metrics}
                enriched_rows.append(enriched_row)

                self.logger.info(
                    f"Processed activity {activity_id} ({idx + 1}/{len(activities_df)})"
                )

            except Exception as e:
                self.logger.error(f"Failed to process activity {activity_id}: {e}")
                continue

        if not enriched_rows:
            self.logger.warning("No activities were successfully processed")
            return pd.DataFrame()

        enriched_df = pd.DataFrame(enriched_rows)
        self.logger.info(f"Successfully processed {len(enriched_df)} activities")

        return enriched_df

    def save_results(
        self, enriched_df: pd.DataFrame, summary: LongitudinalSummary
    ) -> None:
        """
        Save analysis results to files.

        Args:
            enriched_df: Enriched activities DataFrame
            summary: Longitudinal summary object
        """
        try:
            # Add FTP/FTHR columns for reference
            enriched_df_export = enriched_df.copy()
            enriched_df_export["ftp"] = self.settings.ftp
            enriched_df_export["fthr"] = self.settings.fthr
            
            # Add LT values (from stress test) for reference
            enriched_df_export["lt1_power"] = self.settings.lt1_power
            enriched_df_export["lt2_power"] = self.settings.lt2_power
            enriched_df_export["lt1_hr"] = self.settings.lt1_hr
            enriched_df_export["lt2_hr"] = self.settings.lt2_hr
            
            # Compute per-activity training load metrics (CTL, ATL, TSB, ACWR)
            enriched_df_export = self._compute_per_activity_training_load(enriched_df_export)
            
            # Compute per-activity CP model metrics (CP, W', r², AEI) with rolling window
            enriched_df_export = self._compute_per_activity_cp_model(enriched_df_export)
            
            # Save enriched activities
            output_file = self.settings.activities_enriched_file
            self.logger.info(f"Saving enriched activities to {output_file}")
            enriched_df_export.to_csv(
                output_file, index=False, sep=CSVConstants.DEFAULT_SEPARATOR
            )

            # Save summary
            summary_file = self.settings.processed_data_dir / "activity_summary.json"
            self.logger.info(f"Saving summary to {summary_file}")

            # Convert to dict for serialization (Pydantic model)
            summary_dict = summary.model_dump()

            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary_dict, f, indent=2, default=str)

            self.logger.info("Results saved successfully")

        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            raise ProcessingError(f"Failed to save results: {e}") from e

    def _compute_per_activity_training_load(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-activity training load metrics (CTL, ATL, TSB, ACWR).
        
        Each activity gets the training load state as of that activity's date,
        using proper time-based exponential decay (not row-based).
        
        The exponential decay is applied based on actual calendar days:
        - CTL uses 42-day time constant (chronic fitness)
        - ATL uses 7-day time constant (acute fatigue)
        
        Args:
            df: DataFrame with activities and TSS values
            
        Returns:
            DataFrame with added training load columns
        """
        import numpy as np
        
        # Determine TSS column to use
        tss_column = (
            "moving_training_stress_score"
            if "moving_training_stress_score" in df.columns
            else "raw_training_stress_score"
        )
        
        if tss_column not in df.columns:
            self.logger.warning("No TSS column found, skipping training load calculation")
            df["chronic_training_load"] = 0.0
            df["acute_training_load"] = 0.0
            df["training_stress_balance"] = 0.0
            df["acwr"] = 0.0
            return df
        
        # Ensure date column exists
        date_col = "start_date_local" if "start_date_local" in df.columns else "start_date"
        if date_col not in df.columns:
            self.logger.warning("No date column found, skipping training load calculation")
            df["chronic_training_load"] = 0.0
            df["acute_training_load"] = 0.0
            df["training_stress_balance"] = 0.0
            df["acwr"] = 0.0
            return df
        
        # Sort by date ASCENDING for chronological processing
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col, ascending=True).reset_index(drop=True)
        
        # Time constants in days
        ctl_tc = TrainingLoadWindows.CTL_DAYS  # 42 days
        atl_tc = TrainingLoadWindows.ATL_DAYS  # 7 days
        
        # Initialize arrays for results
        n = len(df)
        ctl_values = np.zeros(n)
        atl_values = np.zeros(n)
        
        # Get TSS values and dates
        tss_values = df[tss_column].fillna(0).values
        dates = df[date_col].values
        
        # Compute time-based exponential weighted averages
        # For each activity, we apply exponential decay based on days elapsed
        for i in range(n):
            current_date = dates[i]
            current_tss = tss_values[i]
            
            if i == 0:
                # First activity: CTL and ATL equal to the TSS of that day
                # (or could start at 0 and add the day's contribution)
                ctl_values[i] = current_tss
                atl_values[i] = current_tss
            else:
                prev_date = dates[i - 1]
                # Calculate days elapsed since previous activity
                days_elapsed = (pd.Timestamp(current_date) - pd.Timestamp(prev_date)).days
                days_elapsed = max(days_elapsed, 0)  # Handle same-day activities
                
                # Decay factors based on time elapsed
                # decay = exp(-days_elapsed / time_constant)
                ctl_decay = np.exp(-days_elapsed / ctl_tc)
                atl_decay = np.exp(-days_elapsed / atl_tc)
                
                # Update: new_value = old_value * decay + today_tss * (1 - decay_for_1_day)
                # The (1 - exp(-1/tc)) factor represents the weight for a single day's TSS
                ctl_weight = 1 - np.exp(-1 / ctl_tc)
                atl_weight = 1 - np.exp(-1 / atl_tc)
                
                # Apply decay to previous value, then add today's weighted contribution
                ctl_values[i] = ctl_values[i - 1] * ctl_decay + current_tss * ctl_weight
                atl_values[i] = atl_values[i - 1] * atl_decay + current_tss * atl_weight
        
        # Assign computed values
        df["chronic_training_load"] = ctl_values
        df["acute_training_load"] = atl_values
        
        # Calculate TSB (Training Stress Balance = CTL - ATL)
        df["training_stress_balance"] = df["chronic_training_load"] - df["acute_training_load"]
        
        # Calculate ACWR (Acute:Chronic Workload Ratio)
        df["acwr"] = np.where(
            df["chronic_training_load"] > 0,
            df["acute_training_load"] / df["chronic_training_load"],
            0.0
        )
        
        # Sort back to descending (most recent first) for export
        df = df.sort_values(date_col, ascending=False).reset_index(drop=True)
        
        self.logger.info("Computed per-activity training load metrics with time-based decay (CTL, ATL, TSB, ACWR)")
        
        return df

    def _compute_per_activity_cp_model(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-activity Critical Power model metrics using rolling time windows.
        
        Each activity gets CP/W' computed from the maximum power curve values
        within the trailing window (default 90 days). This represents the athlete's
        current power-duration capacity at the time of each activity.
        
        Args:
            df: DataFrame with activities and power_curve columns
            
        Returns:
            DataFrame with added CP model columns: cp, w_prime, cp_r_squared, aei
        """
        import numpy as np
        from ..metrics.power_curve import estimate_cp_wprime, interval_name_from_seconds
        
        # Get power curve column names
        power_curve_cols = [col for col in df.columns if col.startswith("power_curve_")]
        
        if not power_curve_cols:
            self.logger.warning("No power curve columns found, skipping CP model calculation")
            df["cp"] = np.nan
            df["w_prime"] = np.nan
            df["cp_r_squared"] = np.nan
            df["aei"] = np.nan
            return df
        
        # Ensure date column exists
        date_col = "start_date_local" if "start_date_local" in df.columns else "start_date"
        if date_col not in df.columns:
            self.logger.warning("No date column found, skipping CP model calculation")
            df["cp"] = np.nan
            df["w_prime"] = np.nan
            df["cp_r_squared"] = np.nan
            df["aei"] = np.nan
            return df
        
        # Sort by date ASCENDING for chronological processing
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], utc=True)
        df = df.sort_values(date_col, ascending=True).reset_index(drop=True)
        
        # Get CP window from constants (default 90 days)
        cp_window_days = TrainingLoadWindows.CP_WINDOW_DAYS
        
        # Map column names to durations (in seconds)
        col_to_duration = {}
        for col in power_curve_cols:
            # Extract duration from column name (e.g., "power_curve_5min" -> 300)
            duration_str = col.replace("power_curve_", "")
            for interval_name, duration_sec in self.settings.power_curve_intervals.items():
                if interval_name_from_seconds(duration_sec) == duration_str:
                    col_to_duration[col] = duration_sec
                    break
        
        # Initialize arrays for results
        n = len(df)
        cp_values = np.full(n, np.nan)
        w_prime_values = np.full(n, np.nan)
        r_squared_values = np.full(n, np.nan)
        aei_values = np.full(n, np.nan)
        
        # Get rider weight for AEI calculation
        rider_weight = self.settings.rider_weight_kg
        
        # For each activity, look back cp_window_days and find max power at each duration
        for i in range(n):
            current_date = df.loc[i, date_col]
            window_start = current_date - pd.Timedelta(days=cp_window_days)
            
            # Get activities within the window (up to and including current activity)
            window_mask = (df[date_col] >= window_start) & (df[date_col] <= current_date)
            window_df = df[window_mask]
            
            # Need at least a few activities with power data
            if len(window_df) < 2:
                continue
            
            # Extract MMP data: max power at each duration across the window
            mmp_data = []
            for col, duration_sec in col_to_duration.items():
                if col in window_df.columns:
                    max_power = window_df[col].max()
                    if pd.notna(max_power) and max_power > 0:
                        mmp_data.append((duration_sec, float(max_power)))
            
            # Need at least 3 points for meaningful curve fitting
            if len(mmp_data) < 3:
                continue
            
            # Fit CP model
            result = estimate_cp_wprime(mmp_data)
            
            cp_values[i] = result["cp"]
            w_prime_values[i] = result["w_prime"]
            r_squared_values[i] = result["r_squared"]
            
            # Calculate AEI (Anaerobic Energy Index = W' / body_weight)
            if pd.notna(result["w_prime"]) and rider_weight > 0:
                # W' is in joules, AEI is typically in J/kg
                aei_values[i] = result["w_prime"] / rider_weight
        
        # Assign computed values
        df["cp"] = cp_values
        df["w_prime"] = w_prime_values
        df["cp_r_squared"] = r_squared_values
        df["aei"] = aei_values
        
        # Sort back to descending (most recent first) for export
        df = df.sort_values(date_col, ascending=False).reset_index(drop=True)
        
        self.logger.info(
            f"Computed per-activity CP model metrics with {cp_window_days}-day rolling window"
        )
        
        return df

    def estimate_current_thresholds(
        self, enriched_df: pd.DataFrame
    ) -> dict[str, float]:
        """
        Estimate current FTP and FTHR.

        Args:
            enriched_df: Enriched activities DataFrame

        Returns:
            Dictionary with estimated thresholds
        """
        historical_thresholds = self.loader.load_historical_thresholds()
        return self.threshold_estimator.estimate(enriched_df, historical_thresholds)
