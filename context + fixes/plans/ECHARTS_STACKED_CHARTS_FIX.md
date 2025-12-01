# ECharts Stacked/Grouped Charts Fix - Implementation Complete

## Overview
Fixed ECharts implementation to properly support stacked bar charts, grouped bar charts, and other chart variants (smooth lines, area charts, donut charts).

## Problem Statement
The original implementation had three critical issues:
1. **No variant detection** - Couldn't detect if user wanted stacked vs grouped vs regular charts
2. **Missing group field** - Data preparation didn't include the `group` field needed for multi-series charts
3. **Incomplete ECharts configuration** - Generated configurations didn't properly handle stacked/grouped series

## Solution Implemented

### 1. Enhanced Variant Detection
**File: `src/database/echarts.py` - `detect_graph_request()` function**

**Changes:**
- Added `variant` field to detection response
- Detects chart variants:
  - **Bar charts**: `stacked` or `grouped`
  - **Line charts**: `smooth`, `area`, or `stacked`
  - **Pie charts**: `donut`
- Enhanced prompt to recognize variant keywords (stacked, grouped, cumulative, side-by-side, smooth, curved, area, filled, donut, ring)

**Example Detection:**
```python
{
    "needs_graph": true,
    "chart_type": "bar",
    "variant": "stacked",  # NEW
    "reasoning": "User requested a stacked bar chart"
}
```

### 2. Fixed Data Preparation for Groups
**File: `src/database/echarts.py` - `prepare_chart_data()` function**

**Changes:**
- Added `variant` parameter
- Comprehensive examples for all chart variants in the LLM prompt:
  - Simple bar chart (no grouping)
  - Stacked bar chart (with group field)
  - Grouped bar chart (with group field, no stack)
  - Line charts (smooth, area variants)
  - Stacked line/area charts
  - Donut pie charts (innerRadius)
- Instructs LLM to detect multi-column SQL data and automatically add group fields

**Example Output for Stacked Bar:**
```python
{
    "data": [
        {"category": "King", "value": 5000, "group": "BEV"},
        {"category": "King", "value": 2000, "group": "PHEV"},
        {"category": "Pierce", "value": 3000, "group": "BEV"},
        {"category": "Pierce", "value": 1500, "group": "PHEV"}
    ],
    "stack": true,
    "title": "EV Distribution by County and Type"
}
```

### 3. Improved ECharts Option Generation
**File: `src/database/echarts.py` - `generate_echarts_option()` function**

**Changes:**
- Detects variant flags from chart_data (stack, group, smooth, showArea, innerRadius)
- Enhanced prompt with detailed examples for:
  - Stacked bar charts (multiple series with `stack: "total"`)
  - Grouped bar charts (multiple series without stack)
  - Smooth line charts (`smooth: true`)
  - Area line charts (`areaStyle: {}`)
  - Donut pie charts (`radius: ["60%", "40%"]`)
- Provides complete ECharts configuration examples

**Example Configuration for Stacked Bar:**
```javascript
{
  "title": {"text": "Title", "left": "center"},
  "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
  "legend": {"data": ["BEV", "PHEV"]},
  "xAxis": {"type": "category", "data": ["King", "Pierce"]},
  "yAxis": {"type": "value"},
  "series": [
    {
      "name": "BEV",
      "type": "bar",
      "stack": "total",  // Critical for stacking
      "data": [5000, 3000]
    },
    {
      "name": "PHEV",
      "type": "bar",
      "stack": "total",  // Same stack ID
      "data": [2000, 1500]
    }
  ]
}
```

### 4. Enhanced Fallback Option Generator
**File: `src/database/echarts.py` - `generate_fallback_option()` function**

**Changes:**
- Detects group fields in data
- Handles stacked/grouped bar charts:
  - Extracts unique categories and groups
  - Creates multiple series (one per group)
  - Applies stack configuration when needed
- Handles stacked line/area charts
- Supports donut pie charts
- Includes smooth and area options for line charts

**Key Logic:**
```python
if has_groups and (is_stacked or is_grouped):
    # Extract unique categories and groups
    categories = list(dict.fromkeys([item.get("category", "") for item in data_array]))
    groups = list(dict.fromkeys([item.get("group", "") for item in data_array if "group" in item]))
    
    # Create series for each group
    for group in groups:
        series_config = {
            "name": group,
            "type": "bar",
            "data": group_data
        }
        if is_stacked:
            series_config["stack"] = "total"  # Add stack for stacked charts
```

### 5. Updated Main Chart Generation Function
**File: `src/database/echarts.py` - `generate_chart_for_query()` function**

**Changes:**
- Extracts `variant` from detection result
- Passes `variant` to `prepare_chart_data()`
- Logs variant information for debugging

## Supported Chart Variants

### Bar Charts
- ✅ **Simple bar** - Single series, basic bars
- ✅ **Stacked bar** - Multiple series stacked on top of each other
- ✅ **Grouped bar** - Multiple series side-by-side

### Line Charts
- ✅ **Simple line** - Basic line chart
- ✅ **Smooth line** - Curved lines instead of straight segments
- ✅ **Area chart** - Filled area under the line
- ✅ **Stacked line/area** - Multiple series stacked

### Pie Charts
- ✅ **Regular pie** - Standard pie chart
- ✅ **Donut chart** - Ring chart with hollow center

## Testing Examples

### Stacked Bar Chart
```
User: "Show me a stacked bar chart of BEV vs PHEV by county"

Expected Behavior:
1. Detects: chart_type="bar", variant="stacked"
2. SQL query returns: County, VehicleType, Count
3. Data prep creates:
   - group field populated with VehicleType
   - stack: true flag set
4. ECharts generates:
   - Multiple series (one per VehicleType)
   - Each series has stack: "total"
   - Bars stack on top of each other
```

### Grouped Bar Chart
```
User: "Create a grouped bar chart comparing the top 5 cities across vehicle types"

Expected Behavior:
1. Detects: chart_type="bar", variant="grouped"
2. Data prep creates group field
3. ECharts generates:
   - Multiple series without stack property
   - Bars appear side-by-side
```

### Smooth Line Chart
```
User: "Generate a smooth line chart of EV trends by year"

Expected Behavior:
1. Detects: chart_type="line", variant="smooth"
2. Data prep sets: smooth: true
3. ECharts generates:
   - Line series with smooth: true
   - Curved lines connecting points
```

### Donut Chart
```
User: "Make a donut chart of manufacturer market share"

Expected Behavior:
1. Detects: chart_type="pie", variant="donut"
2. Data prep sets: innerRadius: 0.6
3. ECharts generates:
   - Pie series with radius: ["60%", "40%"]
   - Ring-shaped chart
```

## Technical Details

### Data Flow
```
User Question
    ↓
detect_graph_request() → {chart_type, variant}
    ↓
prepare_chart_data(variant) → {data with groups, stack flags}
    ↓
generate_echarts_option() → Complete ECharts config
    ↓
generate_echarts_html() → Interactive HTML
    ↓
Frontend Display
```

### Key Data Structures

**Simple Chart Data:**
```python
{
    "data": [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20}
    ],
    "title": "Chart Title"
}
```

**Stacked/Grouped Chart Data:**
```python
{
    "data": [
        {"category": "A", "value": 10, "group": "Series1"},
        {"category": "A", "value": 15, "group": "Series2"},
        {"category": "B", "value": 20, "group": "Series1"},
        {"category": "B", "value": 25, "group": "Series2"}
    ],
    "stack": true,  # or "group": true
    "title": "Chart Title"
}
```

## Files Modified
- ✅ `src/database/echarts.py` - All chart generation logic
  - `detect_graph_request()` - Added variant detection
  - `prepare_chart_data()` - Added group field support
  - `generate_echarts_option()` - Enhanced with variant examples
  - `generate_fallback_option()` - Full stacked/grouped support
  - `generate_chart_for_query()` - Variant pipeline integration

## Backward Compatibility
✅ All existing functionality preserved:
- Simple charts still work
- Auto chart type selection still works
- Fallback options improved but still functional
- No breaking changes to API

## Why This Works

### Problem: "Stacked bar chart shows no data"
**Root Cause:** LLM was generating data without group fields, and ECharts config wasn't creating multiple series.

**Solution:**
1. Variant detection tells system user wants stacking
2. Data prep prompt explicitly shows how to add group fields
3. ECharts option generator creates multiple series with stack property
4. Fallback option can handle it even if LLM fails

### Problem: "Can't do grouped bar charts"
**Root Cause:** Same as stacked - missing group field and no multi-series support.

**Solution:**
1. Variant detection distinguishes grouped from stacked
2. Data prep adds groups but sets `group: true` instead of `stack: true`
3. ECharts creates multiple series WITHOUT stack property (side-by-side)

### Problem: "Only basic charts work"
**Root Cause:** No detection or handling of chart variants (smooth, area, donut, etc.)

**Solution:**
1. Comprehensive variant detection
2. Variant-specific data preparation
3. Variant-aware ECharts configuration

## Debug Output
The system now logs:
```
CHART GENERATION DEBUG
============================================================
Question: Show me a stacked bar chart of BEV vs PHEV by county
SQL Query: SELECT County, Electric_Vehicle_Type, COUNT(*)...
Query Result Type: <class 'list'>
Query Result Preview: [{'County': 'King', 'Electric_Vehicle_Type': 'BEV', 'count': 5000}...]
============================================================

Detecting graph request for: Show me a stacked bar chart...
Graph needed. Reasoning: User explicitly requested a stacked bar chart
Selected chart type: bar
Chart variant: stacked
Preparing chart data...
DEBUG: Structured data for chart: [{"County": "King", "Electric_Vehicle_Type": "BEV", "count": 5000}...]
Generating ECharts HTML...
```

## Performance
- No performance impact
- LLM calls remain the same (3-4 per chart)
- Fallback logic is faster and more reliable

## Edge Cases Handled
✅ Data without groups (simple chart)
✅ Data with groups (stacked/grouped chart)
✅ Mixed column types in SQL results
✅ Empty/null data
✅ LLM generation failures (enhanced fallback)
✅ Invalid variant requests (graceful degradation)

## Next Steps (Optional Enhancements)
1. Add more chart types (candlestick, sankey, etc.)
2. Cache variant detection for similar queries
3. Add user preferences for default variants
4. Support custom color schemes per variant
5. Enable drill-down in stacked charts

## Conclusion
The ECharts implementation now fully supports stacked and grouped charts, along with other variants. The fix addresses all three root causes:
1. ✅ Variant detection implemented
2. ✅ Group field properly handled in data prep
3. ✅ ECharts configurations support multi-series charts

Users can now request stacked bar charts, grouped bar charts, smooth line charts, area charts, and donut charts - and they will work correctly with actual data.

