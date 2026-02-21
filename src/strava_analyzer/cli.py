"""
Command-line interface for the Strava Analyzer package.

This module provides a clean command-line interface for running analysis
tasks on Strava data.
"""

import logging
from pathlib import Path

import click
import pandas as pd
from click import Group

from .constants import CSVConstants
from .exceptions import StravaAnalyzerError
from .pipeline import Pipeline
from .settings import load_settings


# Custom command class to show full help text
class CustomGroup(Group):
    """Custom Click group that shows full command help without truncation."""

    def format_commands(self, ctx, formatter):
        """Format commands with full descriptions."""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            help_text = cmd.get_short_help_str(limit=999)
            commands.append((subcommand, help_text))

        if commands:
            with formatter.section("Commands"):
                formatter.write_dl(commands)


# Configure basic logging
def configure_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate level."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


@click.group(cls=CustomGroup, context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """Analyze Strava activity data and calculate performance metrics.

    Quick start: strava-analyzer run --config config.yaml
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
@click.option(
    "--recompute-from",
    type=str,
    default=None,
    help=(
        "Re-process activities from this date onward (ISO-8601, e.g. 2024-06-01). "
        "Useful after changing FTP/FTHR/weight without re-processing the entire history."
    ),
)
def run(
    config: Path | None,
    verbose: bool,
    activities: Path | None,
    streams_dir: Path | None,
    force: bool,
    recompute_from: str | None,
) -> None:
    """
    Process all activities and generate comprehensive analysis.

    Includes per-activity metrics (power, HR, efficiency, zones, TSS),
    longitudinal analysis (ATL, CTL, TSB, ACWR), and power profile metrics.
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
            recompute_from = None  # --force supersedes --recompute-from

        if recompute_from:
            logger.info(
                "Re-processing activities from %s onward", recompute_from
            )

        # Process activities and generate summary
        logger.info("Processing activities and generating analysis...")
        pipeline.run(recompute_from=recompute_from if not force else None)

        # Load summary from saved file
        summary_file = settings.processed_data_dir / "activity_summary.json"
        if summary_file.exists():
            import json

            with open(summary_file, encoding="utf-8") as f:
                summary = json.load(f)

            click.echo("\n" + "=" * 50)
            click.echo("ANALYSIS COMPLETE")
            click.echo("=" * 50)
            click.echo(f"\nTotal Activities: {summary.get('total_activities', 'N/A')}")
            tl = summary.get("training_load", {})
            click.echo(f"Training Load Status: {tl.get('status', 'N/A')}")
            click.echo(f"CTL: {tl.get('chronic_training_load', 0):.1f}")
            click.echo(f"ATL: {tl.get('acute_training_load', 0):.1f}")
            click.echo(f"TSB: {tl.get('training_stress_balance', 0):.1f}")
            click.echo(f"ACWR: {tl.get('acwr', 0):.2f}")
        else:
            click.echo("\nAnalysis complete.")
        click.echo(f"\nResults saved to: {settings.processed_data_dir}")

    except StravaAnalyzerError as e:
        logger.error(f"Processing failed: {str(e)}")
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise click.Abort() from e


@main.command("process-activity")
@click.argument("activity_id", type=int)
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
def process_activity(
    activity_id: int,
    config: Path | None,
    verbose: bool,
) -> None:
    """Process a single activity by Strava ID.

    Computes metrics for the specified activity and appends the result
    to the existing enriched output files, then re-runs longitudinal
    post-processing (CTL/ATL/TSB, CP model).

    Usage: strava-analyzer process-activity 1234567890
    """
    configure_logging(verbose)
    logger = logging.getLogger(__name__)
    settings = load_settings(config)
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)

    try:
        pipeline = Pipeline(settings)
        pipeline.process_single_activity(activity_id)
        click.echo(f"\nActivity {activity_id} processed successfully.")
        click.echo(f"Results saved to: {settings.processed_data_dir}")

    except StravaAnalyzerError as e:
        logger.error(f"Processing failed: {str(e)}")
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise click.Abort() from e


if __name__ == "__main__":
    main()
