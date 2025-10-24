# StravaAnalyzer Metrics Documentation

This document provides a detailed explanation of the various metrics calculated by the `StravaAnalyzer` package. These metrics are designed to help athletes and coaches gain deeper insights into performance, training load, and physiological adaptations from Strava activity data.

---

## Time-Weighted Averaging

**Important Note:** All metrics in StravaAnalyzer use **time-weighted averaging** instead of simple arithmetic means. This ensures accurate calculations regardless of variable sampling rates, recording gaps, or auto-pause periods.

### Why Time-Weighted Averaging?

Stream data from activity recordings is time-series data where:
- Each data point represents a measurement at a specific time
- Time intervals between points may vary (typically 1Hz but can have gaps)
- Auto-pause features create periods with no data
- GPS loss or device issues cause variable sampling rates

**Simple arithmetic mean** (incorrect):
```
Average Power = Σ(power_i) / n_points
```
This treats each data point equally, regardless of the time interval it represents.

**Time-weighted mean** (correct):
```
Average Power = Σ(power_i × Δt_i) / Σ(Δt_i)
```
Where `Δt_i` is the time interval between consecutive points. This properly weights each value by the duration it represents.

### Impact on Metrics

Time-weighted averaging affects:
- **Average Power**: Correctly accounts for recording gaps and variable sampling
- **Average Heart Rate**: Properly weights HR readings by duration
- **Normalized Power**: Fourth powers are time-weighted before taking fourth root
- **TSS/hrTSS**: Duration calculated from actual elapsed time, not data point count
- **Efficiency Factor**: Uses time-weighted averages for both power and HR
- **Variability Index**: Uses time-weighted average power

For more technical details, see `docs/ADR_005_TIME_WEIGHTED_AVERAGING.md`.

---

## Raw vs. Moving Metrics

**All metrics are calculated twice:** once for **raw** data (includes all recorded data) and once for **moving** data (excludes stopped periods). This is indicated by prefixes:

- **`raw_`** prefix: Includes all data, including stopped periods (auto-pause, manual stops)
- **`moving_`** prefix: Excludes stopped periods, representing only actual moving time

### Gap Detection and Stopped Periods

The system automatically detects stopped periods using time gaps in the stream data:

1. **Gap Detection**: Time gaps > **2 seconds** (configurable via `TimeConstants.GAP_DETECTION_THRESHOLD`) indicate stopped periods where the device auto-paused or stopped recording
2. **Boundary Marking**: The data point immediately after a gap is marked as `moving=False` (typically shows 0W/0 velocity)
3. **Raw Metrics**: Include all data points with their actual time deltas, so gaps contribute `0W × large_time_delta` to time-weighted averages
4. **Moving Metrics**: Filter out stopped points AND clip any resulting time deltas >2s to prevent gaps from affecting calculations

### Example: Activity with Stops

For an activity with auto-pause:
- **Total elapsed time**: 5466s (includes 510s of gaps from 6 stopped periods)
- **Moving time**: 4956s (actual riding time)
- **Raw average power**: 161.1W (time-weighted across all 5466s)
- **Moving average power**: 177.5W (time-weighted across only 4956s of movement)

The moving metrics are **power-meter agnostic** - they work based purely on time gaps, regardless of whether power, heart rate, or other sensors are present.

### Metrics Available in Both Variants

All primary metrics have both `raw_` and `moving_` versions:
- Average power, normalized power, intensity factor, TSS
- Average heart rate, max heart rate, hrTSS
- Efficiency factor, variability index, decoupling
- All zone distributions (power, HR, cadence, speed, slope)
- Power per kg (derived from average power)
- First/second half efficiency factors (used in decoupling)

### Metrics Without Raw/Moving Variants

Some metrics represent absolute values or aggregate statistics that don't change based on moving state:
- Power profile (best efforts are absolute regardless of stops)
- Longitudinal metrics (CTL, ATL, TSB, ACWR) - calculated from daily TSS totals
- Activity metadata (distance, elevation gain, etc.)

---

## Cycling-Specific Metrics

### Average Power
- **Description:** The mean power output during the activity, properly time-weighted to account for variable sampling rates and recording gaps.
- **Variants:** `raw_average_power` (includes stopped periods) and `moving_average_power` (excludes stopped periods)
- **Calculation:** Time-weighted mean of power values: `Σ(power_i × Δt_i) / Σ(Δt_i)`. For moving metrics, stopped periods are filtered out and time deltas are clipped to prevent gaps from affecting the calculation.
- **Significance:** Fundamental power metric. Moving average power is typically higher than raw average power for activities with stops, as it represents the true riding intensity. Matches Strava's reported average power (which uses their own moving/elapsed time logic).

### Normalized Power (NP)
- **Description:** Normalized Power represents the power an athlete *could have* maintained for the same physiological cost if their power output had been perfectly constant. It accounts for the physiological impact of variations in power output (e.g., surges, coasting) which are more taxing than steady efforts.
- **Variants:** `raw_normalized_power` and `moving_normalized_power`
- **Calculation:** Calculated using a 30-second rolling average of power, raised to the fourth power, time-weighted averaged, and then the fourth root is taken.
- **Significance:** Provides a more accurate measure of the true physiological cost of a cycling workout compared to simple average power. Used in IF and TSS calculations.

### Intensity Factor (IF)
- **Description:** Intensity Factor is a measure of the intensity of a training session relative to an athlete's Functional Threshold Power (FTP).
- **Variants:** `raw_intensity_factor` and `moving_intensity_factor`
- **Calculation:** `IF = Normalized Power / FTP`
- **Significance:** Helps categorize the intensity of a workout (e.g., recovery, endurance, tempo, threshold, VO2max). An IF of 1.0 indicates an effort at FTP. Moving IF is typically higher than raw IF for activities with stops.

### Training Stress Score (TSS)
- **Description:** Training Stress Score quantifies the physiological stress and training load of a cycling workout. It combines duration and intensity into a single number.
- **Variants:** `raw_training_stress_score` and `moving_training_stress_score`
- **Calculation:** `TSS = (duration_in_seconds * Normalized Power * Intensity Factor) / (FTP * 3600) * 100`. Duration is calculated from actual elapsed time using time deltas, not data point count.
- **Significance:** Used for tracking training load over time, managing fatigue, and planning training cycles. Time-weighted duration ensures accurate TSS even with auto-pause or recording gaps. Raw TSS uses total elapsed time; moving TSS uses only moving time.

### Average Heart Rate
- **Description:** The average heart rate (beats per minute, bpm) recorded during the activity.
- **Variants:** `raw_average_hr` (entire activity) and `moving_average_hr` (excludes stopped periods)
- **Calculation:** Time-weighted mean of heart rate readings. For moving metrics, stopped periods are filtered out and time deltas are clipped.
- **Significance:** A basic indicator of cardiovascular effort. Time-weighted averaging ensures accurate values even with recording gaps. Moving average HR may be higher than raw average HR for activities with rest periods.

### Max Heart Rate
- **Description:** The maximum heart rate (bpm) recorded at any point during the activity.
- **Variants:** `raw_max_hr` and `moving_max_hr` (though typically these are the same)
- **Calculation:** Highest valid heart rate reading during the activity.
- **Significance:** Indicates peak cardiovascular exertion.

### Time in Heart Rate Zones
- **Description:** The percentage of time spent within predefined heart rate zones. These zones are typically set as percentages of Functional Threshold Heart Rate (FTHR).
- **Variants:** `raw_hr_z*_percentage` and `moving_hr_z*_percentage` (where * is zone 1-5)
- **Calculation:** Based on FTHR and configurable zone percentages. Time in each zone is calculated using time-weighted duration.
- **Significance:** Helps assess the physiological focus of a workout (e.g., endurance, tempo, threshold work). Moving percentages exclude stopped periods.

### Efficiency Factor (EF)
- **Description:** Efficiency Factor is the ratio of Normalized Power to average heart rate. It's a measure of aerobic efficiency.
- **Variants:** `raw_efficiency_factor` and `moving_efficiency_factor`
- **Calculation:** `EF = Normalized Power / Time-Weighted Average Heart Rate`. Both NP and average HR use time-weighted calculations.
- **Significance:** An increasing EF over time for similar efforts can indicate improved aerobic fitness. Time-weighted averaging ensures accurate EF even with variable data quality. Moving EF is typically more representative of actual riding efficiency.

### Power:Heart Rate Decoupling
- **Description:** Power:Heart Rate Decoupling measures the percentage change in the power-to-heart rate ratio from the first half to the second half of a steady-state effort. A significant decrease can indicate fatigue or dehydration.
- **Variants:** `raw_power_hr_decoupling` and `moving_power_hr_decoupling`
- **Calculation:** `((EF_second_half - EF_first_half) / EF_first_half) * 100`. Negative values indicate decoupling (fatigue).
- **Significance:** Useful for assessing endurance fitness and identifying signs of fatigue during long efforts. Requires minimum 1-hour duration for meaningful results.

### Variability Index (VI)
- **Description:** Variability Index is the ratio of Normalized Power to average power.
- **Variants:** `raw_variability_index` and `moving_variability_index`
- **Calculation:** `VI = Normalized Power / Time-Weighted Average Power`. Both NP and average power use time-weighted calculations.
- **Significance:** A VI close to 1.0 indicates a very steady effort (e.g., time trial), while a higher VI indicates a more variable effort (e.g., group ride with surges). Time-weighted averaging provides more accurate VI, especially for activities with variable pacing.

### Time in Power Zones
- **Description:** The percentage of time spent within predefined power zones based on FTP.
- **Variants:** `raw_power_z*_percentage` and `moving_power_z*_percentage` (where * is zone 1-7, following Coggan's 7-zone model)
- **Calculation:** Based on FTP and standard zone percentages. Time in each zone is calculated using time-weighted duration.
- **Zones:** Z1 (0-55% FTP), Z2 (56-75%), Z3 (76-90%), Z4 (91-105%), Z5 (106-120%), Z6 (121-150%), Z7 (>150%)
- **Significance:** Helps assess training intensity distribution and whether the workout targeted specific physiological adaptations.

### Power Profile
- **Description:** A collection of an athlete's best mean maximal power outputs for various durations (e.g., 5 seconds, 1 minute, 5 minutes, 20 minutes, 60 minutes).
- **Calculation:** Identifies the highest average power sustained for each specified duration within an activity. Uses rolling time-weighted averages.
- **Significance:** Helps characterize an athlete's strengths and weaknesses across different physiological systems (neuromuscular, anaerobic, aerobic). Not prefixed as it represents absolute best efforts.

---

## Running-Specific Metrics (from `running_metrics.py`)

### Functional Threshold Pace (FTPace)
- **Description:** Functional Threshold Pace is the fastest pace a runner can sustain for approximately 60 minutes in a race or maximal effort. It is analogous to FTP for cyclists.
- **Calculation:** Estimated from a 10-minute maximal mean velocity during a running activity, with an adjustment factor.
- **Significance:** A key metric for setting training paces and understanding a runner's aerobic capacity.

### Normalized Graded Pace (NGP)
- **Description:** Normalized Graded Pace is a measure of pace that accounts for the physiological cost of running on varied terrain (uphill and downhill). It provides a more accurate representation of effort than raw pace on undulating courses.
- **Calculation:** Adjusts raw pace based on grade (uphill slows pace, downhill speeds it up) using configurable factors, then applies a rolling average.
- **Significance:** Allows for more accurate comparison of efforts across different terrains and provides a better indicator of training stress.

### Running Training Stress Score (rTSS)
- **Description:** Running Training Stress Score quantifies the physiological stress and training load of a running workout, analogous to TSS for cycling. It uses Normalized Graded Pace (NGP) as its intensity metric.
- **Calculation:** `rTSS = (duration_in_hours * NGP_intensity^2) * 100`, where `NGP_intensity = Average NGP / FTPace`.
- **Significance:** Used for tracking running training load over time, managing fatigue, and planning training cycles.

### Heart Rate Training Stress Score (hrTSS)
- **Description:** Heart Rate Training Stress Score quantifies training load based on heart rate intensity relative to Functional Threshold Heart Rate (FTHR).
- **Variants:** `raw_hr_training_stress` and `moving_hr_training_stress`
- **Calculation:** `hrTSS = (duration_in_hours * HR_intensity^2) * 100`, where `HR_intensity = Time-Weighted Average HR / FTHR`. Duration is calculated from actual elapsed time using time deltas.
- **Significance:** Useful for estimating training load when power or pace data is unavailable or unreliable, or for understanding cardiovascular stress. Time-weighted duration ensures accurate hrTSS regardless of recording quality. Raw hrTSS uses total elapsed time; moving hrTSS uses only moving time.

---

## Longitudinal Metrics

These metrics track training load and fitness over time. They are calculated from daily TSS totals and do not have raw/moving variants (the TSS used can be either raw or moving depending on configuration).

### Chronic Training Load (CTL)
- **Description:** Chronic Training Load, often referred to as "Fitness," is a 42-day exponentially weighted moving average (EWMA) of daily Training Stress Score (TSS).
- **Calculation:** `CTL_today = CTL_yesterday + (TSS_today - CTL_yesterday) / CTL_DAYS` (where `CTL_DAYS` is typically 42, configurable via `TrainingLoadWindows.CTL_DAYS`)
- **Significance:** Represents an athlete's long-term training adaptation and aerobic fitness. A higher CTL generally indicates greater fitness. Takes approximately 6 weeks to build substantially.

### Acute Training Load (ATL)
- **Description:** Acute Training Load, often referred to as "Fatigue," is a 7-day exponentially weighted moving average (EWMA) of daily Training Stress Score (TSS).
- **Calculation:** `ATL_today = ATL_yesterday + (TSS_today - ATL_yesterday) / ATL_DAYS` (where `ATL_DAYS` is typically 7, configurable via `TrainingLoadWindows.ATL_DAYS`)
- **Significance:** Represents an athlete's short-term training load and accumulated fatigue. A higher ATL indicates greater recent training stress. Responds quickly to training changes.

### Training Stress Balance (TSB)
- **Description:** Training Stress Balance, often referred to as "Form" or "Readiness to Perform," is the difference between Chronic Training Load (CTL) and Acute Training Load (ATL).
- **Calculation:** `TSB = CTL - ATL`
- **Significance:**
  - Positive TSB (>15): Fresh, ready for peak performance
  - TSB near 0: Maintaining fitness
  - Negative TSB (-10 to -30): Productive training range
  - Very negative TSB (<-30): High fatigue, recovery needed

### Acute:Chronic Workload Ratio (ACWR)
- **Description:** The Acute:Chronic Workload Ratio is the ratio of Acute Training Load (ATL) to Chronic Training Load (CTL). It is used to monitor injury risk and training effectiveness.
- **Calculation:** `ACWR = ATL / CTL`
- **Significance:**
  - **0.8-1.3**: "Sweet spot" for optimal training adaptation and reduced injury risk
  - **<0.8**: Undertraining, detraining risk
  - **>1.3**: High injury risk or overtraining
  - Thresholds defined in `TrainingStatusThresholds` constants

### Rolling Efficiency Factor Averages
- **Description:** Long-term rolling averages of Efficiency Factor to track aerobic fitness trends
- **Calculation:**
  - **4-week (28-day) EF average**: Rolling mean of EF over the past 28 days
  - **52-week (364-day) EF average**: Rolling mean of EF over the past year
- **Variants:** Calculated for both `raw_ef` and `moving_ef`
- **Significance:**
  - Increasing trends indicate improving aerobic fitness
  - Decreasing trends may indicate fatigue or need for recovery
  - Compare current EF to rolling averages to assess current form
- **Usage:** Available in longitudinal summaries via `ActivitySummarizer.calculate_rolling_ef()`

---

## Training Intensity Distribution (TID) Metrics

These metrics analyze how training time is distributed across intensity zones, which is critical for understanding training polarization and ensuring appropriate intensity balance.

### 3-Zone TID Model

Both power and heart rate use a simplified 3-zone model optimized for TID analysis:

**Power-Based TID:**
- **Zone 1 (Low)**: < 76% FTP (combines traditional Z1 + Z2)
- **Zone 2 (Moderate)**: 76-90% FTP (traditional Z3)
- **Zone 3 (High)**: > 90% FTP (combines traditional Z4-Z7)

**Heart Rate-Based TID:**
- **Zone 1 (Low)**: < 82% FTHR (traditional Z1)
- **Zone 2 (Moderate)**: 82-94% FTHR (traditional Z2 + Z3)
- **Zone 3 (High)**: > 94% FTHR (traditional Z4 + Z5)

### TID Zone Percentages
- **Metrics:**
  - `power_tid_z1_percentage`, `power_tid_z2_percentage`, `power_tid_z3_percentage`
  - `hr_tid_z1_percentage`, `hr_tid_z2_percentage`, `hr_tid_z3_percentage`
- **Description:** Percentage of activity time spent in each TID zone
- **Variants:** Both `raw_` and `moving_` prefixed versions
- **Calculation:** `(time_in_zone / total_time) × 100`

### Polarization Index (PI)
- **Metrics:** `power_polarization_index`, `hr_polarization_index`
- **Formula:** `PI = (Z1% + Z3%) / Z2%`
- **Variants:** Both `raw_` and `moving_` prefixed versions
- **Significance:**
  - **Higher values** indicate more polarized training (more time at extremes, less at moderate)
  - **PI > 4.0**: Highly polarized (ideal for endurance training)
  - **PI = 2-4**: Moderately polarized
  - **PI < 2**: Pyramidal or threshold-focused training

### Training Distribution Ratio (TDR)
- **Metrics:** `power_tdr`, `hr_tdr`
- **Formula:** `TDR = Z1% / Z3%`
- **Variants:** Both `raw_` and `moving_` prefixed versions
- **Significance:**
  - **TDR > 2.0**: Polarized training (recommended for endurance athletes)
  - **TDR = 1-2**: Balanced training
  - **TDR < 1**: High-intensity focused (typical for shorter events)

### Weekly TID Aggregation
- **Metrics:** `weekly_power_tid_z{1,2,3}_percentage`, `weekly_hr_tid_z{1,2,3}_percentage`
- **Description:** Time-weighted aggregation of TID across multiple activities in a week
- **Usage:** Call `TIDCalculator.calculate_weekly_tid(activities_df)` on a weekly group
- **Significance:** More accurate TID assessment than single activities

---

## Fatigue Resistance Metrics

These metrics quantify an athlete's ability to sustain power output over time, indicating fatigue resistance and pacing strategy effectiveness.

### Fatigue Index
- **Metric:** `fatigue_index`
- **Formula:** `FI = ((Initial_5min_power - Final_5min_power) / Initial_5min_power) × 100`
- **Variants:** Both `raw_` and `moving_` prefixed versions
- **Calculation Details:**
  - Compares first 5 minutes of power to last 5 minutes
  - Only calculated for activities > 1 hour
  - Excludes zero and very low power values
- **Significance:**
  - **0-5%**: Excellent pacing, minimal fatigue
  - **5-15%**: Good pacing, normal fatigue
  - **15-25%**: Moderate fatigue, possible pacing issues
  - **>25%**: High fatigue or poor pacing strategy
- **Related metrics:** `initial_5min_power`, `final_5min_power`

### Power Drop Percentage
- **Metric:** `power_drop_percentage`
- **Formula:** `((First_half_power - Second_half_power) / First_half_power) × 100`
- **Variants:** Both `raw_` and `moving_` prefixed versions
- **Description:** Percentage decrease in power from first half to second half of activity
- **Significance:**
  - **< 5%**: Excellent sustainability
  - **5-10%**: Good sustainability
  - **10-20%**: Moderate fade
  - **> 20%**: Significant power decay
- **Related metrics:** `first_half_power`, `second_half_power`, `half_power_ratio`

### Power Sustainability Index (PSI)
- **Metric:** `power_sustainability_index`
- **Formula:** `PSI = max(0, 100 - CV)` where `CV = (std_power / mean_power) × 100`
- **Variants:** Both `raw_` and `moving_` prefixed versions
- **Calculation:** Based on coefficient of variation of power output
- **Significance:**
  - **> 80**: Very sustainable, steady power
  - **60-80**: Good sustainability
  - **40-60**: Moderate variability
  - **< 40**: High variability, inconsistent pacing
- **Related metrics:** `power_coefficient_variation`

### Interval Fatigue Analysis
- **Metrics:** `interval_{duration}s_decay_rate`, `interval_{duration}s_power_trend`
- **Description:** Analyzes power decay across equal-duration intervals (default 300s = 5min)
- **Usage:** Call `FatigueCalculator.calculate_interval_fatigue(df, interval_duration=300)`
- **Significance:**
  - Decay rate shows percentage drop from first to last interval
  - Power trend (slope) indicates rate of power decline
  - Useful for structured workouts with repeated intervals

---

## Configuration and Constants

All thresholds, zone boundaries, and calculation parameters are defined in `src/strava_analyzer/constants.py` for easy customization:

### Key Constants

- **Gap Detection**: `TimeConstants.GAP_DETECTION_THRESHOLD = 2.0` seconds - threshold for detecting stopped periods
- **Rolling Windows**:
  - Normalized Power: 30 seconds
  - FTP Estimation: 20 minutes (1200s)
  - Decoupling Analysis: 1 hour minimum (3600s)
- **Training Load Windows**:
  - ATL: 7 days
  - CTL: 42 days
- **Power Zones**: Coggan 7-zone model (percentages of FTP)
- **Heart Rate Zones**: 5-zone model (percentages of FTHR)
- **Validation Thresholds**: Min/max values for power, HR, cadence, velocity

For complete details, see `src/strava_analyzer/constants.py` and `docs/ADR_005_TIME_WEIGHTED_AVERAGING.md`.

---


