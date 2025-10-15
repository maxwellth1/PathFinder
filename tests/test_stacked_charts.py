"""
Test script for stacked/grouped chart functionality
Run this to verify the implementation is correct
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.echarts import (
    detect_graph_request,
    prepare_chart_data,
    generate_fallback_option,
    parse_sql_results
)
import json


class MockLLM:
    """Mock LLM for testing"""
    def __init__(self, response_content):
        self.response_content = response_content
    
    def invoke(self, prompt):
        class Response:
            def __init__(self, content):
                self.content = content
        return Response(self.response_content)


def test_variant_detection():
    """Test that variant detection works"""
    print("\n" + "="*60)
    print("TEST 1: Variant Detection")
    print("="*60)
    
    # Test stacked bar detection
    llm = MockLLM(json.dumps({
        "needs_graph": True,
        "chart_type": "bar",
        "variant": "stacked",
        "reasoning": "User requested stacked bar chart"
    }))
    
    result = detect_graph_request("Show me a stacked bar chart of BEV vs PHEV", llm)
    
    assert result["needs_graph"] == True, "Should detect graph needed"
    assert result["chart_type"] == "bar", "Should detect bar chart"
    assert result["variant"] == "stacked", "Should detect stacked variant"
    
    print("[PASS] Variant detection working correctly")
    print(f"   Result: {json.dumps(result, indent=2)}")


def test_grouped_data_preparation():
    """Test that grouped data is prepared correctly"""
    print("\n" + "="*60)
    print("TEST 2: Grouped Data Preparation")
    print("="*60)
    
    # Mock SQL result with groups
    sql_data = [
        {"County": "King", "Electric_Vehicle_Type": "BEV", "count": 5000},
        {"County": "King", "Electric_Vehicle_Type": "PHEV", "count": 2000},
        {"County": "Pierce", "Electric_Vehicle_Type": "BEV", "count": 3000},
        {"County": "Pierce", "Electric_Vehicle_Type": "PHEV", "count": 1500}
    ]
    
    # Mock LLM response with grouped data
    expected_output = {
        "data": [
            {"category": "King", "value": 5000, "group": "BEV"},
            {"category": "King", "value": 2000, "group": "PHEV"},
            {"category": "Pierce", "value": 3000, "group": "BEV"},
            {"category": "Pierce", "value": 1500, "group": "PHEV"}
        ],
        "stack": True,
        "title": "EV Distribution by County and Type",
        "axisXTitle": "County",
        "axisYTitle": "Vehicle Count"
    }
    
    llm = MockLLM(json.dumps(expected_output))
    
    result = prepare_chart_data(
        sql_data, 
        "bar", 
        "Show stacked bar chart", 
        llm, 
        variant="stacked"
    )
    
    # Check if data has groups
    has_groups = any('group' in item for item in result.get('data', []))
    assert has_groups, "Data should have group field"
    assert result.get('stack') == True, "Should have stack flag"
    
    print("[PASS] Grouped data preparation working")
    print(f"   Data sample: {json.dumps(result['data'][:2], indent=2)}")
    print(f"   Stack flag: {result.get('stack')}")


def test_fallback_stacked_bar():
    """Test fallback option generation for stacked bars"""
    print("\n" + "="*60)
    print("TEST 3: Fallback Stacked Bar Chart")
    print("="*60)
    
    chart_data = {
        "data": [
            {"category": "King", "value": 5000, "group": "BEV"},
            {"category": "King", "value": 2000, "group": "PHEV"},
            {"category": "Pierce", "value": 3000, "group": "BEV"},
            {"category": "Pierce", "value": 1500, "group": "PHEV"}
        ],
        "stack": True,
        "title": "Test Stacked Chart"
    }
    
    echarts_option = generate_fallback_option("bar", chart_data)
    option = json.loads(echarts_option)
    
    # Verify multiple series
    assert "series" in option, "Should have series"
    assert len(option["series"]) >= 2, "Should have multiple series for groups"
    
    # Verify stack property
    for series in option["series"]:
        assert "stack" in series, "Each series should have stack property"
        assert series["stack"] == "total", "Stack ID should be 'total'"
    
    # Verify legend
    assert "legend" in option, "Should have legend"
    assert "data" in option["legend"], "Legend should have data"
    
    print("[PASS] Fallback stacked bar working")
    print(f"   Number of series: {len(option['series'])}")
    print(f"   Series names: {[s['name'] for s in option['series']]}")
    print(f"   Stack IDs: {[s.get('stack') for s in option['series']]}")


def test_fallback_grouped_bar():
    """Test fallback option generation for grouped bars"""
    print("\n" + "="*60)
    print("TEST 4: Fallback Grouped Bar Chart")
    print("="*60)
    
    chart_data = {
        "data": [
            {"category": "King", "value": 5000, "group": "BEV"},
            {"category": "King", "value": 2000, "group": "PHEV"},
            {"category": "Pierce", "value": 3000, "group": "BEV"},
            {"category": "Pierce", "value": 1500, "group": "PHEV"}
        ],
        "group": True,  # Grouped, not stacked
        "title": "Test Grouped Chart"
    }
    
    echarts_option = generate_fallback_option("bar", chart_data)
    option = json.loads(echarts_option)
    
    # Verify multiple series
    assert len(option["series"]) >= 2, "Should have multiple series"
    
    # Verify NO stack property (grouped bars)
    for series in option["series"]:
        assert "stack" not in series or series.get("stack") is None, \
            "Grouped bars should NOT have stack property"
    
    print("[PASS] Fallback grouped bar working")
    print(f"   Number of series: {len(option['series'])}")
    print(f"   Has stack property: {any('stack' in s for s in option['series'])}")


def test_smooth_line_chart():
    """Test smooth line chart variant"""
    print("\n" + "="*60)
    print("TEST 5: Smooth Line Chart")
    print("="*60)
    
    chart_data = {
        "data": [
            {"time": "2020", "value": 100},
            {"time": "2021", "value": 150},
            {"time": "2022", "value": 200}
        ],
        "smooth": True,
        "title": "EV Growth Over Time"
    }
    
    echarts_option = generate_fallback_option("line", chart_data)
    option = json.loads(echarts_option)
    
    # Verify smooth property
    assert option["series"][0].get("smooth") == True, "Line should be smooth"
    
    print("[PASS] Smooth line chart working")
    print(f"   Smooth: {option['series'][0].get('smooth')}")


def test_donut_pie_chart():
    """Test donut pie chart variant"""
    print("\n" + "="*60)
    print("TEST 6: Donut Pie Chart")
    print("="*60)
    
    chart_data = {
        "data": [
            {"category": "BEV", "value": 70000},
            {"category": "PHEV", "value": 30000}
        ],
        "innerRadius": 0.6,
        "title": "Vehicle Type Distribution"
    }
    
    echarts_option = generate_fallback_option("pie", chart_data)
    option = json.loads(echarts_option)
    
    # Verify radius is array (donut)
    radius = option["series"][0]["radius"]
    assert isinstance(radius, list), "Donut should have radius as array"
    assert len(radius) == 2, "Radius should have inner and outer values"
    
    print("[PASS] Donut pie chart working")
    print(f"   Radius: {radius}")


def test_sql_data_parsing():
    """Test SQL data parsing with multiple columns"""
    print("\n" + "="*60)
    print("TEST 7: SQL Data Parsing")
    print("="*60)
    
    # Test with list of dicts (typical format)
    sql_data = [
        {"County": "King", "Type": "BEV", "Count": 5000},
        {"County": "Pierce", "Type": "PHEV", "Count": 2000}
    ]
    
    result = parse_sql_results(sql_data)
    
    assert isinstance(result, list), "Should return list"
    assert len(result) == 2, "Should have 2 rows"
    assert "County" in result[0], "Should preserve column names"
    
    print("[PASS] SQL data parsing working")
    print(f"   Parsed {len(result)} rows")
    print(f"   Columns: {list(result[0].keys())}")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("STACKED/GROUPED CHARTS - VALIDATION TESTS")
    print("="*60)
    
    try:
        test_variant_detection()
        test_grouped_data_preparation()
        test_fallback_stacked_bar()
        test_fallback_grouped_bar()
        test_smooth_line_chart()
        test_donut_pie_chart()
        test_sql_data_parsing()
        
        print("\n" + "="*60)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("="*60)
        print("\nThe implementation is working correctly.")
        print("Stacked/grouped charts are now supported!")
        print("\nNext step: Test with real application:")
        print("1. Start backend: python -m src.api")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Try the prompts in STACKED_CHARTS_TEST_GUIDE.md")
        print("="*60 + "\n")
        
        return True
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {str(e)}")
        return False
    except Exception as e:
        print(f"\n[ERROR] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

