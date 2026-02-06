# Quick Start Guide

This guide provides detailed examples for using StravaAnalyzer in different ways.

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/hope0hermes/StravaAnalyzer.git
cd StravaAnalyzer
```

2. **Create and activate a virtual environment**
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install the package**
```bash
uv sync
```

For development:
```bash
uv sync --group dev
```

For visualization support:
```bash
uv sync --group viz
```

## Usage Examples

### Option 1: Pipeline (Simplest)

The easiest way to analyze your activities:

```python
from strava_analyzer.pipeline import Pipeline
from strava_analyzer.settings import Settings

settings = Settings()
pipeline = Pipeline(settings)
pipeline.run()

print("✅ Analysis complete! Check your processed_data directory.")
```

This will:
1. Load all activities from `activities.csv`
2. Process each activity's stream data
3. Calculate all metrics
4. Compute longitudinal metrics (ATL, CTL, TSB, ACWR)
5. Save enriched activities to `activities_enriched.csv`

### Option 2: Service-Based Workflow

For more control:

```python
from strava_analyzer.services import AnalysisService
from strava_analyzer.settings import Settings

settings = Settings()
service = AnalysisService(settings)

enriched_df, summary = service.run_analysis()

print(f"Processed {len(enriched_df)} activities")
print(f"Current CTL: {summary.training_load.chronic_training_load:.1f}")
print(f"Current TSB: {summary.training_load.training_stress_balance:.1f}")

service.save_results(enriched_df, summary)
```

### Option 3: Process Single Activity

```python
from strava_analyzer.services import ActivityService
from strava_analyzer.settings import Settings

settings = Settings()
service = ActivityService(settings)

activity_id = 15919936111
activity = service.get_activity(activity_id)

if service.activity_has_stream(activity_id):
    metrics, stream = service.process_activity(activity)
    print(f"Activity: {activity['name']}")
    print(f"Normalized Power: {metrics['moving_normalized_power']:.1f}W")
    print(f"TSS: {metrics['moving_training_stress_score']:.1f}")
```

### Option 4: Custom Analysis

```python
from strava_analyzer.data import ActivityDataLoader, StreamDataProcessor
from strava_analyzer.analysis import ActivityAnalyzer
from strava_analyzer.settings import Settings

settings = Settings()
loader = ActivityDataLoader(settings)
processor = StreamDataProcessor(settings)
analyzer = ActivityAnalyzer(settings)

activities = loader.load_activities()

for idx, row in activities.head(10).iterrows():
    stream = loader.load_stream(row['id'])
    if stream is None:
        continue

    clean_stream = processor.process(stream)
    metrics = analyzer.analyze(row, clean_stream)
    print(f"{row['name']}: {metrics.get('moving_normalized_power', 'N/A')} W")
```

### Option 5: Command-Line Interface

```bash
# Basic usage
uv run strava-analyzer run

# With configuration file
uv run strava-analyzer run --config config.yaml

# Verbose output
uv run strava-analyzer run --verbose

# Override paths
uv run strava-analyzer run \
  --activities /path/to/activities.csv \
  --streams-dir /path/to/Streams

# Force reprocessing
uv run strava-analyzer run --force
```

**Output files:**
- `activities_enriched.csv`: All activities with metrics
- `summary.json`: Summary statistics
- `analysis_log.txt`: Processing log

## Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options.

## Getting Your Strava Data

1. Log into your Strava account
2. Go to Settings → My Account → Download or Delete Your Account
3. Request your data export
4. Extract and you'll have:
   - `activities.csv`: Activity metadata
   - `Streams/` directory: Time-series data for each activity

## Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=strava_analyzer

# Specific file
uv run pytest tests/test_metrics.py

# Verbose
uv run pytest -v
```

## Next Steps

- Read [METRICS.md](METRICS.md) to understand metric calculations
- Check [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) for system design
- See [ADR_002_TIME_WEIGHTED_AVERAGING.md](ADR_002_TIME_WEIGHTED_AVERAGING.md) for accuracy details
