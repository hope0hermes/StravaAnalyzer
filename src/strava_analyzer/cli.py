"""
Command-line interface for the Strava Analyzer package.

This module provides a clean command-line interface for running various analysis
tasks on Strava data, including activity processing and metric calculations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import click
import pandas as pd
from click import Context

from .analysis import ActivitySummarizer
from .constants import CSVConstants
from .exceptions import StravaAnalyzerError
from .pipeline import Pipeline
from .settings import load_settings


# Configure basic logging
def configure_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate level."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


@click.group()
def main():
    """
    Analyze Strava activity data and calculate performance metrics.

    This tool processes Strava activity data, calculates various performance
    metrics, and generates enriched activity data and summary statistics.
    """


@main.command()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--verbose/--quiet",
    default=False,
    help="Enable verbose output",
)
@click.option(
    "--activities",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to activities CSV file (overrides config)",
)
@click.option(
    "--streams-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to streams directory (overrides config)",
)
@click.option(
    "--force/--no-force",
    default=False,
    help="Force reprocessing of all activities",
)
def run(
    config: Path | None,
    verbose: bool,
    activities: Path | None,
    streams_dir: Path | None,
    force: bool,
) -> None:
    """
    Process Strava activities and calculate metrics.

    This command loads activity data and stream files, calculates various
    performance metrics, and saves the enriched data to CSV files.
    """
    configure_logging(verbose)
    logger = logging.getLogger(__name__)
    settings = load_settings(config)

    # Ensure processed data directory exists
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)

    # Override settings if paths provided
    if activities is not None:
        settings.activities_file = activities
    if streams_dir is not None:
        settings.streams_dir = streams_dir

    try:
        # Create pipeline
        pipeline = Pipeline(settings)

        # Load activities
        activities_df = pd.read_csv(
            settings.activities_file,
            parse_dates=["start_date"],
            sep=CSVConstants.DEFAULT_SEPARATOR,
        )

        if force:
            logger.info("Forcing reprocessing of all activities")
            # Clear existing processed data
            if settings.activities_enriched_file is not None:
                if settings.activities_enriched_file.exists():
                    settings.activities_enriched_file.unlink()

        # Process activities and get summary
        result_df, summary = pipeline.process_activities(activities_df)

        logger.info(f"Successfully processed {len(result_df)} activities")

        # Display summary statistics
        logger.info("\nActivity Summary:")
        logger.info(f"Total Activities: {summary['total_activities']}")
        logger.info(f"Training Load Status: {summary['training_load']['status']}")
        logger.info(f"ACWR: {summary['training_load']['acwr']:.2f}")

    except StravaAnalyzerError as e:
        logger.error(f"Processing failed: {str(e)}")
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise click.Abort() from e


@main.command()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--from-date",
    type=click.DateTime(),
    help="Start date for summary (YYYY-MM-DD)",
)
@click.option(
    "--to-date",
    type=click.DateTime(),
    help="End date for summary (YYYY-MM-DD)",
)
def summarize(
    config: Path | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> None:
    """
    Generate summary statistics from processed activities.

    This command reads the enriched activity data and generates various
    summary statistics and longitudinal metrics.
    """
    logger = logging.getLogger(__name__)

    try:
        settings = load_settings(config)

        if settings.activities_enriched_file is not None:
            if not settings.activities_enriched_file.exists():
                raise StravaAnalyzerError(
                    "No enriched activities found. Run 'run' command first."
                )

        # Load enriched data
        activities_df = pd.read_csv(
            settings.activities_enriched_file,
            parse_dates=["start_date"],
            sep=CSVConstants.DEFAULT_SEPARATOR,
        )

        # Filter by date if specified
        if from_date is not None:
            activities_df = activities_df[activities_df["start_date"] >= from_date]
        if to_date is not None:
            activities_df = activities_df[activities_df["start_date"] <= to_date]

        if activities_df.empty:
            logger.warning("No activities found in specified date range")
            return

        # Generate summary using the ActivitySummarizer
        summarizer = ActivitySummarizer(settings)
        summary = summarizer.generate_summary(
            activities_df, start_date=from_date, end_date=to_date
        )

        # Display summary information
        click.echo("\nActivity Summary Report")
        click.echo("=" * 40)

        click.echo(
            f"\nPeriod: {summary.period_start.date()} to {summary.period_end.date()}"  # pylint: disable=no-member
        )
        click.echo(f"Total Activities: {summary.total_activities}")
        click.echo(f"Total Distance: {summary.total_distance / 1000:.1f} km")
        click.echo(f"Total Elevation: {summary.total_elevation:.0f} m")
        click.echo(f"Total Moving Time: {summary.total_time / 3600:.1f} hours")

        click.echo("\nTraining Load Status")
        click.echo("-" * 20)
        click.echo(f"CTL: {summary.training_load.chronic_training_load:.1f}")  # pylint: disable=no-member
        click.echo(f"ATL: {summary.training_load.acute_training_load:.1f}")  # pylint: disable=no-member
        click.echo(f"TSB: {summary.training_load.training_stress_balance:.1f}")  # pylint: disable=no-member
        click.echo(f"ACWR: {summary.training_load.acwr:.2f}")  # pylint: disable=no-member
        click.echo(f"Status: {summary.training_load.status}")  # pylint: disable=no-member

        if summary.performance_trends:
            click.echo("\nPerformance Trends (% change)")
            click.echo("-" * 30)
            for metric, trend in summary.performance_trends.items():  # pylint: disable=no-member
                click.echo(f"{metric}: {trend:.1f}%")

        # Save detailed summary to file
        summary_file = settings.processed_data_dir / "activity_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            # Convert to dict (Pydantic model)
            summary_dict = summary.model_dump()
            json.dump(summary_dict, f, indent=2, default=str)

        logger.info(f"\nDetailed summary saved to {summary_file}")

        # Create zones summary file
        zones_file = settings.processed_data_dir / "training_zones_summary.csv"
        zone_data = []
        for zone_type, zones in summary.zone_distributions.items():  # pylint: disable=no-member
            for zone_name, percentage in zones.items():
                zone_data.append(
                    {
                        "zone_type": zone_type,
                        "zone_name": zone_name,
                        "percentage": percentage,
                    }
                )

        if zone_data:
            zones_df = pd.DataFrame(zone_data)
            zones_df.to_csv(zones_file, index=False, sep=CSVConstants.DEFAULT_SEPARATOR)
            logger.info(f"Zone distribution summary saved to {zones_file}")

    except StravaAnalyzerError as e:
        logger.error(f"Summary generation failed: {str(e)}")
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise click.Abort() from e


@main.command()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--verbose/--quiet",
    default=False,
    help="Enable verbose output",
)
@click.option(
    "--activities",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to activities CSV file (overrides config)",
)
@click.option(
    "--streams-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to streams directory (overrides config)",
)
@click.option(
    "--force/--no-force",
    default=False,
    help="Force reprocessing of all activities",
)
def process(
    config: Path | None,
    verbose: bool,
    activities: Path | None,
    streams_dir: Path | None,
    force: bool,
) -> None:
    """
    Process activities and generate summary in one step.

    This command combines 'run' and 'summarize' - it processes all activities
    and immediately generates a summary report.
    """
    configure_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        # First, run the processing
        logger.info("Step 1: Processing activities...")
        ctx = Context(run)
        ctx.invoke(
            run,
            config=config,
            verbose=verbose,
            activities=activities,
            streams_dir=streams_dir,
            force=force,
        )

        # Then, generate the summary
        logger.info("\nStep 2: Generating summary...")
        ctx = Context(summarize)
        ctx.invoke(summarize, config=config, from_date=None, to_date=None)

    except Exception as e:
        logger.error(f"Process command failed: {str(e)}")
        raise click.Abort() from e


@main.command()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
)
@click.argument("activity_id", type=str)
def analyze(config: Path | None, activity_id: str) -> None:
    """
    Analyze a single activity in detail.

    This command performs detailed analysis of a single activity and
    displays comprehensive metrics.
    """
    logger = logging.getLogger(__name__)

    try:
        settings = load_settings(config)
        # Create pipeline
        pipeline = Pipeline(settings)

        # Load activity data
        activities_df = pd.read_csv(
            settings.activities_file,
            parse_dates=["start_date"],
            sep=CSVConstants.DEFAULT_SEPARATOR,
        )

        # Find activity
        activity = activities_df[activities_df["id"].astype(str) == activity_id]
        if activity.empty:
            raise StravaAnalyzerError(f"Activity {activity_id} not found")

        # Process activity
        result, _ = pipeline.process_activities(activity)
        if result.empty:
            raise StravaAnalyzerError(f"Failed to process activity {activity_id}")

        # Display results
        result_dict = result.iloc[0].to_dict()

        click.echo("\nActivity Analysis Results:")
        click.echo("-" * 40)

        # Basic metrics
        click.echo("\nBasic Metrics:")
        for metric in ["distance", "moving_time", "total_elevation_gain"]:
            if metric in result_dict:
                click.echo(f"{metric.replace('_', ' ').title()}: {result_dict[metric]}")

        # Power metrics
        click.echo("\nPower Metrics:")
        for metric in [
            "average_power",
            "normalized_power",
            "intensity_factor",
            "training_stress_score",
        ]:
            if metric in result_dict:
                click.echo(
                    f"{metric.replace('_', ' ').title()}: {result_dict[metric]:.1f}"
                )

        # Heart rate metrics
        click.echo("\nHeart Rate Metrics:")
        for metric in ["average_hr", "max_hr", "efficiency_factor"]:
            if metric in result_dict:
                click.echo(
                    f"{metric.replace('_', ' ').title()}: {result_dict[metric]:.1f}"
                )

        # Zone distributions
        click.echo("\nPower Zone Distribution:")
        for zone in range(1, 8):
            zone_key = f"power_zone_perc_zone_{zone}"
            if zone_key in result_dict:
                click.echo(f"Zone {zone}: {result_dict[zone_key]:.1f}%")

    except StravaAnalyzerError as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise click.Abort() from e


if __name__ == "__main__":
    main()
