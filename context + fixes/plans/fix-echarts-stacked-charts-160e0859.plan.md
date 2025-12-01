<!-- 160e0859-5334-42fc-b89b-ff188cd0d98f 50cb1780-71f2-482f-b841-fb1f79b00313 -->
# Fix ECharts Stacked/Grouped Chart Support

## Problem

Current implementation doesn't support stacked/grouped charts because:

1. Data prep doesn't handle `group` field
2. Not using MCP chart tools - generating raw HTML instead
3. No detection of chart variants (stacked, grouped, area, smooth line, etc.)

## Solution

### 1. Enhance Chart Variant Detection

**File: `src/database/echarts.py`**

Update `detect_graph_request()` (lines 110-154) to return variant info:

```python
{
    "needs_graph": bool,
    "chart_type": "bar",
    "variant": "stacked" | "grouped" | "smooth" | "area" | None,
    "reasoning": str
}
```

Add variants to prompt:

- Bar: stacked, grouped
- Line: smooth, area, stacked
- Pie: donut (innerRadius)

### 2. Fix Data Preparation for Groups

**File: `src/database/echarts.py`**

Update `prepare_chart_data()` prompt (lines 212-311) to include group examples:

```python
For STACKED/GROUPED BAR:
{
    "data": [
        {"category": "Q1", "value": 100, "group": "Sales"},
        {"category": "Q1", "value": 80, "group": "Marketing"},
        {"category": "Q2", "value": 120, "group": "Sales"}
    ],
    "stack": true,  # or "group": true
    "title": "Chart Title"
}
```

### 3. Use MCP Tools Directly (Critical Fix)

**File: `src/database/echarts.py`**

Replace `generate_echarts_html()` (lines 481-527) to call actual MCP tools:

```python
def generate_echarts_html(chart_type: str, chart_data: Dict[str, Any], ctx) -> str:
    """Call MCP ECharts tools directly instead of manual HTML generation"""
    
    tool_map = {
        "bar": "mcp_mcp-echarts_generate_bar_chart",
        "line": "mcp_mcp-echarts_generate_line_chart",
        "pie": "mcp_mcp-echarts_generate_pie_chart",
        # ... etc
    }
    
    # Call the MCP tool with proper parameters
    result = ctx.mcp_client.call_tool(
        tool_map[chart_type],
        {
            "data": chart_data["data"],
            "title": chart_data.get("title"),
            "stack": chart_data.get("stack", False),
            "group": chart_data.get("group", False),
            "outputType": "svg",  # or "png"
            # ... other params
        }
    )
    
    # Wrap SVG/PNG in HTML for display
    return wrap_chart_in_html(result)
```

**Key change**: Stop generating `echarts_option` JSON via LLM. Let MCP tools handle chart generation.

### 4. Update Data Transform Logic

**File: `src/database/echarts.py`**

In `prepare_chart_data()`, teach LLM to detect when grouping is needed:

```python
prompt = f"""
CRITICAL: If the SQL data has multiple series/categories to compare:
- Add "group" field to each data point
- Set "stack": true for stacked charts or "group": true for grouped charts

Example SQL: SELECT County, Electric_Vehicle_Type, COUNT(*) ...
Transform to:
{{
    "data": [
        {{"category": "King", "value": 5000, "group": "BEV"}},
        {{"category": "King", "value": 2000, "group": "PHEV"}},
        {{"category": "Pierce", "value": 3000, "group": "BEV"}}
    ],
    "stack": true
}}
```

### 5. Add MCP Client to Context

**File: `src/appContext.py`**

Ensure `ctx.mcp_client` is available for calling MCP tools programmatically.

If not present, add MCP client initialization to context.

## Files Changed

- `src/database/echarts.py` - Main logic fixes
- `src/appContext.py` - Add MCP client if missing

## Testing

```bash
# Test stacked bar
"Show me a stacked bar chart of BEV vs PHEV by county"

# Test grouped bar  
"Create a grouped bar chart comparing the top 5 cities across vehicle types"

# Test smooth line
"Generate a smooth line chart of EV trends by year"

# Test donut pie
"Make a donut chart of manufacturer market share"
```

## Why This Works

- MCP tools have built-in support for variants (stack, group, smooth, innerRadius)
- Direct tool calls = no LLM JSON generation errors
- Proper data format with `group` field enables multi-series charts
- Chart variant detection ensures right parameters passed to MCP tools

### To-dos

- [ ] Update detect_graph_request() to detect chart variants (stacked, grouped, smooth, area)
- [ ] Update prepare_chart_data() prompt to include group field examples and logic
- [ ] Rewrite generate_echarts_html() to call MCP tools directly instead of manual HTML generation
- [ ] Verify ctx.mcp_client exists in appContext.py, add if missing
- [ ] Test stacked/grouped bar charts with real queries