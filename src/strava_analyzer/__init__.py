"""Strava Analyzer - a package for analyzing Strava activity data."""

__version__ = "1.4.1"

from . import analysis, constants, data, exceptions, metrics, models, services
from .analysis import ActivityAnalyzer, ActivitySummarizer, ThresholdEstimator
from .data import ActivityDataLoader, ActivityRepository, StreamDataProcessor
from .metrics import (
    EfficiencyCalculator,
    HeartRateCalculator,
    MetricsCalculator,
    PaceCalculator,
    PowerCalculator,
    ZoneCalculator,
)
from .models import (
    ActivityStream,
    ActivityType,
    CriticalPowerModel,
    GradeAdjustmentConfig,
    LongitudinalSummary,
    MaximumMeanPowers,
    PowerProfile,
    TrainingLoadSummary,
)
from .pipeline import Pipeline
from .services import ActivityService, AnalysisService


def get_version() -> str:
    """Get the current version of strava_analyzer."""
    return __version__


def get_package_info() -> dict[str, str]:
    """Get package information including name and version."""
    return {
        "name": "strava-analyzer",
        "version": __version__,
        "description": "A package for analyzing Strava activity data",
    }


__all__ = [
    # Version & Info
    "get_version",
    "get_package_info",
    # Models
    "ActivityStream",
    "ActivityType",
    "CriticalPowerModel",
    "GradeAdjustmentConfig",
    "LongitudinalSummary",
    "MaximumMeanPowers",
    "PowerProfile",
    "TrainingLoadSummary",
    # Calculators
    "EfficiencyCalculator",
    "HeartRateCalculator",
    "MetricsCalculator",
    "PaceCalculator",
    "PowerCalculator",
    "ZoneCalculator",
    # Data Layer
    "ActivityDataLoader",
    "ActivityRepository",
    "StreamDataProcessor",
    # Analysis Layer
    "ActivityAnalyzer",
    "ActivitySummarizer",
    "ThresholdEstimator",
    # Services
    "ActivityService",
    "AnalysisService",
    # Pipeline
    "Pipeline",
    # Modules
    "analysis",
    "constants",
    "data",
    "exceptions",
    "metrics",
    "models",
    "services",
]
