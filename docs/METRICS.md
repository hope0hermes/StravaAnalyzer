# StravaAnalyzer Metrics Documentation

Complete reference for all metrics calculated by StravaAnalyzer. This document covers metric definitions, interpretation guidelines, calculation methods, and physiological significance.

**Last Updated:** December 21, 2025
**Scope:** All per-activity and longitudinal metrics, including 11 new advanced/climbing metrics

---

## Quick Start: The Metric System

**Two metrics for every metric:**
- **`raw_*` metrics**: Include all recorded data (stops, traffic lights, etc.)
- **`moving_*` metrics**: Exclude stopped periods, representing true riding intensity

Why both? A coffee stop doesn't improve your fitness but does reduce total work. Both perspectives matter!

**Example:**
```
Activity: 1-hour ride with 10-minute stop
- raw_average_power = 150W (total work / total time, including stop)
- moving_average_power = 165W (total work / riding time only)
- raw_tss = 80 (TSS including the stop)
- moving_tss = 90 (TSS only from riding)
```

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

## Training Load Metrics

Training load metrics quantify cumulative training stress over time, helping coaches and athletes optimize training plans while managing injury risk.

### Time-Weighted Training Decay

Unlike simple daily TSS summation, StravaAnalyzer uses **exponential decay** based on actual calendar days:

```
decay_factor = exp(-days_elapsed / time_constant)
```

Where:
- `days_elapsed`: Actual calendar days between activities
- `time_constant`: CTL uses 42 days, ATL uses 7 days
- Result: Activities older than the time constant fade exponentially

**Why this matters:**
- Accounts for natural fitness decay when not training
- Gaps in training don't create artificial spikes
- More physiologically accurate than simple moving averages
- Each activity's time-of-day doesn't matter, only the calendar date

### Chronic Training Load (CTL)

- **Metric**: `chronic_training_load`
- **Time Constant**: 42 days
- **Description**: Cumulative training load representing fitness level
- **Calculation**: Time-weighted exponential average of daily TSS over 42 days
- **Variants**: `raw_` and `moving_` versions in longitudinal summary
- **Interpretation**:
  - **Low (< 50)**: Detraining, recovery phase
  - **Moderate (50-100)**: Base fitness, sustainable long-term training
  - **High (> 100)**: Peak fitness, may indicate overtraining risk if combined with high ATL

### Acute Training Load (ATL)

- **Metric**: `acute_training_load`
- **Time Constant**: 7 days
- **Description**: Recent training stress representing fatigue level
- **Calculation**: Time-weighted exponential average of daily TSS over 7 days
- **Variants**: `raw_` and `moving_` versions in longitudinal summary
- **Interpretation**:
  - **Low (< 30)**: Well recovered
  - **Moderate (30-60)**: Normal fatigue from recent training
  - **High (> 60)**: Significant fatigue, may need recovery

### Training Stress Balance (TSB)

- **Metric**: `training_stress_balance`
- **Formula**: `TSB = CTL - ATL`
- **Description**: Instantaneous indicator of training readiness
- **Variants**: `raw_` and `moving_` versions in longitudinal summary
- **Interpretation**:
  - **> 15**: Fresh and ready for hard efforts (positive TSB)
  - **(-10) to 15**: Productive training zone
  - **(-30) to (-10)**: Fatigued but productive
  - **< -30**: Highly fatigued, needs recovery
- **Optimal Range**: -30 to -10 for peak performance (slight fatigue with high fitness)

### Acute:Chronic Workload Ratio (ACWR)

- **Metric**: `acwr`
- **Formula**: `ACWR = ATL / CTL` (or 0 if CTL is 0)
- **Description**: Ratio of recent stress to overall fitness, key injury risk indicator
- **Variants**: `raw_` and `moving_` versions in longitudinal summary
- **Interpretation**:
  - **< 0.8**: Undertraining, insufficient stimulus
  - **0.8-1.0**: Sweet spot for injury prevention and adaptation
  - **1.0-1.3**: Elevated injury risk, but acceptable with gradual progression
  - **> 1.3**: High injury risk, rapid load increase not tolerated
  - **> 1.5**: Severe overtraining risk

### Training Status

- **Method**: Automatic classification based on TSB and ACWR
- **Possible States**:
  - **Fresh - Ready for Performance**: High CTL, low ATL, positive TSB
  - **Productive Training**: Optimal fatigue-to-fitness ratio
  - **High Fatigue - Recovery Needed**: Low TSB (< -30)
  - **Undertraining**: Low ACWR (< 0.8)
  - **High Risk - Reduce Load**: High ACWR (> 1.3)
  - **Maintenance**: Stable state with balanced load

### Per-Activity Training Load State

**Important:** Each activity record in the enriched CSV includes its own `chronic_training_load`, `acute_training_load`, `training_stress_balance`, and `acwr` values representing the training state **as of that activity's date**.

- **Computation**: Based on all activities up to and including that date
- **Window**: Uses actual calendar days (not row-based)
- **Stability**: Same TSB across multiple activities on the same day
- **Decay**: Activities older than 42 days have minimal CTL contribution

**Example:**
```
Activity 1: 2025-01-01, CTL=50, ATL=40, TSB=+10
Activity 2: 2025-01-02, CTL=51, ATL=38, TSB=+13  (newer activity, ATL decayed 1 day)
Activity 3: 2025-02-20, CTL=52, ATL=35, TSB=+17  (50 days later, ATL decayed significantly)
```

---

## Power Profile Metrics (Rolling 90-Day Window)

Critical Power (CP) and W' (W-prime) model the power-duration relationship, enabling predictions of time-to-exhaustion and power capabilities.

### Critical Power (CP)

- **Metric**: `cp`
- **Units**: Watts (W)
- **Description**: Estimate of the maximum power an athlete can sustain indefinitely
- **Calculation**: Hyperbolic model fit to maximum mean powers over 90 calendar days: `P(t) = CP + W'/t`
- **Variants**: Both `raw_` and `moving_` versions available
- **Window**: 90-day rolling lookback (calendar days, not row count)
- **Update**: Recalculated each activity; changes when new peak efforts enter or old ones exit window
- **Interpretation**:
  - **Typical values**: 200-400W for trained cyclists
  - **Temporal changes**: Rising CP indicates improving fitness; declining CP indicates detraining
  - **Stability**: Remains constant if no new records are established in the window

### W' (Anaerobic Work Capacity)

- **Metric**: `w_prime`
- **Units**: Joules (J)
- **Description**: Finite work capacity above critical power; energy available for anaerobic efforts
- **Calculation**: Fitted from hyperbolic model to maximum mean powers
- **Variants**: Both `raw_` and `moving_` versions available
- **Window**: 90-day rolling lookback
- **Interpretation**:
  - **Typical values**: 1000-3000J for trained cyclists
  - **Physiological meaning**: Energy available from anaerobic metabolism before exhaustion
  - **Fatigue indicator**: Declining W' despite stable CP may indicate overtraining

### CP Model Fit Quality

- **Metric**: `cp_r_squared`
- **Range**: 0.0 to 1.0
- **Description**: R² (coefficient of determination) of the power-duration curve fit
- **Interpretation**:
  - **> 0.9**: Excellent fit, reliable CP estimate
  - **0.75-0.9**: Good fit, usable CP estimate
  - **0.6-0.75**: Moderate fit, caution advised
  - **< 0.6**: Poor fit, may indicate insufficient data quality or irregular power distribution

### Anaerobic Energy Index (AEI)

- **Metric**: `aei`
- **Units**: Joules per kilogram (J/kg)
- **Formula**: `AEI = W' / body_weight_kg`
- **Description**: Normalized anaerobic capacity, accounting for athlete body weight
- **Variants**: Both `raw_` and `moving_` versions available
- **Requires**: `rider_weight_kg` in configuration
- **Interpretation**:
  - **Typical values**: 15-35 J/kg for trained cyclists
  - **Weight comparison**: Allows fair comparison between athletes of different sizes
  - **Advantages**: AEI is more stable than absolute W' when tracking body composition changes
  - **Normalization**: Similar to power-to-weight (W/kg) but for anaerobic capacity

---

## NEW: Advanced Power Metrics

### Time Above 90% FTP

- **Metric**: `time_above_90_ftp` / `moving_time_above_90_ftp`
- **Units**: Seconds
- **Description**: Total time spent above 90% of FTP (VO2max zone)
- **Calculation**: Counts seconds where `power > 0.9 × FTP`
- **Significance**: Measures specific VO2max stimulus time
- **Interpretation**:
  - **0-5 min**: Recovery/endurance ride
  - **5-15 min**: Moderate VO2max stimulus
  - **15-30 min**: Significant VO2max work
  - **>30 min**: Very hard VO2max session

### Sweet Spot Time

- **Metric**: `time_sweet_spot` / `moving_time_sweet_spot`
- **Units**: Seconds
- **Description**: Time in sweet spot range (88-94% of FTP)
- **Calculation**: Counts seconds where `0.88 × FTP <= power <= 0.94 × FTP`
- **Significance**: Optimal training intensity for FTP development
- **Interpretation**:
  - **0-20 min**: Minimal sweet spot work
  - **20-60 min**: Good sweet spot volume
  - **60-120 min**: Long sweet spot session
  - **>120 min**: Extended sweet spot endurance

### W' Balance Minimum

- **Metric**: `w_prime_balance_min` / `moving_w_prime_balance_min`
- **Units**: Joules (J)
- **Description**: Minimum W' balance reached during ride (lowest point)
- **Calculation**: Tracks W' depletion/recovery using Skiba model, records minimum
- **Requires**: CP and W' values from settings or prior computation
- **Significance**: Shows how close you came to total anaerobic exhaustion
- **Interpretation**:
  - **>50% W'**: Easy ride, minimal anaerobic stress
  - **25-50% W'**: Moderate anaerobic demands
  - **10-25% W'**: High anaerobic stress
  - **<10% W'**: Near complete depletion (matches, sprints)

### Match Burn Count

- **Metric**: `match_burn_count` / `moving_match_burn_count`
- **Units**: Count (integer)
- **Description**: Number of significant W' expenditures (>50% depletion)
- **Calculation**: Counts how many times W' drops below 50% threshold
- **Requires**: CP and W' values
- **Significance**: Quantifies hard efforts/attacks during the ride
- **Interpretation**:
  - **0-2 matches**: Steady ride, few surges
  - **3-5 matches**: Typical interval workout or hilly ride
  - **6-10 matches**: Many hard efforts (crit, group ride)
  - **>10 matches**: Very dynamic ride (criterium racing)

### Negative Split Index

- **Metric**: `negative_split_index` / `moving_negative_split_index`
- **Units**: Ratio (dimensionless)
- **Description**: Pacing analysis comparing 2nd half NP to 1st half NP
- **Formula**: `negative_split_index = NP_second_half / NP_first_half`
- **Calculation**: Splits ride at midpoint, calculates NP for each half
- **Significance**: Shows whether you faded or built power through ride
- **Interpretation**:
  - **<0.95**: Strong negative split (built power)
  - **0.95-1.05**: Even pacing
  - **1.05-1.15**: Slight fade
  - **>1.15**: Significant fade (poor pacing or fatigue)

### Cardiac Drift

- **Metric**: `cardiac_drift` / `moving_cardiac_drift`
- **Units**: Percentage (%)
- **Description**: Efficiency Factor drift from 1st half to 2nd half
- **Formula**: `drift = ((EF_second - EF_first) / EF_first) × 100`
- **Calculation**: Splits ride at midpoint, calculates EF for each half, compares
- **Requires**: Both power and heart rate data (minimum 10 minutes)
- **Significance**: Indicator of cardiovascular fitness and aerobic efficiency
- **Interpretation**:
  - **>-3%**: Excellent aerobic fitness
  - **-3% to -5%**: Good fitness, well-hydrated
  - **-5% to -8%**: Moderate drift, possible dehydration
  - **<-8%**: Poor aerobic fitness or significant fatigue
- **Note**: Negative values indicate fatigue/dehydration (EF decreasing). Positive values (rare) indicate warm-up effect.

### Estimated FTP

- **Metric**: `estimated_ftp` / `moving_estimated_ftp`
- **Units**: Watts (W)
- **Description**: FTP estimate from best 20-minute power in this ride
- **Formula**: `estimated_ftp = best_20min_power × 0.95`
- **Calculation**: Finds best rolling 20-min average, applies 95% factor
- **Significance**: Can track FTP progression ride-to-ride
- **Interpretation**:
  - Compare to configured FTP to see if update needed
  - Rising estimates indicate improving fitness
  - Requires rides >20 minutes with sustained effort

---

## NEW: Climbing Metrics

### VAM (Velocità Ascensionale Media)

- **Metric**: `vam` / `moving_vam`
- **Units**: Meters per hour (m/h)
- **Description**: Vertical ascent rate - the gold standard for climbing performance
- **Formula**: `VAM = (total_elevation_gain / climbing_time) × 3600`
- **Calculation**: Sums positive elevation changes, divides by time spent climbing
- **Significance**: Power-independent climbing metric, used in pro cycling
- **Interpretation**:
  - **<800 m/h**: Recreational pace
  - **800-1000 m/h**: Strong amateur
  - **1000-1200 m/h**: Cat 2-3 racer
  - **1200-1400 m/h**: Cat 1 / Pro domestic
  - **1400-1600 m/h**: Pro continental
  - **>1600 m/h**: World Tour climber

### Climbing Time

- **Metric**: `climbing_time` / `moving_climbing_time`
- **Units**: Seconds
- **Description**: Total time spent climbing (positive gradient)
- **Calculation**: Counts seconds where altitude is increasing
- **Significance**: Quantifies climbing volume in the ride
- **Interpretation**:
  - Shows what % of ride was spent climbing
  - Useful for route characterization
  - Compare to flat/rolling rides

### Climbing Power

- **Metric**: `climbing_power` / `moving_climbing_power`
- **Units**: Watts (W)
- **Description**: Average power on significant climbs (gradients >4%)
- **Calculation**: Mean power where `gradient > 4%`
- **Requires**: Grade stream data and power meter
- **Significance**: Shows sustained climbing strength
- **Interpretation**:
  - Compare to overall average power
  - Higher climbing power = good at sustained efforts
  - Track improvements in climbing-specific power

### Climbing Power per Kilogram

- **Metric**: `climbing_power_per_kg` / `moving_climbing_power_per_kg`
- **Units**: Watts per kilogram (W/kg)
- **Description**: Weight-normalized climbing power
- **Formula**: `climbing_power_per_kg = climbing_power / rider_weight_kg`
- **Requires**: Configured rider weight
- **Significance**: THE key metric for climbing performance
- **Interpretation**:
  - **<3.0 W/kg**: Recreational
  - **3.0-3.5 W/kg**: Strong amateur
  - **3.5-4.0 W/kg**: Cat 2-3 racer
  - **4.0-4.5 W/kg**: Cat 1 / Pro domestic
  - **4.5-5.5 W/kg**: Pro continental
  - **>5.5 W/kg**: World Tour climber

---

### Power Curve (Maximum Mean Powers)

- **Metrics**: `power_curve_5sec`, `power_curve_10sec`, ..., `power_curve_1hr`
- **Description**: Maximum mean power sustained for each duration
- **Durations**: 5s, 10s, 15s, 20s, 30s, 1min, 2min, 5min, 10min, 15min, 20min, 30min, 1hr
- **Calculation**: Rolling maximum across all activities in the entire training history
- **Note**: These are **all-time** bests, not limited to 90-day window (unlike CP/W')
- **Interpretation**: Shows power profile shape and identifies weaknesses
  - **Weak 5min power**: May need more VO2max work
  - **Weak 1hr power**: May need FTP/threshold work

### CP Model Confidence

When fewer than 3 power-duration data points are available (e.g., very new athletes or limited power data), CP values will be `NaN` (not computed). This ensures reliability:

- **Need**: At least 3 different duration points with valid power data
- **Why**: Hyperbolic model requires minimum 3 points for meaningful fitting
- **Result**: Activities with `cp=NaN` still have other metrics; CP will populate once 90-day window accumulates enough data

### 90-Day Window Details

- **Type**: Calendar-day based, not row-based
- **Lookback**: Each activity looks back exactly 90 calendar days
- **Boundary**: Includes all activities from (activity_date - 90 days) to activity_date (inclusive)
- **Update Frequency**: Recalculated per activity; different activities on same day may have same CP if no new records
- **Staleness**: Activities older than 90 days have zero contribution to CP
- **Benefits**:
  - Captures current fitness level, not lifetime bests
  - Properly handles off-seasons with minimal distortion
  - Physiologically appropriate for tracking adaptations

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
  - CP Window: 90 days (90-day rolling window for Critical Power modeling)
- **Power Zones**: Coggan 7-zone model (percentages of FTP) or LT-based model if stress test thresholds provided
- **Heart Rate Zones**: 5-zone model (percentages of FTHR) or LT-based model if stress test thresholds provided
- **Validation Thresholds**: Min/max values for power, HR, cadence, velocity

For complete details, see `src/strava_analyzer/constants.py` and `docs/ADR_005_TIME_WEIGHTED_AVERAGING.md`.

---

## Implementation Details

### New Metrics (December 2025)

The following 11 new metrics were added to support enhanced dashboard analysis:

**Advanced Power Metrics (7):**
- Time Above 90% FTP
- Sweet Spot Time
- W' Balance Minimum
- Match Burn Count
- Negative Split Index
- Cardiac Drift
- Estimated FTP

**Climbing Metrics (4):**
- VAM (Velocità Ascensionale Media)
- Climbing Time
- Climbing Power
- Climbing Power per kg

All new metrics are:
- Available in both `raw_` and `moving_` variants
- Integrated into the main metrics pipeline
- Documented with interpretation guidelines
- Tested and validated with synthetic data

### Integration Points

**Calculator Modules:**
- `src/strava_analyzer/metrics/advanced_power.py` - AdvancedPowerCalculator
- `src/strava_analyzer/metrics/climbing.py` - ClimbingCalculator

**Pipeline Integration:**
- Both calculators initialized in `MetricsCalculator.__init__()`
- Automatically called in `compute_all_metrics()` for cycling activities
- Seamlessly integrated with existing metrics

**Requirements:**
- Advanced Power: FTP setting, power stream data
- Climbing: Altitude stream data, optional grade/power data
- Both: rider_weight_kg for normalized metrics

---

## Quick Reference Tables

### Metric Categories

| Category | Metric Count | Raw/Moving | Per-Activity |
|----------|--------------|-----------|--------------|
| Basic Power | 4 | ✓ | ✓ |
| Heart Rate | 3 | ✓ | ✓ |
| Efficiency | 3 | ✓ | ✓ |
| Training Load | 1 | ✓ | ✓ |
| Zones (Power) | 7 | ✓ | ✓ |
| Zones (HR) | 5 | ✓ | ✓ |
| TID Metrics | 6 | ✓ | ✓ |
| Fatigue Resistance | 3 | ✓ | ✓ |
| **Advanced Power (NEW)** | **7** | **✓** | **✓** |
| **Climbing (NEW)** | **4** | **✓** | **✓** |
| Longitudinal | 8 | - | ✓ |
| **Total** | **62** | **40** | **~54** |

### Configuration Checklist

For full functionality, configure these in `settings.yaml` or Settings object:

```yaml
ftp: 250                          # Required for power zones and all power metrics
rider_weight_kg: 70               # Required for W/kg calculations
lthr: 165                         # Required for HR zones
cp: null                          # Optional, computed from 90-day data
w_prime: null                     # Optional, computed from 90-day data
```

### Finding Metrics in Code

| Need | Location |
|------|----------|
| All metric names | `src/strava_analyzer/constants.py` - `METRIC_NAMES` |
| Calculator class | `src/strava_analyzer/metrics/` - `*_calculator.py` |
| New metrics source | `src/strava_analyzer/metrics/advanced_power.py` and `climbing.py` |
| Integration point | `src/strava_analyzer/metrics/calculators.py` - `MetricsCalculator.compute_all_metrics()` |
| Constants/thresholds | `src/strava_analyzer/constants.py` |

---

## Interpretation Quick Start

### Power Metrics

**Average Power vs Normalized Power:**
- Avg Power: Simple time-weighted mean
- NP: Accounts for intensity variations (harder to maintain variable power)
- NP is always ≥ Avg Power
- Use NP for TSS and training load

**Intensity Factor (IF):**
- IF = NP / FTP
- 0.5-0.6: Easy/recovery
- 0.75-0.85: Endurance
- 0.9-1.05: Threshold
- >1.05: VO2max and above

**Training Stress Score (TSS):**
- <100: Recoveryride
- 100-150: Moderate
- 150-300: Hard/workout
- >300: Very hard/racing

### New Advanced Metrics

**Time Above 90% FTP:**
- Measures VO2max training stimulus
- 0-5 min: Light session
- 5-15 min: Good stimulus
- 15-30 min: Significant workout
- >30 min: Hard VO2max session

**W' Balance Minimum:**
- Percentage of W' depleted
- >50%: Minimal anaerobic stress
- 10-50%: Moderate stress
- <10%: Severe depletion (matches/sprints)

**Cardiac Drift:**
- Power:HR change from 1st to 2nd half
- <3%: Excellent aerobic fitness
- 3-5%: Good fitness
- 5-8%: Moderate drift
- >8%: Poor fitness or significant fatigue

**VAM (Climbing):**
- <800 m/h: Recreational
- 800-1000 m/h: Strong amateur
- 1000-1200 m/h: Cat 2-3 racer
- 1200-1400 m/h: Cat 1 / Pro domestic
- >1600 m/h: World Tour climber

### Training Load (Longitudinal)

**ATL (Acute Training Load, 7-day window):**
- <30: Well recovered
- 30-60: Normal fatigue
- >60: High fatigue, consider recovery

**CTL (Chronic Training Load, 42-day window):**
- <50: Low fitness
- 50-100: Base fitness
- >100: Peak fitness

**TSB (Training Stress Balance = CTL - ATL):**
- >15: Fresh, ready for peak
- (-10) to 15: Productive training zone
- (-30) to (-10): Fatigued but productive
- <-30: Overreached, needs recovery

**ACWR (Acute:Chronic Ratio = ATL / CTL):**
- <0.8: Undertraining
- 0.8-1.3: Optimal
- >1.3: High injury risk

---

## File Locations

| What | Where |
|------|-------|
| This document | `docs/METRICS.md` |
| Metric calculator code | `src/strava_analyzer/metrics/` |
| Constants | `src/strava_analyzer/constants.py` |
| Implementation plan | `../dev_docs/DASHBOARD_METRICS_IMPLEMENTATION_PLAN.md` |
| Data structure spec | `../ActivitiesViewer/docs/DATA_STRUCTURE.md` |
| Architecture decisions | `docs/ADR_*.md` |

---

## Common Questions

**Q: Why do my raw and moving metrics differ?**
A: Stopped periods (traffic lights, coffee stops) are included in raw metrics but excluded from moving. Moving metrics show true riding intensity.

**Q: How is time-weighted averaging different?**
A: It weights each data point by the duration it represents, not by point count. Critical for accurate metrics with variable recording rates or gaps.

**Q: When should I update my FTP?**
A: When `estimated_ftp` from rides consistently exceeds your current setting by 5+ watts, or when your CTL increases significantly.

**Q: What's the minimum activity duration for reliable metrics?**
A: 20+ minutes for most metrics. Decoupling/cardiac drift needs 60+ minutes to be meaningful.

**Q: Can I compare my metrics to others?**
A: Use normalized metrics (W/kg, IF, hrTSS) rather than absolute values for fair comparisons across different athletes.

**Q: Why is my VAM lower when climbing?**
A: VAM depends on gradient and elevation gain, not power. A steady climb will have lower VAM than a steep climb at the same speed.

---

## Support and Documentation

- **Metric calculations**: See source code in `src/strava_analyzer/metrics/`
- **Configuration**: Edit `settings.yaml` or configure via Python Settings object
- **Architecture**: See `docs/ADR_*.md` for design decisions
- **Time-weighted averaging**: See `docs/ADR_005_TIME_WEIGHTED_AVERAGING.md` for technical details
- **Issues**: Check calculator classes for default values when stream data is unavailable

---

**Note:** This document consolidates METRICS.md, METRICS_GUIDE.md, and NEW_METRICS_SUMMARY.md (previous separate files). All information is now in this single comprehensive reference.
