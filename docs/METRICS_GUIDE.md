# Metrics Guide

Detailed reference for all metrics calculated by StravaAnalyzer.

## Metric System: Raw vs. Moving

**Every metric is calculated twice:**

- **`raw_*` metrics**: Include all recorded data, including stopped periods
  - Example: `raw_average_power` = total power / total time (including stops)
  - Use for: Total energy expenditure, matching Strava's reported values

- **`moving_*` metrics**: Exclude stopped periods (auto-pause, traffic lights, etc.)
  - Example: `moving_average_power` = power when pedaling / moving time
  - Use for: True performance assessment, intensity analysis

**Why both?** A coffee stop doesn't reduce your fitness, but it does reduce total work. Both perspectives matter!

## Per-Activity Metrics

### Power Metrics (Cycling)

| Metric | Formula | Meaning | Good Value |
|--------|---------|---------|------------|
| **Average Power** | Σ(power × Δt) / Σ(Δt) | Average watts output | Depends on FTP |
| **Normalized Power** | (Σ(power^4 × Δt) / Σ(Δt))^(1/4) | Physiological cost | Higher = harder |
| **Intensity Factor** | NP / FTP | Relative intensity | 0.5-0.6: Recovery, 0.7-0.85: Endurance, 0.9-1.05: Threshold, >1.05: VO2max+ |
| **Training Stress Score** | (duration × NP × IF) / (FTP × 3600) × 100 | Training load | 150+: Hard, 300+: Very hard |
| **Variability Index** | NP / Avg Power | Pacing consistency | 1.0-1.05: Steady, 1.05-1.15: Variable, >1.15: Very variable |
| **Power per kg** | Average Power / Body Weight | Relative intensity | Higher = stronger |
| **Critical Power** | Peak sustainable power | Performance metric | Sport-specific |

### Efficiency Metrics (Cycling)

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Efficiency Factor** | NP / Avg HR | Aerobic efficiency | Higher = fitter, Track trends |
| **Pw:HR Decoupling** | (EF 2nd half - EF 1st half) / EF 1st half × 100 | Aerobic stability | <5%: Excellent, 5-10%: Good, >10%: Drift |

### Running Metrics

- **Normalized Graded Pace** (NGP): Grade-adjusted pace
- **Running TSS** (rTSS): Training stress for running
- **HR Training Stress Score** (hrTSS): HR-based training load
- **Functional Threshold Pace** (FTPace): Estimated threshold

### Universal Metrics

- **Heart Rate**: Average, max, zones
- **Elevation**: Total gain, loss
- **Distance**: Total distance covered
- **Duration**: Total and moving time

## Longitudinal Metrics

### Training Load Management

| Metric | Window | Meaning | Optimal Range |
|--------|--------|---------|---------------|
| **ATL** (Acute) | 7 days | Recent fatigue | Varies by athlete |
| **CTL** (Chronic) | 42 days | Fitness level | Higher = fitter |
| **TSB** (Balance) | CTL - ATL | Readiness | +15 to +25: Peak, -10 to -30: Productive, <-30: Overreached |
| **ACWR** (Ratio) | ATL / CTL | Injury risk | 0.8-1.3: Safe, >1.3: High risk, <0.8: Detraining |

### Performance Trends

- Rolling averages for all key metrics
- 4-week and 52-week Efficiency Factor trends
- Power curve progression over time
- Zone distribution patterns

### Threshold Estimation

- Dynamic FTP estimation from 20-minute efforts
- FTHR estimation from threshold activities
- Rolling threshold updates (42-day window)

## Training Intensity Distribution (TID)

How your training is distributed across intensity zones.

### 3-Zone Model

- **Zone 1** (Low): <76% FTP or <82% FTHR → Easy aerobic
- **Zone 2** (Moderate): 76-90% FTP or 82-94% FTHR → Tempo
- **Zone 3** (High): >90% FTP or >94% FTHR → Threshold and above

### TID Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Polarization Index** | (Z1 + Z3) / Z2 | Training distribution | >4.0: Highly polarized (ideal), 2-4: Moderate, <2: Threshold-focused |
| **Training Distribution Ratio** | Z1 / Z3 | Easy vs hard split | >2.0: Polarized, 1-2: Balanced, <1: High-intensity |

## Fatigue Resistance

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Fatigue Index** | (First 5min - Last 5min) / First 5min × 100 | Power decay | 0-5%: Excellent, 5-15%: Good, 15-25%: Moderate, >25%: High |
| **Power Sustainability** | 100 - CV (Coeff. Variation) | Consistency | >80: Sustainable, 60-80: Good, <60: Variable |

## Advanced Features

### Dual Metric Calculation

Every metric computed twice:
- `raw_*`: Complete picture including stops
- `moving_*`: Actual performance excluding stops

### Gap Detection

Identifies stopped periods:
- 2-second threshold for detecting auto-pause/stops
- Proper handling of GPS gaps
- Prevents distortion of moving metrics

### Time-Weighted Averaging

Mathematically accurate calculations:
- Accounts for variable sampling rates
- Weights data by time intervals
- Handles recording gaps correctly

For details, see [ADR_002_TIME_WEIGHTED_AVERAGING.md](ADR_002_TIME_WEIGHTED_AVERAGING.md)

## See Also

- [METRICS.md](METRICS.md) - Complete metric definitions
- [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) - How metrics are calculated
- [ADR_001_LAYERED_ARCHITECTURE.md](ADR_001_LAYERED_ARCHITECTURE.md) - Architecture decisions
