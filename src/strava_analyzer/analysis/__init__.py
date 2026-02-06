"""
Analysis and computation layer.

This package contains modules for analyzing activities and computing summaries.
"""

from .analyzer import ActivityAnalyzer, AnalysisResult
from .summarizer import ActivitySummarizer
from .threshold_estimator import ThresholdEstimator

__all__ = [
    "ActivityAnalyzer",
    "AnalysisResult",
    "ActivitySummarizer",
    "ThresholdEstimator",
]
