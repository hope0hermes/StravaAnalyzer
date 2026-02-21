"""
Modernized pipeline using service layer architecture.

This is the new, simplified pipeline that uses the service layer
for better separation of concerns and testability.

NOTE: Pipeline now produces separate output files for raw and moving data:
- activities_raw.csv: Metrics from all data points
- activities_moving.csv: Metrics from moving-only data points (contiguous time)
"""

import logging
from pathlib import Path

import pandas as pd

from .constants import CSVConstants
from .exceptions import ProcessingError
from .services import AnalysisService
from .settings import Settings, load_settings

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Simplified pipeline using service layer architecture.

    This pipeline delegates most logic to the AnalysisService,
    keeping the pipeline thin and focused on orchestration.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the pipeline.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.analysis_service = AnalysisService(settings)
        self.logger = logging.getLogger(__name__)

    def run(self, *, recompute_from: str | None = None) -> None:
        """
        Execute the complete analysis pipeline.

        This method:
        1. Loads existing data
        2. Identifies activities to process
        3. Processes new activities (separate raw/moving metrics)
        4. Creates summaries
        5. Saves results to activities_raw.csv and activities_moving.csv

        Args:
            recompute_from: Optional ISO-8601 date (e.g. ``"2024-06-01"``).
                Activities on or after this date are re-processed with the
                current settings.

        Raises:
            ProcessingError: If pipeline execution fails
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("Starting Modern Pipeline")
            self.logger.info("=" * 60)

            # Run analysis workflow (returns DualAnalysisResult)
            result = self.analysis_service.run_analysis(
                recompute_from=recompute_from,
            )

            # Save results to separate files
            self.analysis_service.save_results(result)

            self.logger.info("=" * 60)
            self.logger.info("Pipeline completed successfully")
            self.logger.info(f"Total activities (raw): {len(result.raw_df)}")
            self.logger.info(f"Total activities (moving): {len(result.moving_df)}")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise ProcessingError(f"Pipeline execution failed: {e}") from e

    def process_activities(self, activities_df):
        """
        Process activities and return enriched data with summary.

        This method provides a compatible interface for the CLI.

        Args:
            activities_df: DataFrame containing activities to process

        Returns:
            Tuple of (DualAnalysisResult, summary_dict)

        Raises:
            ProcessingError: If processing fails
        """
        try:
            self.logger.info("Processing activities through modern pipeline")

            # Run analysis workflow (returns DualAnalysisResult)
            result = self.analysis_service.run_analysis()

            # Save results
            self.analysis_service.save_results(result)

            # Convert summary to dict format for CLI compatibility
            summary_dict = {
                "total_activities": result.summary.total_activities,
                "training_load": {
                    "status": result.summary.training_load.status,  # pylint: disable=no-member
                    "acwr": result.summary.training_load.acwr,  # pylint: disable=no-member
                    "ctl": result.summary.training_load.chronic_training_load,  # pylint: disable=no-member
                    "atl": result.summary.training_load.acute_training_load,  # pylint: disable=no-member
                    "tsb": result.summary.training_load.training_stress_balance,  # pylint: disable=no-member
                },
            }

            return result, summary_dict

        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise ProcessingError(f"Pipeline execution failed: {e}") from e

    def process_single_activity(self, activity_id: int) -> None:
        """Process a single activity by ID and append to existing output.

        Loads existing enriched data, processes the specified activity (if it
        hasn't been processed already), merges the result, re-runs
        post-processing (longitudinal metrics), and saves.

        Args:
            activity_id: Strava activity ID to process.

        Raises:
            ProcessingError: If processing fails.
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info(f"Processing single activity {activity_id}")
            self.logger.info("=" * 60)

            # Use recompute_from trick: prune this specific activity from
            # existing data, then let the incremental loop pick it up.
            # But simpler: just call run_analysis which already handles
            # incremental processing. If the activity is new, it'll be
            # processed. If it already exists, nothing happens (unless forced).

            # Force re-process by pruning the specific activity
            raw_file = self.settings.processed_data_dir / "activities_raw.csv"
            moving_file = self.settings.processed_data_dir / "activities_moving.csv"

            if raw_file.exists():
                raw_df = pd.read_csv(
                    raw_file, sep=CSVConstants.DEFAULT_SEPARATOR
                )
                # Remove the activity if it already exists (to force re-process)
                raw_df = raw_df[raw_df["id"] != activity_id].reset_index(drop=True)
                raw_df.to_csv(
                    raw_file, index=False, sep=CSVConstants.DEFAULT_SEPARATOR
                )

            if moving_file.exists():
                moving_df = pd.read_csv(
                    moving_file, sep=CSVConstants.DEFAULT_SEPARATOR
                )
                moving_df = moving_df[moving_df["id"] != activity_id].reset_index(
                    drop=True
                )
                moving_df.to_csv(
                    moving_file, index=False, sep=CSVConstants.DEFAULT_SEPARATOR
                )

            # Now run the normal pipeline — the activity will appear as "new"
            result = self.analysis_service.run_analysis()
            self.analysis_service.save_results(result)

            self.logger.info("=" * 60)
            self.logger.info(f"Single activity {activity_id} processed successfully")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Single activity processing failed: {e}")
            raise ProcessingError(
                f"Failed to process activity {activity_id}: {e}"
            ) from e


def run_pipeline(config_path: str) -> None:
    """
    Run the pipeline from a config file.

    Args:
        config_path: Path to the configuration YAML file
    """
    settings = load_settings(Path(config_path))
    pipeline = Pipeline(settings)
    pipeline.run()
