"""
ECharts Generator Module
Handles chart generation using MCP ECharts server
"""

import json
import re
from typing import Dict, Any, Optional, List


def parse_sql_results(data: Any) -> List[Dict[str, Any]]:
    """
    Parse SQL query results from various formats into structured list of dictionaries.
    
    Args:
        data: SQL results in various formats (string, list, etc.)
        
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
            
            # Try to find patterns like: [(col1, col2), (val1, val2), ...]
            # or [('Make', 12345), ('Tesla', 50000), ...]
            
            # Pattern for list of tuples: [(val1, val2), (val3, val4)]
            tuple_pattern = r'\[(\([^\)]+\)[,\s]*)+\]'
            
            if re.search(tuple_pattern, data):
                # Extract all tuples
                tuples_match = re.findall(r'\(([^\)]+)\)', data)
                if tuples_match:
                    rows = []
                    for tuple_str in tuples_match:
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
                        rows.append(values)
                    
                    # If we have rows, try to determine column names
                    if rows:
                        # Assume first row might be headers, or use generic names
                        # Check if first row looks like headers (all strings)
                        if len(rows) > 1 and all(isinstance(v, str) for v in rows[0]):
                            headers = rows[0]
                            data_rows = rows[1:]
                        else:
                            # Generate column names
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
    Detect if the user wants a graph/chart and what type.
    
    Returns:
        {
            "needs_graph": bool,
            "chart_type": str or None,  # "bar", "line", "pie", etc., or None for auto-select
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
    "reasoning": "brief explanation"
}}

If the user explicitly mentions a chart type (like "show me a bar chart" or "create a pie chart"), set chart_type to that type.
If they want a graph but don't specify the type (like "visualize this" or "show me a chart"), set chart_type to null.
If they don't want a graph at all, set needs_graph to false.

Common keywords for graphs: chart, graph, plot, visualize, show, display, trend, distribution, comparison, heatmap, map.
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


def prepare_chart_data(data: Any, chart_type: str, question: str, llm) -> Dict[str, Any]:
    """
    Transform SQL query results into the format required by ECharts.
    
    Returns:
        Dictionary with chart-specific data format
    """
    # First, clean and structure the data
    structured_data = parse_sql_results(data)
    
    print(f"DEBUG: Structured data for chart: {json.dumps(structured_data, default=str, indent=2)[:500]}")
    
    if not structured_data:
        print("WARNING: No structured data available for chart!")
        return {
            "data": [{"category": "No Data", "value": 0}],
            "title": "No Data Available"
        }
    
    prompt = f"""
Transform the SQL query results into the exact format needed for an ECharts {chart_type} chart.

CRITICAL INSTRUCTIONS:
1. Use the ACTUAL values from the SQL data below - the real names, real numbers, exact values
2. Do NOT make up placeholder names like "Category A", "make1", "Label1", etc.
3. Do NOT generate random percentages or values
4. Copy the exact data from the SQL results into the chart format
5. For example, if the SQL shows "Tesla: 50000", the chart data must show {{"category": "Tesla", "value": 50000}}

User Question: "{question}"
Chart Type: {chart_type}
SQL Data (RAW RESULTS TO USE):
{json.dumps(structured_data, default=str, indent=2)}

Based on the chart type, format the data correctly:

For BAR chart:
{{
    "data": [
        {{"category": "Label1", "value": 10}},
        {{"category": "Label2", "value": 20}}
    ],
    "title": "Chart Title",
    "axisXTitle": "X Axis Label",
    "axisYTitle": "Y Axis Label"
}}

For LINE chart:
{{
    "data": [
        {{"time": "2020", "value": 10}},
        {{"time": "2021", "value": 20}}
    ],
    "title": "Chart Title",
    "axisXTitle": "X Axis",
    "axisYTitle": "Y Axis"
}}

For PIE chart:
{{
    "data": [
        {{"category": "Category A", "value": 30}},
        {{"category": "Category B", "value": 70}}
    ],
    "title": "Chart Title"
}}

For HEATMAP chart (especially for geographic data):
{{
    "data": [
        {{"x": "Location1", "y": "Category1", "value": 100}},
        {{"x": "Location2", "y": "Category2", "value": 200}}
    ],
    "title": "Chart Title",
    "axisXTitle": "X Axis",
    "axisYTitle": "Y Axis"
}}

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
    """
    data_array = chart_data.get("data", [])
    title = chart_data.get("title", "Chart")
    
    if chart_type == "pie":
        return json.dumps({
            "title": {"text": title, "left": "center", "top": "5%"},
            "tooltip": {"trigger": "item"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [{
                "name": title,
                "type": "pie",
                "radius": "50%",
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
        categories = [item.get("category", f"Item {i}") for i, item in enumerate(data_array)]
        values = [item.get("value", 0) for item in data_array]
        return json.dumps({
            "title": {"text": title, "left": "center"},
            "tooltip": {},
            "xAxis": {"type": "category", "data": categories},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": values}]
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
    Generate ECharts option JSON from formatted chart data.
    
    Returns:
        JSON string of ECharts option
    """
    prompt = f"""
Generate a complete ECharts option object in JSON format for a {chart_type} chart.

Chart Type: {chart_type}
Data: {json.dumps(chart_data, indent=2)}

Create a professional, visually appealing ECharts configuration with:
- Appropriate title
- Proper axis labels (if applicable)
- Good color scheme
- Tooltips
- Legend (if applicable)
- Responsive design

Respond with ONLY the valid JSON object for the ECharts option. Example structure:

{{
  "title": {{
    "text": "Chart Title",
    "left": "center"
  }},
  "tooltip": {{}},
  "xAxis": {{
    "type": "category",
    "data": ["A", "B", "C"]
  }},
  "yAxis": {{
    "type": "value"
  }},
  "series": [{{
    "type": "{chart_type}",
    "data": [10, 20, 30]
  }}]
}}

Now generate the complete option for the provided data:
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
    Main function to generate chart for a database query.
    
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
        
        # Step 1: Detect if user wants a graph
        print(f"Detecting graph request for: {question}")
        detection = detect_graph_request(question, llm)
        
        if not detection.get("needs_graph", False):
            print("No graph needed")
            return None
        
        print(f"Graph needed. Reasoning: {detection.get('reasoning')}")
        
        # Step 2: Determine chart type (user-specified or auto-select)
        chart_type = detection.get("chart_type")
        if not chart_type:
            print("Auto-selecting chart type...")
            chart_type = select_chart_type(query_result, question, sql_query, llm)
        
        print(f"Selected chart type: {chart_type}")
        
        # Step 3: Prepare chart data
        print("Preparing chart data...")
        chart_data = prepare_chart_data(query_result, chart_type, question, llm)
        
        # Step 4: Generate HTML
        print("Generating ECharts HTML...")
        html = generate_echarts_html(chart_type, chart_data, ctx)
        
        return html
        
    except Exception as e:
        print(f"Error in generate_chart_for_query: {e}")
        import traceback
        traceback.print_exc()
        return None

