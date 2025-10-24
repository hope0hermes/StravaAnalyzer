"""
Modernized pipeline using service layer architecture.

This is the new, simplified pipeline that uses the service layer
for better separation of concerns and testability.
"""

import logging
from pathlib import Path

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

    def run(self) -> None:
        """
        Execute the complete analysis pipeline.

        This method:
        1. Loads existing data
        2. Identifies activities to process
        3. Processes new activities
        4. Creates summaries
        5. Saves results

        Raises:
            ProcessingError: If pipeline execution fails
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("Starting Modern Pipeline")
            self.logger.info("=" * 60)

            # Run analysis workflow
            enriched_df, summary = self.analysis_service.run_analysis()

            # Save results
            self.analysis_service.save_results(enriched_df, summary)

            self.logger.info("=" * 60)
            self.logger.info("Pipeline completed successfully")
            self.logger.info(f"Total activities: {len(enriched_df)}")
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
            Tuple of (enriched_df, summary_dict)

        Raises:
            ProcessingError: If processing fails
        """
        try:
            self.logger.info("Processing activities through modern pipeline")

            # Run analysis workflow
            enriched_df, summary = self.analysis_service.run_analysis()

            # Save results
            self.analysis_service.save_results(enriched_df, summary)

            # Convert summary to dict format for CLI compatibility
            summary_dict = {
                "total_activities": summary.total_activities,
                "training_load": {
                    "status": summary.training_load.status,  # pylint: disable=no-member
                    "acwr": summary.training_load.acwr,  # pylint: disable=no-member
                    "ctl": summary.training_load.chronic_training_load,  # pylint: disable=no-member
                    "atl": summary.training_load.acute_training_load,  # pylint: disable=no-member
                    "tsb": summary.training_load.training_stress_balance,  # pylint: disable=no-member
                },
            }

            return enriched_df, summary_dict

        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise ProcessingError(f"Pipeline execution failed: {e}") from e


def run_pipeline(config_path: str) -> None:
    """
    Run the pipeline from a config file.

    Args:
        config_path: Path to the configuration YAML file
    """
    settings = load_settings(Path(config_path))
    pipeline = Pipeline(settings)
    pipeline.run()
