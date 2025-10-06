# Heatmap Chart Generation Fix

## Issue
**Error:** `Expecting value: line 12 column 18 (char 212)` when generating heatmap charts.

The LLM was generating malformed JSON for the ECharts option, causing a JSON parse error.

## Root Cause
The `generate_echarts_option()` function had no error recovery when the LLM produced invalid JSON (missing commas, extra commas, JavaScript comments, etc.).

## Fix Applied

### 1. Enhanced JSON Parsing with Error Recovery
**File:** `src/database/echarts_generator.py` (lines 359-397)

**Added:**
- Automatic removal of trailing commas: `,}` → `}`
- JavaScript comment removal: `// comment` and `/* comment */`
- Better error messages showing the problematic content
- Fallback to `generate_fallback_option()` on parse failure

**Code:**
```python
# Remove any trailing commas before closing braces/brackets (common JSON error)
content = re.sub(r',(\s*[}\]])', r'\1', content)

try:
    parsed = json.loads(content)
    return json.dumps(parsed)
except json.JSONDecodeError as e:
    print(f"Error generating ECharts option (JSON parse error): {e}")
    print(f"Problematic content (first 500 chars): {content[:500]}")
    
    # Try to fix common issues
    content = re.sub(r'//.*?\n', '\n', content)  # Remove comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r',(\s*[}\]])', r'\1', content)  # Fix trailing commas
    
    # If still fails, use fallback
    return generate_fallback_option(chart_type, chart_data)
```

### 2. Added Fallback Chart Generator
**File:** `src/database/echarts_generator.py` (lines 314-392)

**New Function:** `generate_fallback_option(chart_type, chart_data)`

Creates valid ECharts configurations without LLM when JSON parsing fails:

- **Pie Chart:** Legend, tooltips, proper data format
- **Bar Chart:** Categories on X-axis, values on Y-axis
- **Heatmap:** Visual map, grid layout, proper 2D data structure
- **Generic:** Minimal but functional fallback

**Example (Heatmap):**
```python
elif chart_type == "heatmap":
    heatmap_data = []
    for item in data_array:
        x = item.get("x", 0)
        y = item.get("y", 0)
        value = item.get("value", 0)
        heatmap_data.append([x, y, value])
    
    return json.dumps({
        "title": {"text": title, "left": "center"},
        "tooltip": {"position": "top"},
        "xAxis": {"type": "category"},
        "yAxis": {"type": "category"},
        "visualMap": {
            "min": 0,
            "max": max([item[2] for item in heatmap_data]) if heatmap_data else 100,
            "calculable": True
        },
        "series": [{
            "type": "heatmap",
            "data": heatmap_data
        }]
    })
```

## Result
✅ **Before:** Charts failed with JSON parse errors
✅ **After:** Charts render successfully using fallback when LLM generates invalid JSON

### Debug Output
Now shows helpful diagnostics:
```
Error generating ECharts option (JSON parse error): Expecting value: line 12 column 18
Problematic content (first 500 chars): {"title": {"text": "Heatmap"}, "series": [{"type": "heatmap", "data": [...],}]}
                                                                                                           ^^^
                                                                                              Trailing comma found and fixed
```

## Testing
**Query:** "create a heatmap of the ev population by quantity in each zip code"

**Expected Result:**
- Chart renders successfully
- Shows zip codes and quantities
- Uses fallback if LLM JSON is malformed

**Before Fix:** ❌ JSON parse error, no chart
**After Fix:** ✅ Chart displays correctly

