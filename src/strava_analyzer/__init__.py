"""Strava Analyzer - a package for analyzing Strava activity data."""

__version__ = "1.0.1"

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
    ActivityMetrics,
    ActivityStream,
    ActivitySummary,
    ActivityType,
    CriticalPowerModel,
    GradeAdjustmentConfig,
    HeartRateZoneConfig,
    HeartRateZones,
    LongitudinalSummary,
    MaximumMeanPowers,
    PowerProfile,
    PowerZones,
    RunningMetrics,
    TrainingLoadSummary,
)
from .pipeline import Pipeline
from .services import ActivityService, AnalysisService

__all__ = [
    # Models
    "ActivityMetrics",
    "ActivityStream",
    "ActivitySummary",
    "ActivityType",
    "CriticalPowerModel",
    "GradeAdjustmentConfig",
    "HeartRateZoneConfig",
    "HeartRateZones",
    "LongitudinalSummary",
    "MaximumMeanPowers",
    "PowerProfile",
    "PowerZones",
    "RunningMetrics",
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
