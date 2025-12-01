"""
ECharts Generator Module
Handles chart generation using MCP ECharts server
"""

import json
import re
from typing import Dict, Any, Optional, List


def extract_column_names_from_sql(sql_query: str) -> List[str]:
    """
    Extract column names from SQL SELECT query.
    
    Args:
        sql_query: SQL query string
        
    Returns:
        List of column names
    """
    try:
        if not sql_query:
            return []
        
        # Find the SELECT ... FROM portion
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return []
        
        select_clause = select_match.group(1)
        
        # Split by comma (not inside parentheses)
        columns = []
        paren_depth = 0
        current_col = []
        
        for char in select_clause:
            if char == '(':
                paren_depth += 1
                current_col.append(char)
            elif char == ')':
                paren_depth -= 1
                current_col.append(char)
            elif char == ',' and paren_depth == 0:
                columns.append(''.join(current_col).strip())
                current_col = []
            else:
                current_col.append(char)
        
        # Add the last column
        if current_col:
            columns.append(''.join(current_col).strip())
        
        # Extract actual column names (handle AS aliases, brackets, etc.)
        column_names = []
        for col in columns:
            # Remove leading/trailing whitespace
            col = col.strip()
            
            # Check for AS alias
            as_match = re.search(r'\bAS\s+(.+)$', col, re.IGNORECASE)
            if as_match:
                alias = as_match.group(1).strip()
                # Remove brackets if present
                alias = re.sub(r'[\[\]]', '', alias)
                column_names.append(alias)
            else:
                # No alias - extract column name
                # Remove function calls like COUNT(*), handle [brackets]
                # Take the last part after dot (for table.column)
                cleaned = re.sub(r'.*\(.*?\)', col, '')  # Remove functions
                cleaned = re.sub(r'[\[\]]', '', cleaned)  # Remove brackets
                cleaned = cleaned.strip()
                
                # If it's just *, skip or use a generic name
                if cleaned == '*':
                    continue
                
                # Take last part after dot
                if '.' in cleaned:
                    cleaned = cleaned.split('.')[-1]
                
                if cleaned:
                    column_names.append(cleaned)
                else:
                    # For expressions like COUNT(*), use the original
                    original = re.sub(r'[\[\]]', '', col.strip())
                    column_names.append(original)
        
        return column_names
        
    except Exception as e:
        print(f"Error extracting column names from SQL: {e}")
        return []


def parse_sql_results(data: Any, sql_query: str = "") -> List[Dict[str, Any]]:
    """
    Parse SQL query results from various formats into structured list of dictionaries.
    
    Args:
        data: SQL results in various formats (string, list, etc.)
        sql_query: Optional SQL query to extract column names from
        
    Returns:
        List of dictionaries with column names and values
    """
    try:
        # If data is None or empty
        if not data:
            return []
        
        # If it's already a list of dicts, return it
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data
        
        # If it's a string, try to parse it
        if isinstance(data, str):
            # Remove "Result:" prefix if present
            if "Result:" in data:
                data = data.split("Result:", 1)[1].strip()
            
            # Try to parse as Python literal (safest for tuples)
            # Check if it looks like a list of tuples
            if data.strip().startswith('[') and '(' in data:
                try:
                    import ast
                    parsed_list = ast.literal_eval(data)
                    
                    if isinstance(parsed_list, list) and len(parsed_list) > 0:
                        # Convert tuples/lists to list of values
                        rows = []
                        for item in parsed_list:
                            if isinstance(item, (tuple, list)):
                                rows.append(list(item))
                        
                        if rows:
                            # Try to extract column names from SQL query first
                            headers = extract_column_names_from_sql(sql_query) if sql_query else []
                            
                            # If we got column names from SQL and they match the number of columns
                            if headers and len(headers) == len(rows[0]):
                                data_rows = rows
                                print(f"DEBUG: Using SQL-extracted column names: {headers}")
                            # Check if first row looks like headers (all strings)
                            elif len(rows) > 1 and all(isinstance(v, str) for v in rows[0]):
                                headers = rows[0]
                                data_rows = rows[1:]
                            else:
                                # Generate generic column names
                                num_cols = len(rows[0])
                                headers = [f"col_{i}" for i in range(num_cols)]
                                data_rows = rows
                            
                            # Convert to list of dicts
                            result = []
                            for row in data_rows:
                                if len(row) == len(headers):
                                    result.append(dict(zip(headers, row)))
                            
                            return result if result else []
                except (ValueError, SyntaxError) as e:
                    print(f"DEBUG: ast.literal_eval failed: {e}, trying regex fallback")
                    # Fall through to regex method
            
            # Fallback: Try regex-based tuple extraction (for simpler cases)
            # Pattern for list of tuples: [(val1, val2), (val3, val4)]
            tuple_pattern = r'\[(\([^\)]+\)[,\s]*)+\]'
            
            if re.search(tuple_pattern, data):
                # Extract all tuples - but handle nested parens better
                # Split by '), (' to get individual tuples
                tuple_strings = re.split(r'\),\s*\(', data.strip('[]'))
                if tuple_strings:
                    rows = []
                    for tuple_str in tuple_strings:
                        # Clean up
                        tuple_str = tuple_str.strip('()')
                        # Split by comma, handling quoted strings
                        values = []
                        for val in tuple_str.split(','):
                            val = val.strip().strip("'\"")
                            # Try to convert to number
                            try:
                                if '.' in val:
                                    values.append(float(val))
                                else:
                                    values.append(int(val))
                            except ValueError:
                                values.append(val)
                        if values:
                            rows.append(values)
                    
                    # If we have rows, determine column names
                    if rows:
                        # Try to extract column names from SQL query first
                        headers = extract_column_names_from_sql(sql_query) if sql_query else []
                        
                        # If we got column names from SQL and they match the number of columns
                        if headers and len(headers) == len(rows[0]):
                            data_rows = rows
                            print(f"DEBUG: Using SQL-extracted column names: {headers}")
                        # Check if first row looks like headers (all strings)
                        elif len(rows) > 1 and all(isinstance(v, str) for v in rows[0]):
                            headers = rows[0]
                            data_rows = rows[1:]
                        else:
                            # Generate generic column names
                            num_cols = len(rows[0])
                            headers = [f"col_{i}" for i in range(num_cols)]
                            data_rows = rows
                        
                        # Convert to list of dicts
                        result = []
                        for row in data_rows:
                            if len(row) == len(headers):
                                result.append(dict(zip(headers, row)))
                        
                        return result if result else []
            
            # Try to parse as JSON
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        
        # If it's a list but not of dicts, try to structure it
        if isinstance(data, list):
            # If it's a list of tuples
            if len(data) > 0 and isinstance(data[0], (tuple, list)):
                num_cols = len(data[0])
                headers = [f"col_{i}" for i in range(num_cols)]
                return [dict(zip(headers, row)) for row in data]
        
        # Last resort: return empty list
        print(f"Warning: Could not parse SQL results: {type(data)}")
        return []
        
    except Exception as e:
        print(f"Error parsing SQL results: {e}")
        import traceback
        traceback.print_exc()
        return []


def detect_graph_request(question: str, llm) -> Dict[str, Any]:
    """
    Detect if the user wants a graph/chart and what type, including variants.
    
    Returns:
        {
            "needs_graph": bool,
            "chart_type": str or None,  # "bar", "line", "pie", etc., or None for auto-select
            "variant": str or None,  # "stacked", "grouped", "smooth", "area", "donut", etc.
            "reasoning": str
        }
    """
    prompt = f"""
Analyze the following user question and determine if they want a visualization/graph/chart.

User Question: "{question}"

Respond in JSON format with:
{{
    "needs_graph": true/false,
    "chart_type": "bar" | "line" | "pie" | "scatter" | "heatmap" | "candlestick" | "radar" | "gauge" | "funnel" | "sankey" | "treemap" | "sunburst" | "boxplot" | "graph" | "parallel" | "tree" | null,
    "variant": "stacked" | "grouped" | "smooth" | "area" | "donut" | null,
    "reasoning": "brief explanation"
}}

Chart type detection:
- If the user explicitly mentions a chart type (like "show me a bar chart"), set chart_type to that type
- If they want a graph but don't specify the type (like "visualize this"), set chart_type to null
- If they don't want a graph at all, set needs_graph to false

Variant detection:
- Bar charts: "stacked" (stacked bars) or "grouped" (side-by-side bars)
- Line charts: "smooth" (curved lines), "area" (filled area under line), "stacked" (stacked areas)
- Pie charts: "donut" (ring chart with hollow center)
- Set variant to null if no specific variant is mentioned

Common keywords:
- Graphs: chart, graph, plot, visualize, show, display, trend, distribution, comparison
- Stacked: stacked, cumulative, total
- Grouped: grouped, side-by-side, compared
- Smooth: smooth, curved
- Area: area, filled
- Donut: donut, ring
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Clean markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"Error detecting graph request: {e}")
        return {"needs_graph": False, "chart_type": None, "reasoning": "Error in detection"}


def select_chart_type(data: Any, question: str, sql_query: str, llm) -> str:
    """
    Automatically select the best chart type based on data structure and query intent.
    
    Returns:
        Chart type string: "bar", "line", "pie", etc.
    """
    prompt = f"""
You are a data visualization expert. Based on the user's question, SQL query, and data structure, select the BEST chart type.

User Question: "{question}"
SQL Query: "{sql_query}"
Data Sample: {str(data)[:500]}

Available chart types:
- bar: Compare categorical data, show rankings
- line: Show trends over time, continuous data
- pie: Show proportions and percentages
- scatter: Show relationships between two variables
- heatmap: Show data density or patterns in a matrix (especially geographic data with coordinates)
- radar: Compare multiple dimensions across items
- gauge: Show single KPI or progress
- funnel: Show conversion or process stages
- sankey: Show flow between states
- treemap: Show hierarchical data with size comparison
- sunburst: Show multi-level hierarchical data
- boxplot: Show statistical distribution
- candlestick: Show financial OHLC data
- graph: Show network relationships
- parallel: Show multi-dimensional data comparison
- tree: Show tree structure/hierarchy

Respond with ONLY the chart type name (one word, lowercase). Examples: "bar", "line", "pie", "heatmap"
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        chart_type = content.strip().lower().replace('"', '').replace("'", "")
        
        # Validate chart type
        valid_types = ["bar", "line", "pie", "scatter", "heatmap", "radar", "gauge", 
                      "funnel", "sankey", "treemap", "sunburst", "boxplot", "candlestick",
                      "graph", "parallel", "tree"]
        
        if chart_type not in valid_types:
            print(f"Invalid chart type '{chart_type}', defaulting to 'bar'")
            return "bar"
        
        return chart_type
    except Exception as e:
        print(f"Error selecting chart type: {e}")
        return "bar"  # Default fallback


def prepare_chart_data(data: Any, chart_type: str, question: str, llm, variant: Optional[str] = None, sql_query: str = "") -> Dict[str, Any]:
    """
    Transform SQL query results into the format required by ECharts.
    
    Args:
        data: SQL query results
        chart_type: Type of chart
        question: User's question
        llm: Language model
        variant: Chart variant (stacked, grouped, smooth, area, donut, etc.)
        sql_query: Optional SQL query to extract column names from
    
    Returns:
        Dictionary with chart-specific data format
    """
    # First, clean and structure the data
    structured_data = parse_sql_results(data, sql_query)
    
    print(f"DEBUG: Structured data for chart: {json.dumps(structured_data, default=str, indent=2)[:500]}")
    
    if not structured_data:
        print("WARNING: No structured data available for chart!")
        return {
            "data": [{"category": "No Data", "value": 0}],
            "title": "No Data Available"
        }
    
    prompt = f"""
Transform the SQL query results into the exact format needed for an ECharts {chart_type} chart{f" ({variant} variant)" if variant else ""}.

CRITICAL INSTRUCTIONS:
1. Use the ACTUAL values from the SQL data below - the real names, real numbers, exact values
2. Do NOT make up placeholder names like "Category A", "make1", "Label1", etc.
3. Do NOT generate random percentages or values
4. Copy the exact data from the SQL results into the chart format
5. For example, if the SQL shows "Tesla: 50000", the chart data must show {{"category": "Tesla", "value": 50000}}
6. If the SQL has multiple columns that represent different series (e.g., County, VehicleType, Count), use the "group" field

User Question: "{question}"
Chart Type: {chart_type}
Variant: {variant or "none"}
SQL Data (RAW RESULTS TO USE):
{json.dumps(structured_data, default=str, indent=2)}

Based on the chart type, format the data correctly:

For SIMPLE BAR chart (no grouping/stacking):
{{
    "data": [
        {{"category": "Label1", "value": 10}},
        {{"category": "Label2", "value": 20}}
    ],
    "title": "Chart Title",
    "axisXTitle": "X Axis Label",
    "axisYTitle": "Y Axis Label"
}}

For STACKED BAR chart (when SQL has multiple series - e.g., County + VehicleType + Count):
{{
    "data": [
        {{"category": "King", "value": 5000, "group": "BEV"}},
        {{"category": "King", "value": 2000, "group": "PHEV"}},
        {{"category": "Pierce", "value": 3000, "group": "BEV"}},
        {{"category": "Pierce", "value": 1500, "group": "PHEV"}}
    ],
    "stack": true,
    "title": "Chart Title",
    "axisXTitle": "County",
    "axisYTitle": "Vehicle Count"
}}

For GROUPED BAR chart (side-by-side comparison):
{{
    "data": [
        {{"category": "King", "value": 5000, "group": "BEV"}},
        {{"category": "King", "value": 2000, "group": "PHEV"}},
        {{"category": "Pierce", "value": 3000, "group": "BEV"}},
        {{"category": "Pierce", "value": 1500, "group": "PHEV"}}
    ],
    "group": true,
    "title": "Chart Title",
    "axisXTitle": "County",
    "axisYTitle": "Vehicle Count"
}}

For LINE chart:
{{
    "data": [
        {{"time": "2020", "value": 10}},
        {{"time": "2021", "value": 20}}
    ],
    "smooth": {str(variant == "smooth").lower()},
    "showArea": {str(variant == "area").lower()},
    "title": "Chart Title",
    "axisXTitle": "Year",
    "axisYTitle": "Count"
}}

For STACKED LINE/AREA chart:
{{
    "data": [
        {{"time": "2020", "value": 100, "group": "BEV"}},
        {{"time": "2020", "value": 50, "group": "PHEV"}},
        {{"time": "2021", "value": 150, "group": "BEV"}},
        {{"time": "2021", "value": 80, "group": "PHEV"}}
    ],
    "stack": true,
    "showArea": true,
    "title": "Chart Title"
}}

For PIE chart (regular):
{{
    "data": [
        {{"category": "Tesla", "value": 30000}},
        {{"category": "Nissan", "value": 20000}}
    ],
    "title": "Chart Title"
}}

For DONUT PIE chart:
{{
    "data": [
        {{"category": "BEV", "value": 70000}},
        {{"category": "PHEV", "value": 30000}}
    ],
    "innerRadius": 0.6,
    "title": "Chart Title"
}}

For HEATMAP chart:
{{
    "data": [
        {{"x": "Location1", "y": "Category1", "value": 100}},
        {{"x": "Location2", "y": "Category2", "value": 200}}
    ],
    "title": "Chart Title",
    "axisXTitle": "X Axis",
    "axisYTitle": "Y Axis"
}}

IMPORTANT: 
- Detect if SQL data has 3+ columns - if so, likely needs grouping
- The "group" field should come from the SQL data (e.g., VehicleType, Make, etc.)
- For stacked/grouped charts, ensure each category-group combination has one data point

Respond with ONLY the JSON object, no explanations.
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Clean markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        chart_data = json.loads(content)
        return chart_data
    except Exception as e:
        print(f"Error preparing chart data: {e}")
        # Return minimal fallback data
        return {
            "data": [{"category": "Data", "value": 1}],
            "title": "Chart"
        }


def generate_fallback_option(chart_type: str, chart_data: Dict[str, Any]) -> str:
    """
    Generate a minimal but functional ECharts option when LLM fails.
    Supports stacked/grouped variants.
    """
    data_array = chart_data.get("data", [])
    title = chart_data.get("title", "Chart")
    is_stacked = chart_data.get("stack", False)
    is_grouped = chart_data.get("group", False)
    inner_radius = chart_data.get("innerRadius", 0)
    is_smooth = chart_data.get("smooth", False)
    show_area = chart_data.get("showArea", False)
    
    # Check if data has groups
    has_groups = any('group' in item for item in data_array if isinstance(item, dict))
    
    if chart_type == "pie":
        radius = ["60%", "40%"] if inner_radius > 0 else "50%"
        return json.dumps({
            "title": {"text": title, "left": "center", "top": "5%"},
            "tooltip": {"trigger": "item"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [{
                "name": title,
                "type": "pie",
                "radius": radius,
                "data": [{"name": item.get("category", "Item"), "value": item.get("value", 0)} for item in data_array],
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        })
    elif chart_type == "bar":
        if has_groups and (is_stacked or is_grouped):
            # Extract unique categories and groups
            categories = list(dict.fromkeys([item.get("category", "") for item in data_array]))
            groups = list(dict.fromkeys([item.get("group", "") for item in data_array if "group" in item]))
            
            # Create series for each group
            series = []
            for group in groups:
                group_data = []
                for category in categories:
                    value = next((item.get("value", 0) for item in data_array 
                                if item.get("category") == category and item.get("group") == group), 0)
                    group_data.append(value)
                
                series_config = {
                    "name": group,
                    "type": "bar",
                    "data": group_data
                }
                if is_stacked:
                    series_config["stack"] = "total"
                
                series.append(series_config)
            
            return json.dumps({
                "title": {"text": title, "left": "center"},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": groups},
                "xAxis": {"type": "category", "data": categories},
                "yAxis": {"type": "value"},
                "series": series
            })
        else:
            # Simple bar chart
            categories = [item.get("category", f"Item {i}") for i, item in enumerate(data_array)]
            values = [item.get("value", 0) for item in data_array]
            return json.dumps({
                "title": {"text": title, "left": "center"},
                "tooltip": {},
                "xAxis": {"type": "category", "data": categories},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "data": values}]
            })
    elif chart_type == "line":
        if has_groups and is_stacked:
            # Stacked line chart
            time_points = list(dict.fromkeys([item.get("time", "") for item in data_array]))
            groups = list(dict.fromkeys([item.get("group", "") for item in data_array if "group" in item]))
            
            series = []
            for group in groups:
                group_data = []
                for time_point in time_points:
                    value = next((item.get("value", 0) for item in data_array 
                                if item.get("time") == time_point and item.get("group") == group), 0)
                    group_data.append(value)
                
                series_config = {
                    "name": group,
                    "type": "line",
                    "stack": "total",
                    "data": group_data
                }
                if show_area:
                    series_config["areaStyle"] = {}
                if is_smooth:
                    series_config["smooth"] = True
                
                series.append(series_config)
            
            return json.dumps({
                "title": {"text": title, "left": "center"},
                "tooltip": {"trigger": "axis"},
                "legend": {"data": groups},
                "xAxis": {"type": "category", "data": time_points},
                "yAxis": {"type": "value"},
                "series": series
            })
        else:
            # Simple line chart
            time_points = [item.get("time", f"T{i}") for i, item in enumerate(data_array)]
            values = [item.get("value", 0) for item in data_array]
            series_config = {"type": "line", "data": values}
            if is_smooth:
                series_config["smooth"] = True
            if show_area:
                series_config["areaStyle"] = {}
            
            return json.dumps({
                "title": {"text": title, "left": "center"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": time_points},
                "yAxis": {"type": "value"},
                "series": [series_config]
            })
    elif chart_type == "heatmap":
        # For heatmap, restructure data
        heatmap_data = []
        for item in data_array:
            x = item.get("x", 0)
            y = item.get("y", 0)
            value = item.get("value", 0)
            heatmap_data.append([x, y, value])
        
        return json.dumps({
            "title": {"text": title, "left": "center"},
            "tooltip": {"position": "top"},
            "grid": {"height": "70%", "top": "10%"},
            "xAxis": {"type": "category"},
            "yAxis": {"type": "category"},
            "visualMap": {
                "min": 0,
                "max": max([item[2] for item in heatmap_data]) if heatmap_data else 100,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "5%"
            },
            "series": [{
                "name": title,
                "type": "heatmap",
                "data": heatmap_data,
                "label": {"show": True},
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        })
    else:
        # Generic fallback
        return json.dumps({
            "title": {"text": title, "left": "center"},
            "tooltip": {},
            "series": [{"type": chart_type, "data": [item.get("value", 0) for item in data_array]}]
        })


def generate_echarts_option(chart_type: str, chart_data: Dict[str, Any], llm) -> str:
    """
    Generate ECharts option JSON from formatted chart data with support for variants.
    
    Returns:
        JSON string of ECharts option
    """
    # Check for stacked/grouped data
    has_groups = any('group' in item for item in chart_data.get('data', []) if isinstance(item, dict))
    is_stacked = chart_data.get('stack', False)
    is_grouped = chart_data.get('group', False)
    is_smooth = chart_data.get('smooth', False)
    show_area = chart_data.get('showArea', False)
    inner_radius = chart_data.get('innerRadius', 0)
    
    prompt = f"""
Generate a complete ECharts option object in JSON format for a {chart_type} chart.

Chart Type: {chart_type}
Data: {json.dumps(chart_data, indent=2)}
Has Groups: {has_groups}
Is Stacked: {is_stacked}
Is Grouped: {is_grouped}
Is Smooth: {is_smooth}
Show Area: {show_area}
Inner Radius: {inner_radius}

CRITICAL INSTRUCTIONS FOR STACKED/GROUPED CHARTS:
1. If data has "group" field, create MULTIPLE series - one per unique group
2. For stacked bar: Each series should have same stack ID (e.g., "stack": "total")
3. For grouped bar: Each series should NOT have a stack property
4. Extract unique categories and groups from the data
5. Map data correctly to each series

Example for STACKED BAR with groups:
{{
  "title": {{"text": "Title", "left": "center"}},
  "tooltip": {{"trigger": "axis", "axisPointer": {{"type": "shadow"}}}},
  "legend": {{"data": ["BEV", "PHEV"]}},
  "xAxis": {{"type": "category", "data": ["King", "Pierce"]}},
  "yAxis": {{"type": "value"}},
  "series": [
    {{
      "name": "BEV",
      "type": "bar",
      "stack": "total",
      "data": [5000, 3000]
    }},
    {{
      "name": "PHEV",
      "type": "bar",
      "stack": "total",
      "data": [2000, 1500]
    }}
  ]
}}

Example for GROUPED BAR (no stack):
{{
  "title": {{"text": "Title", "left": "center"}},
  "tooltip": {{"trigger": "axis"}},
  "legend": {{"data": ["BEV", "PHEV"]}},
  "xAxis": {{"type": "category", "data": ["King", "Pierce"]}},
  "yAxis": {{"type": "value"}},
  "series": [
    {{"name": "BEV", "type": "bar", "data": [5000, 3000]}},
    {{"name": "PHEV", "type": "bar", "data": [2000, 1500]}}
  ]
}}

Example for SMOOTH LINE:
{{
  "title": {{"text": "Title", "left": "center"}},
  "tooltip": {{"trigger": "axis"}},
  "xAxis": {{"type": "category", "data": ["2020", "2021"]}},
  "yAxis": {{"type": "value"}},
  "series": [{{
    "type": "line",
    "smooth": true,
    "data": [100, 150]
  }}]
}}

Example for AREA LINE:
{{
  "title": {{"text": "Title", "left": "center"}},
  "tooltip": {{"trigger": "axis"}},
  "xAxis": {{"type": "category", "data": ["2020", "2021"]}},
  "yAxis": {{"type": "value"}},
  "series": [{{
    "type": "line",
    "areaStyle": {{}},
    "data": [100, 150]
  }}]
}}

Example for DONUT PIE:
{{
  "title": {{"text": "Title", "left": "center"}},
  "tooltip": {{"trigger": "item"}},
  "legend": {{"orient": "vertical", "left": "left"}},
  "series": [{{
    "type": "pie",
    "radius": ["60%", "40%"],
    "data": [{{"name": "BEV", "value": 70000}}, {{"name": "PHEV", "value": 30000}}]
  }}]
}}

Now generate the complete, professional ECharts option with:
- Proper title from chart_data
- Tooltips with appropriate triggers
- Legend (if multiple series)
- Good color palette
- Axis labels (if applicable)
- Responsive design

Respond with ONLY valid JSON, no explanations:
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Clean markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Remove any trailing commas before closing braces/brackets (common JSON error)
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Try to validate and pretty print
        parsed = json.loads(content)
        return json.dumps(parsed)
        
    except json.JSONDecodeError as e:
        print(f"Error generating ECharts option (JSON parse error): {e}")
        print(f"Problematic content (first 500 chars): {content[:500]}")
        
        # Try to fix common issues and re-parse
        try:
            # Remove comments
            content = re.sub(r'//.*?\n', '\n', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # Fix trailing commas
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            parsed = json.loads(content)
            return json.dumps(parsed)
        except:
            pass
        
        # Return minimal fallback with the actual chart_data
        return generate_fallback_option(chart_type, chart_data)
        
    except Exception as e:
        print(f"Error generating ECharts option: {e}")
        return generate_fallback_option(chart_type, chart_data)


def generate_echarts_html(chart_type: str, chart_data: Dict[str, Any], ctx) -> str:
    """
    Generate interactive ECharts HTML using MCP server.
    
    Args:
        chart_type: Type of chart (bar, line, pie, etc.)
        chart_data: Formatted data for the chart
        ctx: Application context with MCP access
        
    Returns:
        HTML string with embedded ECharts visualization
    """
    try:
        echarts_option = generate_echarts_option(chart_type, chart_data, ctx.llm)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{ margin: 0; padding: 10px; background: transparent; }}
        #chart {{ width: 100%; height: 400px; }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        var chartDom = document.getElementById('chart');
        var myChart = echarts.init(chartDom);
        var option = {echarts_option};
        myChart.setOption(option);
        
        // Responsive resize
        window.addEventListener('resize', function() {{
            myChart.resize();
        }});
    </script>
</body>
</html>
"""
        return html
        
    except Exception as e:
        print(f"Error generating ECharts HTML: {e}")
        return f"<div>Error generating chart: {str(e)}</div>"


def generate_chart_for_query(question: str, sql_query: str, query_result: Any, ctx) -> Optional[str]:
    """
    Main function to generate chart for a database query with variant support.
    
    Args:
        question: User's original question
        sql_query: The SQL query that was executed
        query_result: Results from the SQL query
        ctx: Application context
        
    Returns:
        HTML string with embedded chart, or None if no chart needed
    """
    try:
        llm = ctx.llm
        
        print(f"\n{'='*60}")
        print(f"CHART GENERATION DEBUG")
        print(f"{'='*60}")
        print(f"Question: {question}")
        print(f"SQL Query: {sql_query[:200] if sql_query else 'None'}...")
        print(f"Query Result Type: {type(query_result)}")
        print(f"Query Result Preview: {str(query_result)[:500]}...")
        print(f"{'='*60}\n")
        
        # Step 1: Detect if user wants a graph and what variant
        print(f"Detecting graph request for: {question}")
        detection = detect_graph_request(question, llm)
        
        if not detection.get("needs_graph", False):
            print("No graph needed")
            return None
        
        print(f"Graph needed. Reasoning: {detection.get('reasoning')}")
        
        # Step 2: Determine chart type (user-specified or auto-select)
        chart_type = detection.get("chart_type")
        variant = detection.get("variant")
        
        if not chart_type:
            print("Auto-selecting chart type...")
            chart_type = select_chart_type(query_result, question, sql_query, llm)
        
        print(f"Selected chart type: {chart_type}")
        if variant:
            print(f"Chart variant: {variant}")
        
        # Step 3: Prepare chart data with variant info
        print("Preparing chart data...")
        chart_data = prepare_chart_data(query_result, chart_type, question, llm, variant, sql_query)
        
        # Step 4: Generate HTML
        print("Generating ECharts HTML...")
        html = generate_echarts_html(chart_type, chart_data, ctx)
        
        return html
        
    except Exception as e:
        print(f"Error in generate_chart_for_query: {e}")
        import traceback
        traceback.print_exc()
        return None

