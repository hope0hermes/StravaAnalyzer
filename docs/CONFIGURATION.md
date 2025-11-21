# Configuration Guide

StravaAnalyzer uses a settings system based on Pydantic for type-safe configuration.

## Configuration Methods

Configuration can be provided via (in order of precedence):

1. **Environment variables** (prefix with `STRAVA_ANALYZER_`)
2. **`.env` file** in the project root
3. **Direct instantiation** with custom values

## Minimal Configuration

Create a `.env` file in your project root:

```bash
# Required: Path to your Strava data
STRAVA_ANALYZER_DATA_DIR=/path/to/your/strava/export
STRAVA_ANALYZER_ACTIVITIES_FILE=/path/to/activities.csv
STRAVA_ANALYZER_STREAMS_DIR=/path/to/Streams

# Athlete-specific thresholds
STRAVA_ANALYZER_FTP=285.0           # Functional Threshold Power (watts)
STRAVA_ANALYZER_FTHR=170            # Functional Threshold Heart Rate (bpm)
STRAVA_ANALYZER_RIDER_WEIGHT_KG=70.0
```

## Advanced Configuration

For fine-tuned control, create a custom settings instance:

```python
from pathlib import Path
from strava_analyzer.settings import Settings

settings = Settings(
    # Data paths
    data_dir=Path("~/strava_data").expanduser(),
    activities_file=Path("~/strava_data/activities.csv").expanduser(),
    streams_dir=Path("~/strava_data/Streams").expanduser(),

    # Athlete thresholds
    ftp=285.0,
    fthr=170,
    rider_weight_kg=70.0,

    # Training load windows (optional - defaults shown)
    atl_days=7,   # Acute Training Load window
    ctl_days=42,  # Chronic Training Load window

    # FTP estimation factor (optional)
    ftp_rolling_window_days=42,  # Days to look back for FTP estimation
)
```

## Configuration Options

| Parameter | Description | Default | Type |
|-----------|-------------|---------|------|
| `ftp` | Functional Threshold Power (watts) | 285.0 | float |
| `fthr` | Functional Threshold Heart Rate (bpm) | 170 | int |
| `rider_weight_kg` | Athlete weight for power/kg calculations | 70.0 | float |
| `atl_days` | Acute Training Load window | 7 | int |
| `ctl_days` | Chronic Training Load window | 42 | int |
| `ftp_rolling_window_days` | FTP estimation lookback period | 42 | int |
| `data_dir` | Base data directory | `./data` | Path |
| `activities_file` | Path to activities CSV | `data_dir/activities.csv` | Path |
| `streams_dir` | Path to streams directory | `data_dir/Streams` | Path |
| `processed_data_dir` | Output directory for results | `./processed_data` | Path |

## Configuration File (YAML)

You can also use a YAML configuration file:

```yaml
# config.yaml
data_dir: /path/to/strava/export
activities_file: /path/to/activities.csv
streams_dir: /path/to/Streams

# Athlete thresholds
ftp: 285.0
fthr: 170
rider_weight_kg: 70.0

# Training load windows
atl_days: 7
ctl_days: 42
ftp_rolling_window_days: 42

# Output
processed_data_dir: ./results
```

Load with:

```python
from strava_analyzer.settings import load_settings
settings = load_settings("config.yaml")
```

## Environment Variables

All settings can be set via environment variables with the `STRAVA_ANALYZER_` prefix:

```bash
export STRAVA_ANALYZER_FTP=290
export STRAVA_ANALYZER_FTHR=175
export STRAVA_ANALYZER_RIDER_WEIGHT_KG=75
export STRAVA_ANALYZER_DATA_DIR=/my/strava/data
```

## Getting Your Strava Data

1. Log into your Strava account
2. Go to Settings → My Account → Download or Delete Your Account
3. Request your data export
4. Extract the archive and set:
   - `activities_file` to `activities.csv`
   - `streams_dir` to the `Streams/` directory

## Advanced Topics

### Time Windows

- **ATL (Acute Training Load)**: Recent stress indicator (default 7 days)
- **CTL (Chronic Training Load)**: Fitness indicator (default 42 days)

Adjust based on your sport:
- Endurance athletes: Consider longer windows (52 days)
- Shorter duration athletes: May use shorter windows

### FTP/FTHR Estimation

The tool can estimate FTP from 20-minute efforts and FTHR from threshold activities:

```python
settings = Settings(
    ftp_rolling_window_days=42  # Look back 42 days for estimation
)
```

See source code in `src/strava_analyzer/settings.py` for all available options.
