# StravaAnalyzer Improvements Implementation Summary

## Overview
This implementation addresses three key improvements to StravaAnalyzer:
1. **Dataframe sorting by date** (descending order)
2. **Zone bin edges tracking with backpropagation**
3. **New aggregated metrics** (cadence, power, HR, speed - both avg and max)

---

## 1. Dataframe Sorting by Date (Requirement #1)

### Implementation
**File Modified:** `src/strava_analyzer/services/analysis_service.py`

**Location:** `run_analysis()` method, STEP 1

**Logic:**
- After merging enriched and new activities
- Before any metric calculations or zone bin application
- Sorts by `start_date_local` in **descending order** (most recent first)
- Resets index to ensure clean ordering

```python
if "start_date_local" in enriched_df.columns:
    enriched_df = enriched_df.sort_values(
        "start_date_local", ascending=False
    ).reset_index(drop=True)
```

**Purpose:** Ensures consistent ordering for all downstream operations

---

## 2. Zone Bin Edges with Backpropagation (Requirement #2)

### New Module Created
**File:** `src/strava_analyzer/metrics/zone_bins.py`

**Class:** `ZoneBinEdgesManager`

### Key Methods

#### `extract_zone_right_edges(zones: dict[str, tuple[float, float]]) -> list[float]`
- Extracts only the **right edges** from zone bin definitions
- Ignores infinity boundaries (last zone upper bound)
- Returns sorted list of right edges
- Example: Power zones `[(0,157), (158,214), ...]` → `[157, 214, ...]`

#### `get_current_zone_bins() -> dict[str, list[float]]`
- Retrieves current zone bin edges based on active settings
- Returns: `{'power_bins': [...], 'hr_bins': [...]}`

#### `apply_zone_bins_with_backpropagation(enriched_df, config_timestamp=None) -> pd.DataFrame`
**This is the main backpropagation function:**

1. **Validates & Sorts**: Ensures dataframe has `start_date_local` column and is sorted descending
2. **Initializes Columns**: Creates `power_zone_bins` and `hr_zone_bins` columns if missing
3. **Early Exit**: If all activities already have zone bins, skips processing
4. **Finds Closest Activity**:
   - Takes `config_timestamp` (when zones were configured)
   - Finds activity with closest `start_date_local` to this timestamp
   - Sets zone bins on that activity entry
5. **Backpropagates Backward Only**:
   - Iterates from closest activity index to end of dataframe (older activities)
   - Fills `power_zone_bins` and `hr_zone_bins` for activities without them
   - Stops at most recent activity (never updates newer activities)

**Example Flow:**
```
Activities (sorted descending by date):
[Most Recent] Activity 1 (2025-12-01)
              Activity 2 (2025-11-25)  ← Config timestamp
              Activity 3 (2025-11-20)  ← Set bins here (closest)
              Activity 4 (2025-11-15)
              Activity 5 (2025-11-10)  ← Backpropagate to here
[Oldest]      Activity 6 (2025-11-05)

Result: Activities 3, 4, 5, 6 get zone bins
        Activities 1, 2 remain unchanged (newer)
```

### Integration Point
**File Modified:** `src/strava_analyzer/services/analysis_service.py`

**Location:** `run_analysis()` method, STEP 2 (right after sorting)

**Execution Order:**
1. ✅ Load existing data
2. ✅ Process new activities
3. ✅ Merge datasets
4. ✅ **Sort by date (descending)**
5. ✅ **Apply zone bins with backpropagation** ← FIRST metric operation
6. Continue with analysis and summarization

**Code:**
```python
enriched_df = self.zone_bins_manager.apply_zone_bins_with_backpropagation(
    enriched_df, config_timestamp=datetime.now()
)
```

### CSV Storage Format
- **Column Names:** `power_zone_bins`, `hr_zone_bins`
- **Storage Format:** String representation of list (e.g., `"[157, 214, 256, 300, 342]"`)
- **Helper Methods:**
  - `format_zone_bins_for_storage()`: Converts list to string
  - `parse_zone_bins_from_storage()`: Parses string back to list

---

## 3. New Aggregated Metrics (Requirement #3)

### New Module Created
**File:** `src/strava_analyzer/metrics/basic.py`

**Class:** `BasicMetricsCalculator`

### Metrics Calculated

#### Cadence Metrics
- **`raw_average_cadence`** / **`moving_average_cadence`** (RPM)
- **`raw_max_cadence`** / **`moving_max_cadence`** (RPM)
- Uses time-weighted average (includes zeros)
- Filters zeros for max calculation

#### Speed Metrics
- **`raw_average_speed`** / **`moving_average_speed`** (m/s)
- **`raw_max_speed`** / **`moving_max_speed`** (m/s)
- Looks for `velocity_smooth`, `velocity`, or `speed` columns
- Uses time-weighted average (includes zeros)
- Filters zeros for max calculation

### Integration
**File Modified:** `src/strava_analyzer/metrics/calculators.py`

**Changes:**
1. Added import: `from .basic import BasicMetricsCalculator`
2. Instantiated in `__init__`: `self.basic_calculator = BasicMetricsCalculator(settings)`
3. Added calculation in `compute_all_metrics()` loop:
   ```python
   basic_metrics = self.basic_calculator.calculate(stream_df, moving_only)
   all_metrics.update(basic_metrics)
   ```

### Metrics Export
**File Modified:** `src/strava_analyzer/metrics/__init__.py`

- Added `BasicMetricsCalculator` to imports and `__all__` list
- Added `ZoneBinEdgesManager` to imports and `__all__` list

---

## Execution Flow Summary

```
Pipeline.run_analysis()
    ↓
AnalysisService.run_analysis()
    ├─ Load existing enriched data
    ├─ Load new activities
    ├─ Process new activities (individual metric calculation)
    ├─ Merge datasets
    │
    ├─ STEP 1: Sort by start_date_local (descending) ✅
    │
    ├─ STEP 2: Apply zone bins with backpropagation ✅
    │   └─ Find closest activity to config timestamp
    │   └─ Set zone bins on that activity
    │   └─ Backpropagate to all older activities
    │
    ├─ Create summary (uses enriched_df with zone bins)
    │
    └─ Save results (enriched_df includes zone_bins columns)
```

---

## Files Modified/Created

### New Files (Created)
- ✅ `src/strava_analyzer/metrics/zone_bins.py` (169 lines)
- ✅ `src/strava_analyzer/metrics/basic.py` (138 lines)

### Modified Files
- ✅ `src/strava_analyzer/metrics/__init__.py` (added imports and exports)
- ✅ `src/strava_analyzer/metrics/calculators.py` (added BasicMetricsCalculator integration)
- ✅ `src/strava_analyzer/services/analysis_service.py` (added sorting and zone bins application)

---

## Key Design Decisions

1. **Right Edges Only**: Only storing right edges of zones makes CSV storage simpler and more readable. The left edge can be inferred from the previous zone's right edge.

2. **Backward-Only Backpropagation**: Ensures that newer runs with updated zone configurations don't retroactively change older activities' zone definitions. This preserves historical accuracy.

3. **Closest Activity Logic**: Uses absolute date difference to find the most relevant activity at the time of configuration change, rather than just taking the first activity after the config change.

4. **Zone Bins as First Metric Step**: Placing zone bin application before summary creation ensures all downstream calculations have access to the zone definitions used.

5. **Time-Weighted Metrics**: Cadence and speed averages use time-weighted means to account for variable sampling rates in stream data, consistent with existing HR and power metrics.

---

## Testing Recommendations

1. **Zone Bins Backpropagation:**
   - Create test dataframe with activities spanning multiple dates
   - Verify closest activity selection logic
   - Verify backpropagation fills only older activities
   - Verify config timestamp handling

2. **New Metrics:**
   - Verify cadence metrics calculate correctly with/without data
   - Verify speed metrics work with different column names
   - Verify moving vs raw differentiation
   - Verify max values exclude zeros appropriately

3. **Integration:**
   - Run full pipeline with sample data
   - Verify enriched CSV includes zone_bins columns
   - Verify sorting doesn't affect metric accuracy
   - Verify no duplicate or missing activities after merge+sort

4. **Edge Cases:**
   - Empty dataframes
   - Activities with missing start_date_local
   - Activities with no cadence/speed data
   - All activities already having zone bins
