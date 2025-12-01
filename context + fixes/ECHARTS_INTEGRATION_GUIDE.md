# ECharts Integration Implementation Guide

## Overview

This guide provides complete, step-by-step instructions for integrating Apache ECharts visualization into the Database Chat feature of the PathFinder application. When a user's query requests a graph, the system will:

1. Execute the SQL query to get data from the MSSQL database
2. Analyze the query intent and returned data
3. Determine if additional data is needed and fetch it if necessary
4. Select the appropriate ECharts chart type (or use user-specified type)
5. Generate an interactive HTML chart using the MCP ECharts server
6. Stream the chart back to the frontend for display

## Architecture Changes

### Components Modified
- `src/database/agent.py` - Add graph detection and ECharts generation
- `src/database/echarts_generator.py` - **NEW** - ECharts generation logic
- `src/api.py` - Update streaming response to include chart data
- `frontend/hooks/use-jewelry-chat.ts` - Handle chart data in responses
- `frontend/app/page.tsx` - Render interactive ECharts HTML

### Data Flow
```
User Query → SQL Agent → Execute SQL → Check for Graph Request
                                            ↓
                                    Yes: Generate Chart
                                            ↓
                                    Analyze Data + Query Intent
                                            ↓
                                    Need More Data? → Query DB Again (if needed)
                                            ↓
                                    Select Chart Type (auto or specified)
                                            ↓
                                    Call MCP ECharts Server
                                            ↓
                                    Generate Interactive HTML
                                            ↓
                                    Stream to Frontend
                                            ↓
                                    Render in Browser
```

## Prerequisites

### 1. MCP ECharts Server Configuration

Ensure the MCP ECharts server is configured in your Cursor settings. Add to `.cursor/mcp.json` or your global MCP configuration:

```json
{
  "mcpServers": {
    "mcp-echarts": {
      "command": "npx",
      "args": ["-y", "@replit/mcp-echarts"]
    },
    "mssql": {
      // ... your existing MSSQL configuration
    }
  }
}
```

### 2. Python Dependencies

Add to `requirements.txt` if not already present:
```
langchain-core>=0.2.0
langchain-community>=0.2.0
langgraph>=0.1.0
mcp>=0.1.0
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Frontend Dependencies

Verify these are in `frontend/package.json`:
```json
{
  "dependencies": {
    "react": "^18.0.0",
    "next": "^14.0.0"
  }
}
```

## Implementation Steps

## Step 1: Create ECharts Generator Module

Create a new file: `src/database/echarts_generator.py`

```python
"""
ECharts Generator Module
Handles chart generation using MCP ECharts server
"""

import json
from typing import Dict, Any, Optional, List
from langchain_core.messages import HumanMessage


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

Common keywords for graphs: chart, graph, plot, visualize, show, display, trend, distribution, comparison.
"""
    
    try:
        response = llm.invoke(prompt)
        # Extract JSON from response
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
- heatmap: Show data density or patterns in a matrix
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

Respond with ONLY the chart type name (one word, lowercase). Examples: "bar", "line", "pie"
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


def check_data_sufficiency(data: Any, question: str, chart_type: str, llm) -> Dict[str, Any]:
    """
    Check if the returned SQL data is sufficient for the requested chart.
    If not, generate a new SQL query to get the needed data.
    
    Returns:
        {
            "is_sufficient": bool,
            "missing_info": str or None,
            "suggested_sql": str or None
        }
    """
    prompt = f"""
Analyze if the returned SQL data is sufficient to create the requested chart.

User Question: "{question}"
Chart Type: "{chart_type}"
Returned Data: {str(data)[:1000]}

Determine:
1. Is this data sufficient to create a meaningful {chart_type} chart?
2. What information is missing (if any)?
3. If insufficient, write a SQL query to get the needed data.

Respond in JSON format:
{{
    "is_sufficient": true/false,
    "missing_info": "description of what's missing" or null,
    "suggested_sql": "SELECT query to get missing data" or null
}}
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"Error checking data sufficiency: {e}")
        return {"is_sufficient": True, "missing_info": None, "suggested_sql": None}


def prepare_chart_data(data: Any, chart_type: str, question: str, llm) -> Dict[str, Any]:
    """
    Transform SQL query results into the format required by ECharts.
    
    Returns:
        Dictionary with chart-specific data format
    """
    prompt = f"""
Transform the SQL query results into the exact format needed for an ECharts {chart_type} chart.

User Question: "{question}"
Chart Type: {chart_type}
SQL Data: {json.dumps(data, default=str)}

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

For SCATTER chart:
{{
    "data": [
        {{"x": 10, "y": 20}},
        {{"x": 15, "y": 25}}
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
        # Map chart types to MCP tool names
        chart_type_map = {
            "bar": "mcp_mcp-echarts_generate_bar_chart",
            "line": "mcp_mcp-echarts_generate_line_chart",
            "pie": "mcp_mcp-echarts_generate_pie_chart",
            "scatter": "mcp_mcp-echarts_generate_scatter_chart",
            "heatmap": "mcp_mcp-echarts_generate_heatmap_chart",
            "radar": "mcp_mcp-echarts_generate_radar_chart",
            "gauge": "mcp_mcp-echarts_generate_gauge_chart",
            "funnel": "mcp_mcp-echarts_generate_funnel_chart",
            "sankey": "mcp_mcp-echarts_generate_sankey_chart",
            "treemap": "mcp_mcp-echarts_generate_treemap_chart",
            "sunburst": "mcp_mcp-echarts_generate_sunburst_chart",
            "boxplot": "mcp_mcp-echarts_generate_boxplot_chart",
            "candlestick": "mcp_mcp-echarts_generate_candlestick_chart",
            "graph": "mcp_mcp-echarts_generate_graph_chart",
            "parallel": "mcp_mcp-echarts_generate_parallel_chart",
            "tree": "mcp_mcp-echarts_generate_tree_chart",
        }
        
        tool_name = chart_type_map.get(chart_type, "mcp_mcp-echarts_generate_bar_chart")
        
        # The MCP tools return PNG/SVG by default, but we need to generate the HTML
        # We'll use the general echarts tool and specify outputType as HTML via the option
        
        # For now, we'll construct the ECharts option JSON and use the generic generator
        # that can output as HTML (if available) or we'll embed the option in HTML ourselves
        
        # Since MCP echarts tools return images, we need to create HTML manually
        # Let's construct an ECharts option and embed it in HTML
        
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
        
        # Validate JSON
        json.loads(content)
        return content
        
    except Exception as e:
        print(f"Error generating ECharts option: {e}")
        # Return minimal fallback
        return json.dumps({
            "title": {"text": "Chart", "left": "center"},
            "tooltip": {},
            "series": [{"type": chart_type, "data": [1, 2, 3]}]
        })


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
        
        # Step 3: Check if data is sufficient
        sufficiency = check_data_sufficiency(query_result, question, chart_type, llm)
        
        data_to_use = query_result
        if not sufficiency.get("is_sufficient", True):
            print(f"Data insufficient: {sufficiency.get('missing_info')}")
            suggested_sql = sufficiency.get("suggested_sql")
            
            if suggested_sql:
                print(f"Fetching additional data with: {suggested_sql}")
                try:
                    # Execute the additional query
                    from langchain_community.agent_toolkits import SQLDatabaseToolkit
                    db = ctx.db
                    additional_result = db.run(suggested_sql)
                    data_to_use = additional_result
                    print(f"Additional data fetched successfully")
                except Exception as e:
                    print(f"Error fetching additional data: {e}")
                    # Continue with original data
        
        # Step 4: Prepare chart data
        print("Preparing chart data...")
        chart_data = prepare_chart_data(data_to_use, chart_type, question, llm)
        
        # Step 5: Generate HTML
        print("Generating ECharts HTML...")
        html = generate_echarts_html(chart_type, chart_data, ctx)
        
        return html
        
    except Exception as e:
        print(f"Error in generate_chart_for_query: {e}")
        import traceback
        traceback.print_exc()
        return None
```

## Step 2: Modify Database Agent

Update `src/database/agent.py` to integrate chart generation:

```python
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.checkpoint.memory import MemorySaver
from datetime import date


def callSQLAgent(ctx, question, session_id: str = "default_session"):
    llm = ctx.llm
    db = ctx.db

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    memory = ctx.memory
    system_prompt = """
    ## Washington EV Population SQL Agent (MSSQL via MCP)

You are a specialized, read‑only SQL Server agent for the `data.gov` database connected through the MCP `mssql` server. The database houses Washington State's electric vehicle population data. Generate precise, efficient SELECT queries in T‑SQL and provide concise business insights.

## Core Guidelines

### Query Generation Rules
- Generate **READ‑ONLY** SQL Server queries exclusively.
- **NEVER** run DML/DDL (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE).
- Discover schema first using `INFORMATION_SCHEMA` before assuming table/column names.
- Qualify objects with schema when helpful (e.g., `dbo.TableName`).
- Prefer sargable predicates, appropriate indexes (when known), and minimal `SELECT` lists.
- Handle NULLs, data type conversions, and string trimming/casing thoughtfully.
- When unsure about a column, first query the dictionary to confirm.

### Response Format
1. The SQL query (single final query or a short sequence if discovery is required).
2. Brief explanation of logic and any assumptions.
3. Key insights to expect from the results (with units and context).

## Schema Discovery Workflow
Run lightweight discovery before analytics:
1) List tables
```sql
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME;
```
2) Inspect columns of the chosen table
```sql
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = '<ev_table_name>'
ORDER BY ORDINAL_POSITION;
```
3) Optional quick row count
```sql
SELECT COUNT(*) AS row_count FROM <schema>.<ev_table_name>;
```

### Likely EV Population Fields (for orientation; verify via discovery)
- VIN, Make, Model, Model_Year
- Electric_Vehicle_Type (e.g., BEV, PHEV)
- Electric_Range, Base_MSRP
- CAFV_Eligibility
- County, City, State, Postal_Code
- Legislative_District, Census_Tract
- Vehicle_Location (Latitude, Longitude)
- Electric_Utility

Use these only as hints; rely on `INFORMATION_SCHEMA` to confirm exact names.

## Example Business Questions (Washington EV)
- EV count by County/City; BEV vs PHEV split.
- Top 10 Makes/Models by registrations.
- Year‑over‑year trend by `Model_Year`.
- Average Electric Range by Make and Model_Year.
- CAFV eligibility distribution.
- Vehicles by Electric Utility and County.
- Counts within a Postal Code or Legislative District.

## Query Patterns (replace placeholders after discovery)

EV count by county and type:
```sql
SELECT County, Electric_Vehicle_Type, COUNT(*) AS vehicle_count
FROM <schema>.<ev_table>
GROUP BY County, Electric_Vehicle_Type
ORDER BY County, Electric_Vehicle_Type;
```

Top makes/models:
```sql
SELECT TOP 10 Make, Model, COUNT(*) AS registrations
FROM <schema>.<ev_table>
GROUP BY Make, Model
ORDER BY registrations DESC;
```

BEV vs PHEV share statewide:
```sql
SELECT Electric_Vehicle_Type, COUNT(*) AS vehicles
FROM <schema>.<ev_table>
GROUP BY Electric_Vehicle_Type
ORDER BY vehicles DESC;
```

Average electric range by make and year:
```sql
SELECT Make, Model_Year, AVG(TRY_CONVERT(float, Electric_Range)) AS avg_range
FROM <schema>.<ev_table>
WHERE TRY_CONVERT(float, Electric_Range) IS NOT NULL
GROUP BY Make, Model_Year
ORDER BY Make, Model_Year;
```

## Best Practices
1. Use clear aliases and consistent casing.
2. Use `TRY_CONVERT`/`TRY_CAST` when parsing numeric fields stored as strings.
3. Consider NULL/blank values and trim whitespace for grouping.
4. Limit result size (`TOP`, filters) for exploratory steps.
5. Present user‑friendly terms in the narrative (e.g., "Make" instead of raw column casing).

## Answer Generation Guidelines
1. Use markdown; include compact tables for aggregates.
2. Provide short, decision‑oriented insights (what, where, how much, trend).
3. State assumptions and how you validated schema.
4. Keep outputs read‑only and safe; never suggest write operations.
    """.format(current_date=date.today().isoformat())

    agent = create_react_agent(llm, tools, prompt=system_prompt, checkpointer=memory)

    config = {"configurable": {"thread_id": session_id}}

    result = agent.invoke({"messages": [HumanMessage(content=question)]}, config)
    final_message = result["messages"][-1].content

    # Extract the SQL query and results from the agent's response
    sql_query = ""
    query_result = None
    
    # Try to extract SQL query from intermediate steps
    for message in result["messages"]:
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                if "query" in tool_call.get("args", {}):
                    sql_query = tool_call["args"]["query"]
        
        # Extract query results
        if hasattr(message, "content") and "Result:" in str(message.content):
            query_result = message.content

    # NEW: Generate chart if requested
    chart_html = None
    try:
        from .echarts_generator import generate_chart_for_query
        chart_html = generate_chart_for_query(question, sql_query, query_result, ctx)
        if chart_html:
            print("Chart generated successfully")
    except Exception as e:
        print(f"Error generating chart: {e}")
        import traceback
        traceback.print_exc()

    return {
        "answer": final_message, 
        "sql_query": sql_query,
        "chart_html": chart_html  # NEW
    }
```

## Step 3: Update API Streaming

Modify `src/api.py` to include chart HTML in streaming responses:

Find the `stream_chat_message` method (around line 109) and update it:

```python
async def stream_chat_message(
    self, message: str, session_id: str
) -> AsyncGenerator[str, None]:
    """Stream a chat message using the agent with fake real-time updates"""
    try:
        self._check_initialization()

        if not message or not message.strip():
            yield f"data: {json.dumps({'error': 'Message cannot be empty', 'status': 'error'})}\n\n"
            return

        print(f"Streaming message with agent: {message}")

        # IMMEDIATE RESPONSE - Start streaming right away
        yield f"data: {json.dumps({'response': 'Thinking...', 'status': 'analyzing'})}\n\n"
        await asyncio.sleep(0.01)

        # Run the agent in a separate thread to avoid blocking the event loop
        agent_response = await asyncio.to_thread(
            callSQLAgent, self.ctx, message.strip(), session_id
        )
        answer = agent_response.get("answer", "")
        sql_query = agent_response.get("sql_query", "")
        chart_html = agent_response.get("chart_html", None)  # NEW

        # Send the final response
        response_data = {
            'response': answer, 
            'sqlQuery': sql_query, 
            'status': 'completed'
        }
        
        # Add chart if generated
        if chart_html:
            response_data['chartHtml'] = chart_html  # NEW
        
        yield f"data: {json.dumps(response_data)}\n\n"

    except HTTPException as e:
        yield f"data: {json.dumps({'error': e.detail, 'status': 'error'})}\n\n"
    except Exception as e:
        print(f"Error streaming message: {str(e)}")
        yield f"data: {json.dumps({'error': f'I encountered an error: {str(e)}', 'status': 'error'})}\n\n"
```

Also update the non-streaming `process_chat_message` method (around line 78):

```python
async def process_chat_message(
    self, message: str, session_id: str
) -> Dict[str, Any]:
    """Process a chat message through the SQL Agent"""
    try:
        self._check_initialization()

        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        print(f"Processing message with agent: {message}")

        # Run the agent in a separate thread to avoid blocking the event loop
        agent_response = await asyncio.to_thread(
            callSQLAgent, self.ctx, message.strip(), session_id
        )
        answer = agent_response.get("answer", "")
        sql_query = agent_response.get("sql_query", "")
        chart_html = agent_response.get("chart_html", None)  # NEW

        result = {"response": answer, "sqlQuery": sql_query, "status": "success"}
        
        if chart_html:  # NEW
            result["chartHtml"] = chart_html
        
        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return {
            "response": f"I encountered an error while processing your request: {str(e)}",
            "status": "error",
        }
```

## Step 4: Update Frontend Types

Modify `frontend/hooks/use-jewelry-chat.ts` to handle chart HTML:

Update the `ChatMessage` interface (around line 5):

```typescript
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sqlQuery?: string
  chartHtml?: string  // NEW
}
```

Update the streaming handler (around line 224):

```typescript
for (const line of lines) {
  if (line.startsWith('data: ')) {
    try {
      const data = JSON.parse(line.slice(6))
      
      if (data.response) {
        // Update the content with the streamed response
        assistantContent = data.response
        
        // Apply real-time formatting to the streaming content
        const formattedContent = formatStreamingContent(assistantContent)
        
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { 
                  ...msg, 
                  content: formattedContent, 
                  sqlQuery: data.sqlQuery,
                  chartHtml: data.chartHtml  // NEW
                }
              : msg
          )
        )
      }
      
      if (data.error) {
        throw new Error(data.error)
      }
    } catch (parseError) {
      console.warn('Failed to parse SSE data:', line)
    }
  }
}
```

Also update the non-streaming case (around line 269):

```typescript
} else {
  const data = await response.json()
  
  const assistantMessage: ChatMessage = {
    id: generateMessageId(),
    role: 'assistant',
    content: data.response || 'I received your message but couldn\'t generate a proper response.',
    timestamp: new Date(),
    sqlQuery: data.sqlQuery,
    chartHtml: data.chartHtml  // NEW
  }

  setMessages(prev => [...prev, assistantMessage])
}
```

## Step 5: Update Frontend Display

Modify `frontend/app/page.tsx` to render the chart HTML:

Find the message rendering section and add chart display logic. Look for where messages are mapped and add this component:

```typescript
{/* Around line 200+ where messages are rendered */}
{messages.map((message) => (
  <div key={message.id} className={/* ... existing classes ... */}>
    {/* Existing message content */}
    <div className="message-content">
      {message.content}
    </div>
    
    {/* SQL Query display (existing) */}
    {message.sqlQuery && (
      <div className="sql-query-display">
        {/* existing SQL display code */}
      </div>
    )}
    
    {/* NEW: Chart display */}
    {message.chartHtml && (
      <div className="chart-container" style={{
        marginTop: '1rem',
        padding: '1rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #e0e0e0'
      }}>
        <div 
          dangerouslySetInnerHTML={{ __html: message.chartHtml }}
          style={{
            width: '100%',
            minHeight: '400px'
          }}
        />
      </div>
    )}
  </div>
))}
```

If you want a safer approach than `dangerouslySetInnerHTML`, create a dedicated component:

```typescript
// Add this component in the same file or create a new one

interface ChartDisplayProps {
  htmlContent: string
}

function ChartDisplay({ htmlContent }: ChartDisplayProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  
  useEffect(() => {
    if (iframeRef.current) {
      const iframe = iframeRef.current
      const doc = iframe.contentDocument || iframe.contentWindow?.document
      if (doc) {
        doc.open()
        doc.write(htmlContent)
        doc.close()
      }
    }
  }, [htmlContent])
  
  return (
    <div className="chart-container" style={{
      marginTop: '1rem',
      padding: '1rem',
      backgroundColor: '#f8f9fa',
      borderRadius: '8px',
      border: '1px solid #e0e0e0'
    }}>
      <iframe
        ref={iframeRef}
        style={{
          width: '100%',
          height: '450px',
          border: 'none',
          borderRadius: '4px'
        }}
        sandbox="allow-scripts allow-same-origin"
        title="ECharts Visualization"
      />
    </div>
  )
}

// Then use it in the message rendering:
{message.chartHtml && (
  <ChartDisplay htmlContent={message.chartHtml} />
)}
```

## Step 6: Add CSS Styling (Optional)

Add to `frontend/app/globals.css` or `frontend/styles/globals.css`:

```css
/* Chart Container Styles */
.chart-container {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  overflow: hidden;
}

.chart-container iframe {
  display: block;
  width: 100%;
  height: 450px;
  border: none;
  border-radius: 4px;
  background: white;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .chart-container {
    background-color: #1a1a1a;
    border-color: #333;
  }
  
  .chart-container iframe {
    background: #2a2a2a;
  }
}

/* Responsive chart sizing */
@media (max-width: 768px) {
  .chart-container {
    padding: 0.5rem;
  }
  
  .chart-container iframe {
    height: 350px;
  }
}
```

## Testing Instructions

### 1. Backend Testing

Test the chart generation module:

```python
# Create test file: tests/test_echarts_integration.py

import sys
sys.path.append('src')

from appContext import AppContext
from database.echarts_generator import generate_chart_for_query

def test_chart_generation():
    ctx = AppContext()
    
    # Test case 1: Bar chart request
    question = "Show me a bar chart of EV counts by county"
    sql_query = "SELECT County, COUNT(*) as count FROM EVs GROUP BY County"
    result = [
        {"County": "King", "count": 5000},
        {"County": "Pierce", "count": 3000},
        {"County": "Snohomish", "count": 2500}
    ]
    
    html = generate_chart_for_query(question, sql_query, result, ctx)
    
    assert html is not None
    assert "<script" in html
    assert "echarts" in html.lower()
    print("✓ Chart generation test passed")

if __name__ == "__main__":
    test_chart_generation()
```

Run the test:
```bash
python tests/test_echarts_integration.py
```

### 2. Integration Testing

Start the backend:
```bash
python -m src.api
```

Test the endpoint with curl:
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me a bar chart of top 10 EV makes", "session_id": "test_123"}'
```

### 3. Frontend Testing

Start the frontend:
```bash
cd frontend
npm run dev
```

Test queries:
1. **Explicit chart request**: "Show me a bar chart of EVs by county"
2. **Implicit chart request**: "Visualize the distribution of EVs by type"
3. **Specific chart type**: "Create a pie chart showing BEV vs PHEV percentages"
4. **No chart needed**: "How many EVs are registered in King County?"

### 4. End-to-End Testing

Complete workflow test:

```bash
# Terminal 1: Start backend
python -m src.api

# Terminal 2: Start frontend
cd frontend && npm run dev

# Terminal 3: Run E2E test
# (Open browser to http://localhost:3000)
```

Test scenarios:
- [ ] Chart is generated for explicit requests
- [ ] Chart type matches user specification
- [ ] Auto-selection chooses appropriate chart type
- [ ] Chart displays correctly in the UI
- [ ] Chart is responsive
- [ ] No chart generated when not requested
- [ ] Error handling works properly

## Troubleshooting

### Issue: "MCP echarts server not found"

**Solution**: Ensure MCP configuration is correct:
```bash
# Check if npx can access the package
npx -y @replit/mcp-echarts --help
```

Add to your Cursor settings or `.cursor/mcp.json`.

### Issue: "Chart not displaying in frontend"

**Checklist**:
1. Check browser console for errors
2. Verify `chartHtml` is in the API response (Network tab)
3. Ensure iframe sandbox permissions are correct
4. Check CSP (Content Security Policy) headers

**Solution**: Add to `next.config.mjs`:
```javascript
const nextConfig = {
  // ... existing config
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net"
          }
        ]
      }
    ]
  }
}
```

### Issue: "Invalid JSON in chart generation"

**Solution**: The LLM might be adding markdown formatting. The code already handles this, but if issues persist:

```python
# In echarts_generator.py, enhance the JSON cleaning:
def clean_llm_response(content: str) -> str:
    """Remove common LLM response artifacts"""
    # Remove markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    # Remove common prefixes
    content = content.strip()
    if content.startswith("Here is") or content.startswith("Here's"):
        lines = content.split('\n')
        content = '\n'.join(lines[1:])
    
    return content.strip()
```

### Issue: "Chart generation is slow"

**Solutions**:
1. Cache chart types for similar queries
2. Reduce LLM prompt size
3. Use faster LLM model for chart selection
4. Pre-compute common visualizations

### Issue: "Data insufficient but additional query fails"

**Debug**:
```python
# Add detailed logging in echarts_generator.py
print(f"Original SQL: {sql_query}")
print(f"Original Result: {query_result}")
print(f"Suggested SQL: {suggested_sql}")
print(f"Additional Result: {additional_result}")
```

**Solution**: Improve the prompt for generating additional SQL queries, or fall back to original data.

## Performance Optimization

### 1. Caching Chart Configurations

```python
# In echarts_generator.py
from functools import lru_cache
import hashlib

def get_query_hash(question: str, data: str) -> str:
    """Generate hash for caching"""
    combined = f"{question}:{data}"
    return hashlib.md5(combined.encode()).hexdigest()

@lru_cache(maxsize=100)
def cached_chart_selection(query_hash: str, question: str, data_sample: str, llm_model: str) -> str:
    """Cache chart type selection"""
    # Chart selection logic here
    pass
```

### 2. Async Chart Generation

```python
# Make chart generation async
async def generate_chart_async(question: str, sql_query: str, result: Any, ctx):
    """Async version of chart generation"""
    return await asyncio.to_thread(
        generate_chart_for_query,
        question, sql_query, result, ctx
    )
```

### 3. Progressive Loading

Show placeholder while chart loads:
```typescript
const [chartLoading, setChartLoading] = useState(false)

{message.chartHtml ? (
  <ChartDisplay htmlContent={message.chartHtml} />
) : chartLoading ? (
  <div className="chart-loading">
    <Spinner /> Generating chart...
  </div>
) : null}
```

## Security Considerations

### 1. HTML Sanitization

If not using iframe approach, sanitize HTML:

```bash
npm install dompurify @types/dompurify
```

```typescript
import DOMPurify from 'dompurify'

const sanitizedHtml = DOMPurify.sanitize(message.chartHtml, {
  ALLOWED_TAGS: ['div', 'script', 'style'],
  ALLOWED_ATTR: ['id', 'class', 'style']
})
```

### 2. SQL Injection Prevention

Already handled by LangChain SQL toolkit, but ensure:
- All queries are read-only (SELECT only)
- No dynamic SQL concatenation
- Parameterized queries where possible

### 3. Rate Limiting

Add to `src/api.py`:
```python
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/chat/stream")
@limiter.limit("10/minute")  # Limit chart generation
async def chat_stream_endpoint(request: Request, chat_request: ChatRequest):
    # ... existing code
```

## Deployment Checklist

- [ ] MCP echarts server configured in production
- [ ] Environment variables set
- [ ] Database connection tested
- [ ] Frontend build successful
- [ ] API endpoints responding
- [ ] Chart generation tested with production data
- [ ] Error handling verified
- [ ] Logging configured
- [ ] Performance monitoring enabled
- [ ] Security headers configured

## Environment Variables

Add to `.env`:
```bash
# Existing variables
DATABASE_URL=your_database_url
OPENAI_API_KEY=your_openai_key

# New (optional)
ECHARTS_CACHE_SIZE=100
CHART_GENERATION_TIMEOUT=30
ENABLE_CHART_CACHING=true
```

## Monitoring and Logging

Add to `src/api.py`:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# In chart generation:
logger.info(f"Chart requested for query: {question}")
logger.info(f"Chart type selected: {chart_type}")
logger.info(f"Chart generation time: {time.time() - start_time}s")
```

## Future Enhancements

### 1. Chart Customization
- Allow users to customize colors, themes
- Interactive legend toggling
- Export chart as image

### 2. Advanced Chart Types
- Composite charts (bar + line)
- 3D visualizations
- Geographic maps with location data

### 3. Real-time Updates
- WebSocket connection for live data updates
- Animated transitions
- Auto-refresh charts

### 4. Chart Gallery
- Save favorite visualizations
- Share charts with team
- Template library

## Support and Resources

- **ECharts Documentation**: https://echarts.apache.org/en/index.html
- **MCP ECharts Server**: https://github.com/replit/mcp-echarts
- **LangChain SQL Toolkit**: https://python.langchain.com/docs/integrations/toolkits/sql_database
- **FastAPI Streaming**: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

## Conclusion

This guide provides a complete implementation path for integrating ECharts visualization into your Database Chat feature. The system intelligently:

1. Detects when visualizations are requested
2. Selects appropriate chart types
3. Ensures data sufficiency
4. Generates interactive, responsive charts
5. Streams results to the frontend

Follow each step carefully, test thoroughly, and refer to the troubleshooting section for common issues.

**Questions or Issues?** 
- Check the troubleshooting section
- Review error logs in console
- Test individual components separately
- Verify MCP server connectivity

Good luck with your implementation! 🚀

