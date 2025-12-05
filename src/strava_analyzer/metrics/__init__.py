"""
Metrics calculation modules.

This package contains all metric calculation logic, organized by type:
- power: Power-based metrics (NP, IF, TSS, power curves)
- power_curve: Power curve analysis and critical power modeling
- heartrate: Heart rate metrics (avg HR, zones, hrTSS)
- efficiency: Efficiency and decoupling metrics
- pace: Running pace metrics (NGP, rTSS)
- zones: Zone distribution calculations
- tid: Training Intensity Distribution analysis
- fatigue: Fatigue resistance and power decay metrics
- basic: Basic aggregated metrics (cadence, speed)
- zone_edges: Zone edges tracking and backpropagation
- calculators: High-level calculator orchestrators
"""

from .basic import BasicMetricsCalculator
from .calculators import MetricsCalculator
from .efficiency import EfficiencyCalculator
from .fatigue import FatigueCalculator
from .heartrate import HeartRateCalculator
from .pace import PaceCalculator
from .power import PowerCalculator
from .power_curve import (
    estimate_cp_wprime,
    extract_mmp_data,
    hyperbolic_model,
    interval_name_from_seconds,
)
from .tid import TIDCalculator
from .zone_edges import ZoneEdgesManager
from .zones import ZoneCalculator

__all__ = [
    "MetricsCalculator",
    "PowerCalculator",
    "HeartRateCalculator",
    "EfficiencyCalculator",
    "PaceCalculator",
    "ZoneCalculator",
    "TIDCalculator",
    "FatigueCalculator",
    "BasicMetricsCalculator",
    "ZoneEdgesManager",
    "estimate_cp_wprime",
    "extract_mmp_data",
    "hyperbolic_model",
    "interval_name_from_seconds",
]
