# StravaAnalyzer 🚴‍♂️📊

A comprehensive Python package for analyzing Strava activity data with scientific rigor. Built for athletes, coaches, and data enthusiasts who want to go beyond basic metrics and gain deep insights into training load, performance trends, and physiological adaptations.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why StravaAnalyzer?

StravaAnalyzer transforms your raw Strava data into actionable insights using advanced sports science metrics. Unlike basic analysis tools, it provides:

- **Dual Metric System**: All metrics calculated for both raw data (complete activities) and moving data (excluding stops)
- **Time-Weighted Averaging**: Mathematically accurate calculations that account for variable sampling rates and recording gaps
- **Comprehensive Training Load**: ATL, CTL, TSB, and ACWR for optimizing training and preventing overtraining
- **Advanced Power Analysis**: Critical Power modeling, power curves, and fatigue resistance metrics
- **Training Intensity Distribution**: Analyze polarization and zone distribution for optimal training adaptation
- **Scientific Accuracy**: Based on established sports science methodologies (Coggan, Friel, Seiler)

---

---

## 🌟 Key Features

### Per-Activity Metrics

#### Cycling Metrics
- **Power Analysis**
  - Average and Normalized Power (NP)
  - Intensity Factor (IF) and Training Stress Score (TSS)
  - Power per kilogram
  - Variability Index (VI)
  - Power profile (5s to 2hr mean maximal power)
  - Critical Power (CP) and W' (anaerobic capacity)

- **Efficiency Metrics**
  - Efficiency Factor (EF): Power-to-heart rate ratio
  - Aerobic Decoupling: First-half vs second-half EF comparison
  - Fatigue resistance and power sustainability

- **Zone Distribution**
  - 7-zone Coggan power model
  - Time-in-zone percentages
  - Training Intensity Distribution (TID) analysis
  - Polarization metrics

#### Running Metrics
- Normalized Graded Pace (NGP): Grade-adjusted pace
- Running Training Stress Score (rTSS)
- Heart Rate Training Stress Score (hrTSS)
- Functional Threshold Pace (FTPace) estimation

#### Universal Metrics
- Heart rate metrics (average, max, zones)
- Training Intensity Distribution (power and HR-based)
- Fatigue resistance (fatigue index, power drop percentage)
- Elevation and distance analysis

### Longitudinal Analysis

- **Training Load Management**
  - **ATL** (Acute Training Load): 7-day fatigue indicator
  - **CTL** (Chronic Training Load): 42-day fitness indicator
  - **TSB** (Training Stress Balance): Readiness to perform
  - **ACWR** (Acute:Chronic Workload Ratio): Injury risk monitoring

- **Performance Trends**
  - Rolling averages for all key metrics
  - 4-week and 52-week Efficiency Factor trends
  - Power curve progression over time
  - Zone distribution patterns

- **Threshold Estimation**
  - Dynamic FTP estimation from 20-minute efforts
  - FTHR estimation from threshold activities
  - Rolling threshold updates (42-day window)

### Advanced Features

- **Dual Metric Calculation**: Every metric computed twice
  - `raw_*`: Includes all data (complete picture)
  - `moving_*`: Excludes stopped periods (actual performance)

- **Gap Detection**: Intelligent identification of stopped periods
  - 2-second threshold for detecting auto-pause/manual stops
  - Proper handling of large time gaps
  - Prevents distortion of moving metrics

- **Time-Weighted Averaging**: Mathematically accurate calculations
  - Accounts for variable sampling rates
  - Properly weights data by time intervals
  - Handles recording gaps correctly

---

---

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- Strava data export (activities.csv and Streams/ directory)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/hope0hermes/StravaAnalyzer.git
cd StravaAnalyzer
```

2. **Create and activate a virtual environment** (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install the package**
```bash
pip install -e .
```

For development with testing and linting tools:
```bash
pip install -e ".[dev]"
```

For visualization and dashboard support (Jupyter, Plotly, Folium):
```bash
pip install -e ".[viz]"
```

### Getting Your Strava Data

1. Log into your Strava account
2. Go to Settings → My Account → Download or Delete Your Account
3. Request your data export
4. Extract the archive - you'll need:
   - `activities.csv`: Activity metadata
   - `Streams/` directory: Detailed time-series data for each activity

---

---

## ⚙️ Configuration

StravaAnalyzer uses a settings system based on Pydantic for type-safe configuration. You can configure it via:

1. **Environment variables** (prefix with `STRAVA_ANALYZER_`)
2. **`.env` file** in the project root
3. **Direct instantiation** with custom values

### Minimal Configuration

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

### Advanced Configuration

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

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ftp` | Functional Threshold Power (watts) | 285.0 |
| `fthr` | Functional Threshold Heart Rate (bpm) | 170 |
| `rider_weight_kg` | Athlete weight for power/kg calculations | 70.0 |
| `atl_days` | Acute Training Load window | 7 |
| `ctl_days` | Chronic Training Load window | 42 |
| `ftp_rolling_window_days` | FTP estimation lookback period | 42 |

See `src/strava_analyzer/settings.py` for all available options.

---

---

## 🚀 Quick Start

### Option 1: Pipeline (Simplest)

The easiest way to analyze your activities:

```python
from strava_analyzer.modern_pipeline import ModernPipeline
from strava_analyzer.settings import Settings

# Initialize with your settings
settings = Settings()
pipeline = ModernPipeline(settings)

# Run complete analysis
pipeline.run()

print("✅ Analysis complete! Check your processed_data directory.")
```

This will:
1. Load all activities from `activities.csv`
2. Process each activity's stream data
3. Calculate all metrics (power, HR, efficiency, zones, TID, fatigue)
4. Compute longitudinal metrics (ATL, CTL, TSB, ACWR)
5. Save enriched activities to `activities_enriched.csv`
6. Generate summary statistics

### Option 2: Service-Based Workflow (More Control)

For more control over the analysis process:

```python
from strava_analyzer.services import AnalysisService
from strava_analyzer.settings import Settings

# Initialize service
settings = Settings()
service = AnalysisService(settings)

# Run analysis
enriched_df, summary = service.run_analysis()

# Access results
print(f"Processed {len(enriched_df)} activities")
print(f"Current CTL: {summary.training_load.chronic_training_load:.1f}")
print(f"Current TSB: {summary.training_load.training_stress_balance:.1f}")

# Save results
service.save_results(enriched_df, summary)
```

### Option 3: Process Single Activity

Analyze a specific activity:

```python
from strava_analyzer.services import ActivityService
from strava_analyzer.settings import Settings

settings = Settings()
service = ActivityService(settings)

# Process specific activity
activity_id = 15919936111
activity = service.get_activity(activity_id)

if service.activity_has_stream(activity_id):
    metrics, stream = service.process_activity(activity)

    # Access metrics
    print(f"Activity: {activity['name']}")
    print(f"Moving Average Power: {metrics['moving_average_power']:.1f}W")
    print(f"Normalized Power: {metrics['moving_normalized_power']:.1f}W")
    print(f"Training Stress Score: {metrics['moving_training_stress_score']:.1f}")
    print(f"Efficiency Factor: {metrics['moving_efficiency_factor']:.2f}")
```

### Option 4: Custom Analysis

Build your own workflow using individual components:

```python
from strava_analyzer.data import ActivityDataLoader, StreamDataProcessor
from strava_analyzer.analysis import ActivityAnalyzer
from strava_analyzer.settings import Settings

settings = Settings()
loader = ActivityDataLoader(settings)
processor = StreamDataProcessor(settings)
analyzer = ActivityAnalyzer(settings)

# Load activities
activities = loader.load_activities()

# Process first 10 activities
for idx, row in activities.head(10).iterrows():
    # Load stream data
    stream = loader.load_stream(row['id'])
    if stream is None:
        continue

    # Clean and process
    clean_stream = processor.process(stream)

    # Analyze
    metrics = analyzer.analyze(row, clean_stream)

    # Display results
    print(f"{row['name']}: {metrics.get('moving_normalized_power', 'N/A')} W")
```

---

## 📊 Understanding Key Metrics

### Raw vs. Moving Metrics

**Every metric is calculated twice** to give you the complete picture:

- **`raw_*` metrics**: Include all recorded data, including stopped periods
  - Example: `raw_average_power` = total power / total time (including stops)
  - Use for: Total energy expenditure, matching Strava's reported values

- **`moving_*` metrics**: Exclude stopped periods (auto-pause, traffic lights, etc.)
  - Example: `moving_average_power` = power when actually pedaling / moving time
  - Use for: True performance assessment, intensity analysis

**Why both?** A coffee stop doesn't reduce your cycling ability, but it does reduce total work done. Both perspectives matter!

### Power Metrics (Cycling)

| Metric | Formula | Meaning | Good Value |
|--------|---------|---------|------------|
| **Average Power** | Σ(power × Δt) / Σ(Δt) | Average watts output | Depends on FTP |
| **Normalized Power** | (Σ(power^4 × Δt) / Σ(Δt))^(1/4) | Physiological cost of effort | Higher = harder |
| **Intensity Factor** | NP / FTP | Relative intensity | 0.5-0.6: Recovery<br>0.7-0.85: Endurance<br>0.9-1.05: Threshold<br>>1.05: VO2max+ |
| **Training Stress Score** | (duration × NP × IF) / (FTP × 3600) × 100 | Training load | 150+ = Hard workout<br>300+ = Very hard |
| **Variability Index** | NP / Average Power | Pacing consistency | 1.0-1.05: Steady<br>1.05-1.15: Variable<br>>1.15: Very variable |

### Efficiency Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| **Efficiency Factor** | NP / Average HR | Aerobic efficiency | Higher = fitter<br>Track trends over time |
| **Pw:HR Decoupling** | (EF 2nd half - EF 1st half) / EF 1st half × 100 | Aerobic stability | <5%: Excellent<br>5-10%: Good<br>>10%: Significant drift |

### Training Load (Longitudinal)

| Metric | Window | Meaning | Optimal Range |
|--------|--------|---------|---------------|
| **ATL** (Fatigue) | 7 days | Recent training stress | Varies by athlete |
| **CTL** (Fitness) | 42 days | Long-term fitness | Higher = fitter |
| **TSB** (Form) | CTL - ATL | Readiness to perform | +15 to +25: Fresh/peak<br>-10 to -30: Training productively<br><-30: Overreached |
| **ACWR** | ATL / CTL | Injury risk indicator | 0.8-1.3: Safe zone<br>>1.3: High injury risk<br><0.8: Detraining |

### Training Intensity Distribution (TID)

Analyzes how your training time is distributed across intensity zones:

**3-Zone Model:**
- **Zone 1** (Low): <76% FTP or <82% FTHR - Easy aerobic
- **Zone 2** (Moderate): 76-90% FTP or 82-94% FTHR - Tempo
- **Zone 3** (High): >90% FTP or >94% FTHR - Threshold and above

**Polarization Index**: (Z1 + Z3) / Z2
- **>4.0**: Highly polarized (ideal for endurance)
- **2-4**: Moderately polarized
- **<2**: Pyramidal or threshold-focused

**Training Distribution Ratio**: Z1 / Z3
- **>2.0**: Polarized training (recommended for endurance)
- **1-2**: Balanced
- **<1**: High-intensity focused

### Fatigue Resistance

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Fatigue Index** | (Initial 5min - Final 5min) / Initial 5min × 100 | Power decay rate | 0-5%: Excellent<br>5-15%: Good<br>15-25%: Moderate<br>>25%: High fatigue |
| **Power Sustainability Index** | 100 - CV (Coefficient of Variation) | Pacing consistency | >80: Very sustainable<br>60-80: Good<br><60: High variability |

---

## 🏗️ Architecture

StravaAnalyzer follows a **layered architecture** for maintainability and testability:

```
┌─────────────────────────────────────┐
│   CLI / Pipeline (Entry Points)     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   SERVICE LAYER                     │
│   Orchestrate workflows             │
│   • ActivityService                 │
│   • AnalysisService                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   ANALYSIS LAYER                    │
│   Business logic & computations     │
│   • ActivityAnalyzer                │
│   • ActivitySummarizer              │
│   • ThresholdEstimator              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   DATA LAYER                        │
│   I/O & data preparation            │
│   • ActivityDataLoader              │
│   • StreamDataProcessor             │
│   • ActivityRepository              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   METRICS LAYER                     │
│   Domain calculations               │
│   • PowerCalculator                 │
│   • HeartRateCalculator             │
│   • EfficiencyCalculator            │
│   • TIDCalculator                   │
│   • FatigueCalculator               │
└─────────────────────────────────────┘
```

**Key Principles:**
- **Separation of Concerns**: Each layer has specific responsibilities
- **Dependency Rule**: Layers only depend on layers below them
- **Testability**: Each layer can be tested independently with mocks
- **Extensibility**: Easy to add new calculators, data sources, or services

See [`docs/ARCHITECTURE_GUIDE.md`](docs/ARCHITECTURE_GUIDE.md) for detailed documentation.

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [`METRICS.md`](docs/METRICS.md) | Complete metric definitions, formulas, and interpretations |
| [`ARCHITECTURE_GUIDE.md`](docs/ARCHITECTURE_GUIDE.md) | System architecture, components, and extension points |
| [`ADR_002_TIME_WEIGHTED_AVERAGING.md`](docs/ADR_002_TIME_WEIGHTED_AVERAGING.md) | Why and how time-weighted averaging works |
| [`ADR_001_LAYERED_ARCHITECTURE.md`](docs/ADR_001_LAYERED_ARCHITECTURE.md) | Architecture decision record |

### Key Concepts

#### Time-Weighted Averaging

StravaAnalyzer uses **time-weighted averaging** for mathematical accuracy:

**Why?** Activity data is time-series with:
- Variable sampling rates (typically 1Hz, but varies)
- Recording gaps (auto-pause, GPS loss)
- Different time intervals between points

**Simple mean (incorrect)**:
```python
average_power = sum(power) / count(power)  # Treats all points equally
```

**Time-weighted mean (correct)**:
```python
average_power = sum(power × Δt) / sum(Δt)  # Weights by time interval
```

This ensures accurate calculations regardless of recording gaps or variable sampling.

#### Gap Detection

Activities often have stopped periods:
- Auto-pause features
- Traffic lights
- Mechanical issues
- Rest periods

StravaAnalyzer detects gaps using a **2-second threshold**:
- Time difference >2s between consecutive points → stopped period
- These periods marked as `moving=False`
- Allows separate analysis of moving vs. complete activity

---

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=strava_analyzer

# Run specific test file
pytest tests/test_metrics.py

# Run with verbose output
pytest -v
```

### Testing Individual Components

```python
# Test new metrics implementation
python test_new_metrics.py

# Verify gap detection
python -c "
from strava_analyzer.data import ActivityDataLoader, StreamDataProcessor
from strava_analyzer.settings import Settings

settings = Settings()
loader = ActivityDataLoader(settings)
processor = StreamDataProcessor(settings)

stream = loader.load_stream(your_activity_id)
processed = processor.process(stream)

print(f'Total rows: {len(processed)}')
print(f'Moving rows: {processed[\"moving\"].sum()}')
print(f'Stopped rows: {(~processed[\"moving\"]).sum()}')
"
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Run tests**: `pytest`
5. **Run linting**: `ruff check .`
6. **Commit your changes**: `git commit -m 'Add amazing feature'`
7. **Push to the branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Code Style

This project uses:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pytest** for testing

Run quality checks:
```bash
# Format code
ruff format .

# Check for issues
ruff check .

# Type checking
mypy src/strava_analyzer

# Run all quality checks
pytest && ruff check . && mypy src/strava_analyzer
```

---

## 🛣️ Roadmap

### Planned Features

- [ ] **Web Dashboard**: Interactive visualizations using Plotly/Dash
- [ ] **Real-time Analysis**: API integration for automatic processing
- [ ] **Machine Learning**: Predictive models for FTP progression
- [ ] **Multi-Sport Support**: Swimming and multisport activities
- [ ] **Advanced CP Modeling**: W' balance tracking during activities
- [ ] **Comparative Analysis**: Compare activities, segments, or time periods
- [ ] **Training Plan Templates**: Prescriptive training recommendations

### Recently Added

- ✅ Training Intensity Distribution (TID) analysis
- ✅ Polarization and TDR metrics
- ✅ Fatigue resistance metrics (fatigue index, power sustainability)
- ✅ Rolling Efficiency Factor averages
- ✅ Time-weighted averaging for all metrics
- ✅ Dual metric system (raw + moving)
- ✅ Gap detection and handling

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

**Sports Science Methodologies:**
- **Dr. Andrew Coggan**: Normalized Power, Training Stress Score, Power Zones
- **Joe Friel**: Training Stress Balance, Periodization concepts
- **Dr. Stephen Seiler**: Polarized Training model
- **Allen & Coggan**: *Training and Racing with a Power Meter*

**Inspiration:**
- Strava's activity analysis
- TrainingPeaks' performance metrics
- Golden Cheetah's comprehensive analytics

**Community:**
- All contributors and users providing feedback
- Open-source Python data science ecosystem (pandas, numpy, scipy)

---

## 📧 Contact

- **Author**: Israel Barragan
- **Email**: abraham0vidal@gmail.com
- **GitHub**: [@hope0hermes](https://github.com/hope0hermes)
- **Issues**: [GitHub Issues](https://github.com/hope0hermes/StravaAnalyzer/issues)

---

## 🌟 Star History

If you find this project useful, please consider giving it a star ⭐ on GitHub!

---

**Happy Analyzing! 🚴‍♂️📈**
# Test
# Test fix
