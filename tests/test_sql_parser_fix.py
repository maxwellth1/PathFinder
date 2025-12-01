"""
Test SQL Parser Fix for Tuple String Format
Validates that the parser correctly handles tuple strings with SQL column extraction
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.echarts import extract_column_names_from_sql, parse_sql_results
import json


def test_extract_column_names():
    """Test extracting column names from SQL query"""
    print("\n" + "="*60)
    print("TEST 1: Extract Column Names from SQL")
    print("="*60)
    
    # Test case from user's terminal output
    sql_query = """SELECT [Legislative District], [Electric Vehicle Type], COUNT(*) AS vehicle_count
FROM Electric_Vehicle_Population_Data
GROUP BY [Legislative District], [Electric Vehicle Type]
ORDER BY [Legislative District]"""
    
    column_names = extract_column_names_from_sql(sql_query)
    
    print(f"SQL Query: {sql_query[:100]}...")
    print(f"Extracted Columns: {column_names}")
    
    assert len(column_names) == 3, f"Expected 3 columns, got {len(column_names)}"
    assert "Legislative District" in column_names, "Should extract 'Legislative District'"
    assert "Electric Vehicle Type" in column_names, "Should extract 'Electric Vehicle Type'"
    assert "vehicle_count" in column_names, "Should extract 'vehicle_count' alias"
    
    print("[PASS] Column extraction working correctly")


def test_parse_tuple_string_with_sql():
    """Test parsing tuple string format with SQL column names"""
    print("\n" + "="*60)
    print("TEST 2: Parse Tuple String with SQL Columns")
    print("="*60)
    
    # Actual data format from user's terminal
    tuple_data = "[(0, 'Battery Electric Vehicle (BEV)', 222), (0, 'Plug-in Hybrid Electric Vehicle (PHEV)', 119), (1, 'Battery Electric Vehicle (BEV)', 5485), (1, 'Plug-in Hybrid Electric Vehicle (PHEV)', 1025)]"
    
    sql_query = "SELECT [Legislative District], [Electric Vehicle Type], COUNT(*) AS vehicle_count FROM Electric_Vehicle_Population_Data GROUP BY [Legislative District], [Electric Vehicle Type]"
    
    result = parse_sql_results(tuple_data, sql_query)
    
    print(f"Input (first 150 chars): {tuple_data[:150]}...")
    print(f"Parsed result (first 2 rows):")
    for row in result[:2]:
        print(f"  {json.dumps(row, indent=2)}")
    
    # Validate results
    assert len(result) > 0, "Should parse data successfully"
    assert isinstance(result, list), "Should return a list"
    assert isinstance(result[0], dict), "Should return list of dicts"
    
    # Check column names
    first_row = result[0]
    assert "Legislative District" in first_row, "Should have 'Legislative District' column"
    assert "Electric Vehicle Type" in first_row, "Should have 'Electric Vehicle Type' column"
    assert "vehicle_count" in first_row, "Should have 'vehicle_count' column"
    
    # Check values
    assert first_row["Legislative District"] == 0, "First district should be 0"
    assert first_row["Electric Vehicle Type"] == "Battery Electric Vehicle (BEV)", "First type should be BEV"
    assert first_row["vehicle_count"] == 222, "First count should be 222"
    
    print("[PASS] Tuple string parsing with SQL columns working correctly")


def test_complex_sql_queries():
    """Test various SQL query formats"""
    print("\n" + "="*60)
    print("TEST 3: Complex SQL Query Formats")
    print("="*60)
    
    test_cases = [
        {
            "name": "Aliased columns",
            "sql": "SELECT County AS region, COUNT(*) AS total FROM EVs GROUP BY County",
            "expected": ["region", "total"]
        },
        {
            "name": "Function with AS",
            "sql": "SELECT Make, AVG(Range) AS avg_range FROM EVs GROUP BY Make",
            "expected": ["Make", "avg_range"]
        },
        {
            "name": "Mixed brackets and AS",
            "sql": "SELECT [County Name], [Vehicle Type], SUM([Count]) AS vehicle_sum FROM Data",
            "expected": ["County Name", "Vehicle Type", "vehicle_sum"]
        }
    ]
    
    for test_case in test_cases:
        columns = extract_column_names_from_sql(test_case["sql"])
        print(f"\n{test_case['name']}:")
        print(f"  SQL: {test_case['sql'][:80]}...")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Got: {columns}")
        
        assert columns == test_case["expected"], f"Mismatch for {test_case['name']}"
    
    print("\n[PASS] Complex SQL query parsing working correctly")


def test_backwards_compatibility():
    """Test that existing functionality still works"""
    print("\n" + "="*60)
    print("TEST 4: Backwards Compatibility")
    print("="*60)
    
    # Test with list of dicts (should pass through unchanged)
    dict_data = [
        {"County": "King", "Count": 5000},
        {"County": "Pierce", "Count": 3000}
    ]
    
    result = parse_sql_results(dict_data, "")
    assert result == dict_data, "List of dicts should pass through unchanged"
    print("[PASS] List of dicts: unchanged")
    
    # Test without SQL query (should use generic names)
    tuple_data = "[(King, 5000), (Pierce, 3000)]"
    result = parse_sql_results(tuple_data, "")
    assert len(result) == 2, "Should parse 2 rows"
    assert "col_0" in result[0] or "County" in result[0], "Should have some column names"
    print("[PASS] Tuple data without SQL: fallback to generic names")
    
    print("\n[PASS] Backwards compatibility maintained")


def run_all_tests():
    """Run all SQL parser tests"""
    print("\n" + "="*60)
    print("SQL PARSER FIX - VALIDATION TESTS")
    print("="*60)
    
    try:
        test_extract_column_names()
        test_parse_tuple_string_with_sql()
        test_complex_sql_queries()
        test_backwards_compatibility()
        
        print("\n" + "="*60)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("="*60)
        print("\nThe SQL parser fix is working correctly.")
        print("Tuple string format with SQL column extraction is functional!")
        print("\nNext: Test with real application")
        print('Try: "Show me a stacked bar chart of vehicle types across different legislative districts"')
        print("="*60 + "\n")
        
        return True
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n[ERROR] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

