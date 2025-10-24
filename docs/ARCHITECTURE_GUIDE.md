# Strava Analyzer Architecture Guide

## Overview

Strava Analyzer follows a **layered architecture** with clear separation of concerns, making it maintainable, testable, and extensible. This guide explains the architecture and how to work with it.

---

## Architecture Layers

### Visual Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI / Pipeline                         │
│                  (Entry points for users)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    SERVICE LAYER                            │
│  High-level workflows and orchestration                     │
│                                                              │
│  • ActivityService: Activity processing workflows           │
│  • AnalysisService: Complete analysis orchestration         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   ANALYSIS LAYER                            │
│  Business logic and computations                            │
│                                                              │
│  • ActivityAnalyzer: Individual activity analysis           │
│  • ActivitySummarizer: Summaries and aggregations          │
│  • ThresholdEstimator: FTP/FTHR estimation                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     DATA LAYER                              │
│  Data access, I/O, and cleaning                             │
│                                                              │
│  • ActivityDataLoader: File I/O operations                  │
│  • StreamDataProcessor: Data cleaning & validation          │
│  • ActivityRepository: Query and filtering logic            │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   METRICS LAYER                             │
│  Domain-specific metric calculations                        │
│                                                              │
│  • PowerCalculator: Power metrics (NP, IF, TSS)            │
│  • HeartRateCalculator: HR metrics                          │
│  • EfficiencyCalculator: Efficiency metrics                 │
│  • PaceCalculator: Pace metrics                             │
│  • ZoneCalculator: Zone distributions                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. Service Layer (`services/`)

**Purpose**: Orchestrate high-level workflows

**Components**:
- `ActivityService`: Coordinates single activity processing
- `AnalysisService`: Coordinates full analysis workflow

**Key Characteristics**:
- ✅ Coordinates multiple components
- ✅ Handles error recovery
- ✅ Manages transactions
- ✅ Provides simple interfaces
- ❌ No direct calculations
- ❌ No direct file I/O

**Example**:
```python
from strava_analyzer.services import ActivityService

service = ActivityService(settings)
metrics, stream = service.process_activity(activity_row)
# Coordinates: load → clean → analyze
```

### 2. Analysis Layer (`analysis/`)

**Purpose**: Implement business logic and computations

**Components**:
- `ActivityAnalyzer`: Analyzes individual activities
- `ActivitySummarizer`: Creates summaries and aggregations
- `ThresholdEstimator`: Estimates FTP and FTHR

**Key Characteristics**:
- ✅ Business logic only
- ✅ Works with data structures
- ✅ Delegates to metrics layer
- ❌ No I/O operations
- ❌ No file system access

**Example**:
```python
from strava_analyzer.analysis import ActivityAnalyzer

analyzer = ActivityAnalyzer(settings)
metrics = analyzer.analyze(activity_row, stream_df)
# Pure computation, no I/O
```

### 3. Data Layer (`data/`)

**Purpose**: Handle data access and preparation

**Components**:
- `ActivityDataLoader`: File I/O operations
- `StreamDataProcessor`: Data cleaning and validation
- `ActivityRepository`: Query and filtering logic

**Key Characteristics**:
- ✅ File I/O operations
- ✅ Data cleaning
- ✅ Query logic
- ✅ Caching
- ❌ No business logic
- ❌ No metric calculations

**Example**:
```python
from strava_analyzer.data import ActivityDataLoader, StreamDataProcessor

loader = ActivityDataLoader(settings)
processor = StreamDataProcessor(settings)

raw_df = loader.load_stream(activity_id)
clean_df = processor.process(raw_df)
# Data access and cleaning only
```

### 4. Metrics Layer (`metrics/`)

**Purpose**: Calculate domain-specific metrics

**Components**:
- `PowerCalculator`: Power-based metrics
- `HeartRateCalculator`: HR-based metrics
- `EfficiencyCalculator`: Efficiency metrics
- `PaceCalculator`: Pace-based metrics
- `ZoneCalculator`: Zone distributions

**Key Characteristics**:
- ✅ Domain calculations
- ✅ Single responsibility
- ✅ Independent calculators
- ❌ No I/O
- ❌ No orchestration

**Example**:
```python
from strava_analyzer.metrics import PowerCalculator

calc = PowerCalculator(settings)
metrics = calc.calculate(stream_df, moving_only=False)
# {'raw_normalized_power': 250.5, 'raw_intensity_factor': 0.87, ...}
```

---

## Dependency Flow

### Allowed Dependencies

```
CLI/Pipeline
    ↓
Services  →  Analysis  →  Data  →  Metrics
    ↓            ↓          ↓
  (compose)   (use)    (access)
```

### Rules

✅ **Allowed**:
- Services can use Analysis, Data, and Metrics
- Analysis can use Data and Metrics
- Data can use basic utilities
- Metrics are self-contained

❌ **Forbidden**:
- Data calling Analysis
- Metrics calling Data
- Lower layers calling higher layers
- Circular dependencies

---

## Component Details

### ActivityService

**Location**: `services/activity_service.py`

**Purpose**: Coordinate activity processing workflow

**Methods**:
```python
class ActivityService:
    def process_activity(self, activity_row) -> tuple[dict, DataFrame]:
        """Process activity: load → clean → analyze"""

    def get_activities_to_process(self) -> DataFrame:
        """Get activities needing processing"""

    def activity_has_stream(self, activity_id) -> bool:
        """Check if stream exists"""
```

**Workflow**:
1. Load stream data via `ActivityDataLoader`
2. Clean data via `StreamDataProcessor`
3. Analyze via `ActivityAnalyzer`
4. Return metrics and processed stream

**Usage**:
```python
service = ActivityService(settings)
metrics, stream = service.process_activity(activity_row)
```

### AnalysisService

**Location**: `services/analysis_service.py`

**Purpose**: Orchestrate complete analysis workflow

**Methods**:
```python
class AnalysisService:
    def run_analysis(self) -> tuple[DataFrame, LongitudinalSummary]:
        """Run complete analysis workflow"""

    def save_results(self, enriched_df, summary) -> None:
        """Save analysis results"""

    def estimate_current_thresholds(self, enriched_df) -> dict:
        """Estimate FTP and FTHR"""
```

**Workflow**:
1. Load existing data
2. Identify new activities
3. Process each activity
4. Create summaries
5. Save results

**Usage**:
```python
service = AnalysisService(settings)
enriched_df, summary = service.run_analysis()
service.save_results(enriched_df, summary)
```

### ActivityDataLoader

**Location**: `data/loader.py`

**Purpose**: Handle all file I/O operations

**Methods**:
```python
class ActivityDataLoader:
    def load_activities(self) -> DataFrame:
        """Load activities from CSV"""

    def load_stream(self, activity_id) -> DataFrame:
        """Load stream data for activity"""

    def load_enriched_activities(self) -> DataFrame | None:
        """Load previously processed data"""

    def stream_exists(self, activity_id) -> bool:
        """Check if stream file exists"""
```

**Usage**:
```python
loader = ActivityDataLoader(settings)
activities = loader.load_activities()
stream = loader.load_stream(activity_id)
```

### StreamDataProcessor

**Location**: `data/processor.py`

**Purpose**: Clean and validate stream data

**Methods**:
```python
class StreamDataProcessor:
    def process(self, df: DataFrame) -> DataFrame:
        """Complete cleaning pipeline"""
```

**Processing Steps**:
1. Validate essential columns
2. Process temporal data (time)
3. Process physiological data (HR) - forward fill
4. Process power data (watts, cadence) - zero fill
5. Process motion data (velocity, grade, altitude)
6. Process GPS data (extract lat/lng)
7. Infer moving state

**Usage**:
```python
processor = StreamDataProcessor(settings)
clean_df = processor.process(raw_df)
```

### ActivityRepository

**Location**: `data/repository.py`

**Purpose**: Provide high-level queries for activity data

**Methods**:
```python
class ActivityRepository:
    def get_all_activities(self) -> DataFrame:
        """Get all activities"""

    def get_activities_by_type(self, activity_type) -> DataFrame:
        """Filter by activity type"""

    def get_supported_activities(self) -> DataFrame:
        """Get Ride/VirtualRide/Run only"""

    def get_activities_needing_processing(self, enriched_df=None) -> DataFrame:
        """Find unprocessed activities"""

    def get_recent_activities(self, n=10) -> DataFrame:
        """Get N most recent"""
```

**Features**:
- Caching for performance
- Business logic queries
- Filters and transformations

**Usage**:
```python
repo = ActivityRepository(loader, settings)
rides = repo.get_activities_by_type(ActivityType.RIDE)
recent = repo.get_recent_activities(10)
```

### ActivityAnalyzer

**Location**: `analysis/analyzer.py`

**Purpose**: Analyze individual activities

**Methods**:
```python
class ActivityAnalyzer:
    def analyze(self, activity_row, stream_df) -> dict[str, float]:
        """Analyze activity and compute metrics"""

    def supports_activity_type(self, activity_type) -> bool:
        """Check if type is supported"""
```

**Usage**:
```python
analyzer = ActivityAnalyzer(settings)
metrics = analyzer.analyze(activity_row, stream_df)
```

### MetricsCalculator

**Location**: `metrics/calculators.py`

**Purpose**: Orchestrate all metric calculations

**Methods**:
```python
class MetricsCalculator:
    def compute_all_metrics(
        self, stream_df, activity_type,
        compute_raw=True, compute_moving=True
    ) -> dict[str, float]:
        """Compute all metrics for activity"""
```

**Composition**:
```python
self.power_calculator = PowerCalculator(settings)
self.hr_calculator = HeartRateCalculator(settings)
self.efficiency_calculator = EfficiencyCalculator(settings)
self.pace_calculator = PaceCalculator(settings)
self.zone_calculator = ZoneCalculator(settings)
```

**Usage**:
```python
calc = MetricsCalculator(settings)
metrics = calc.compute_all_metrics(stream_df, "ride")
```

---

## Usage Patterns

### Pattern 1: Process Single Activity

```python
from strava_analyzer.services import ActivityService

service = ActivityService(settings)

# Get activity metadata
activity = service.get_activity(activity_id)

# Process it
if service.activity_has_stream(activity_id):
    metrics, stream = service.process_activity(activity)
    print(f"Normalized Power: {metrics['raw_normalized_power']}")
```

### Pattern 2: Run Full Analysis

```python
from strava_analyzer.services import AnalysisService

service = AnalysisService(settings)

# Run complete workflow
enriched_df, summary = service.run_analysis()

# Save results
service.save_results(enriched_df, summary)

print(f"Processed {len(enriched_df)} activities")
```

### Pattern 3: Use Modern Pipeline

```python
from strava_analyzer.modern_pipeline import ModernPipeline

pipeline = ModernPipeline(settings)
pipeline.run()
# Done! Handles everything
```

### Pattern 4: Custom Workflow

```python
from strava_analyzer.data import ActivityDataLoader, StreamDataProcessor
from strava_analyzer.analysis import ActivityAnalyzer
from strava_analyzer.metrics import PowerCalculator

# Build custom workflow
loader = ActivityDataLoader(settings)
processor = StreamDataProcessor(settings)
analyzer = ActivityAnalyzer(settings)

# Custom processing
activities = loader.load_activities()
for idx, row in activities.head(10).iterrows():
    stream = loader.load_stream(row['id'])
    clean_stream = processor.process(stream)
    metrics = analyzer.analyze(row, clean_stream)
    print(f"{row['name']}: {metrics['raw_normalized_power']} W")
```

### Pattern 5: Testing with Mocks

```python
from unittest.mock import Mock
from strava_analyzer.data import ActivityRepository

def test_repository():
    # Mock the loader
    mock_loader = Mock()
    mock_loader.load_activities.return_value = sample_df

    # Test repository in isolation
    repo = ActivityRepository(mock_loader, settings)
    result = repo.get_supported_activities()

    assert len(result) > 0
    mock_loader.load_activities.assert_called_once()
```

---

## Extension Points

### Adding a New Data Source

Create a new loader implementing `DataLoaderProtocol`:

```python
from strava_analyzer.data.loader import DataLoaderProtocol

class DatabaseActivityLoader:
    def load_activities(self) -> DataFrame:
        return pd.read_sql("SELECT * FROM activities", conn)

    def load_stream(self, activity_id) -> DataFrame:
        return pd.read_sql(f"SELECT * FROM streams WHERE id={activity_id}", conn)

# Use it
loader = DatabaseActivityLoader(connection_string)
repo = ActivityRepository(loader, settings)
```

### Adding a New Metric Calculator

Create a calculator inheriting from `BaseMetricCalculator`:

```python
from strava_analyzer.metrics.base import BaseMetricCalculator

class CadenceCalculator(BaseMetricCalculator):
    def calculate(self, stream_df, moving_only=False) -> dict[str, float]:
        df = self._filter_moving(stream_df, moving_only)
        prefix = self._get_prefix(moving_only)

        return {
            f"{prefix}avg_cadence": df['cadence'].mean(),
            f"{prefix}max_cadence": df['cadence'].max(),
        }

# Add to MetricsCalculator
calc = MetricsCalculator(settings)
calc.cadence_calculator = CadenceCalculator(settings)
```

### Adding a New Service

Create a service following the pattern:

```python
class ExportService:
    def __init__(self, settings):
        self.settings = settings
        self.loader = ActivityDataLoader(settings)

    def export_to_json(self, activity_id):
        stream = self.loader.load_stream(activity_id)
        return stream.to_json()
```

---

## Best Practices

### DO ✅

1. **Use Services for workflows**: Let services coordinate components
2. **Use Repository for queries**: Don't load files directly
3. **Test each layer independently**: Use mocks for dependencies
4. **Follow the dependency rule**: Only depend on lower layers
5. **Use protocols for flexibility**: Define interfaces with protocols
6. **Keep components focused**: Single responsibility per class

### DON'T ❌

1. **Don't mix concerns**: Keep data, analysis, and orchestration separate
2. **Don't skip layers**: Use the appropriate layer for each task
3. **Don't create circular dependencies**: Follow unidirectional flow
4. **Don't put business logic in data layer**: Keep it in analysis
5. **Don't do I/O in analysis layer**: Use data layer
6. **Don't tightly couple**: Depend on abstractions (protocols)

---

## Troubleshooting

### "Where do I put this code?"

**Question**: "I need to load data from a file"
**Answer**: → Data Layer (`data/loader.py`)

**Question**: "I need to calculate a new metric"
**Answer**: → Metrics Layer (new calculator in `metrics/`)

**Question**: "I need to coordinate multiple operations"
**Answer**: → Service Layer (new service or extend existing)

**Question**: "I need business logic (not metrics)"
**Answer**: → Analysis Layer (`analysis/`)

### "How do I test component X?"

**Data Layer**:
```python
# Mock file system or use test fixtures
def test_loader(tmp_path):
    # Create test CSV
    test_file = tmp_path / "activities.csv"
    test_file.write_text("id,name\n1,Test")

    loader = ActivityDataLoader(settings)
    df = loader.load_activities()
    assert len(df) == 1
```

**Analysis Layer**:
```python
# Mock data layer, test logic
def test_analyzer():
    analyzer = ActivityAnalyzer(settings)
    metrics = analyzer.analyze(sample_activity, sample_stream)
    assert "normalized_power" in metrics
```

**Service Layer**:
```python
# Mock all dependencies, test orchestration
def test_service(mock_loader, mock_analyzer):
    service = ActivityService(settings)
    service.loader = mock_loader
    service.analyzer = mock_analyzer

    result = service.process_activity(activity)
    # Verify calls and orchestration
```

---

## Migration Guide

### From Old Code

**Before**:
```python
from strava_analyzer.pipeline import AnalysisPipeline
pipeline = AnalysisPipeline(settings)
pipeline.process()
```

**After (Recommended)**:
```python
from strava_analyzer.modern_pipeline import ModernPipeline
pipeline = ModernPipeline(settings)
pipeline.run()
```

**After (Using Services Directly)**:
```python
from strava_analyzer.services import AnalysisService
service = AnalysisService(settings)
enriched_df, summary = service.run_analysis()
```

---

## Summary

### Key Takeaways

1. **Layered Architecture**: 4 clear layers (service, analysis, data, metrics)
2. **Separation of Concerns**: Each layer has specific responsibility
3. **Testability**: Test each layer independently with mocks
4. **Flexibility**: Swap implementations via protocols
5. **Maintainability**: Clear organization, easy to find and modify code

### Quick Reference

| Need to... | Use... |
|------------|--------|
| Load data | `ActivityDataLoader` |
| Clean data | `StreamDataProcessor` |
| Query activities | `ActivityRepository` |
| Analyze activity | `ActivityAnalyzer` |
| Calculate metrics | `MetricsCalculator` |
| Process workflow | `ActivityService` |
| Run full analysis | `AnalysisService` |

---

**Document Version**: 1.0
**Date**: 2025-10-22
**Status**: Current
