"""
High-level service for coordinating full analysis workflows.

This service orchestrates the complete analysis process including
data loading, processing, threshold estimation, and summarization.
"""

import json
import logging
from typing import Protocol

import pandas as pd

from ..analysis import ActivitySummarizer, ThresholdEstimator
from ..constants import CSVConstants
from ..data import ActivityDataLoader
from ..exceptions import DataLoadError, ProcessingError
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
            # Save enriched activities
            output_file = self.settings.activities_enriched_file
            self.logger.info(f"Saving enriched activities to {output_file}")
            enriched_df.to_csv(
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
