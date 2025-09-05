#!/usr/bin/env python3
"""
Analyze the data structures returned by both BTO agents
"""
import sys
import json
sys.path.append('agents/transport_agents')

from transport_evaluation_agents import analyze_bto_transport, compare_bto_transports

def analyze_single_bto_structure():
    """Analyze the data structure returned by single BTO analysis"""
    print("=" * 70)
    print("SINGLE BTO ANALYSIS - DATA STRUCTURE")
    print("=" * 70)
    
    print("Function: analyze_bto_transport(name, postal_code, time_period)")
    print("Return Type: Dict[str, str]")
    print()
    
    print("SUCCESS CASE:")
    print("Structure: {'result': 'AI analysis text'}")
    print("Example:")
    print("""
    {
        "result": "1. **Your Daily Commute**: Walk 13 minutes to bus stop 54359. Take a 26-minute bus and MRT journey with 2 transfers. A 45-minute trip that balances walking and transit time.

2. **Key Details for Your Decision**:
   - **Journey Time**: 45 minutes total
   - **Starting Point**: Bus stop 54359, 869m walk (13 min) - moderate distance, consider umbrella for rainy days
   - **Transfers**: 2 transfers - slightly complex, but manageable with good timing
   - **Transport Options**: Bus and MRT - reliable combination, provides flexibility

3. **Is This BTO Right for You?**:
   • Pro: Multiple route options available, good for adapting to delays
   • Con: Significant initial walk to bus stop may be challenging in bad weather
   • Pro: Direct bus access, reducing dependence on MRT breakdowns

4. **Decision Tip**: Suitable for those who don't mind a bit of walking and can handle multiple transfers in their daily commute."
    }
    """)
    
    print("ERROR CASES:")
    print("Structure: {'error': 'Error message'}")
    print("Examples:")
    print("""
    # Invalid postal code
    {"error": "Postal code must be a 6-digit number"}
    
    # Invalid time period  
    {"error": "Invalid time period: Invalid Time. Choose from ['Morning Peak', 'Evening Peak', 'Daytime Off-Peak', 'Nighttime Off-Peak']"}
    
    # BTO not found
    {"error": "BTO with name 'NonExistentBTO' not found"}
    
    # API throttling
    {"error": "AI analysis failed: An error occurred (ThrottlingException) when calling the InvokeModel operation..."}
    """)

def analyze_comparison_structure():
    """Analyze the data structure returned by comparison analysis"""
    print("\n" + "=" * 70)
    print("COMPARISON ANALYSIS - DATA STRUCTURE")
    print("=" * 70)
    
    print("Function: compare_bto_transports(destination_address, time_period)")
    print("Return Type: Dict[str, str]")
    print()
    
    print("SUCCESS CASE:")
    print("Structure: {'result': 'AI comparison analysis text'}")
    print("Example:")
    print("""
    {
        "result": "## 🏆 RANKING (Best to Worst)
1. **Ang Mo Kio** - 2-Room Flexi, 3-Room, 4-Room - 45min
2. **Bedok** - 2-Room Flexi, 3-Room, 4-Room, 5-Room, 3Gen - 52min
3. **Jurong East** - 2-Room Flexi, 3-Room, 4-Room, 5-Room, 3Gen - 58min

## 🥇 WHY #1 RANKS HIGHEST
**Transport Advantages:**
- **Journey Time**: 45 minutes (vs others: 52min, 58min)
- **Starting Point**: Bus stop 54359 - 13min walk (869m)
- **Transfers**: 2 transfers (vs others: 3, 2)
- **Transport Options**: Bus and MRT - reliable combination
- **Peak Performance**: Handles morning rush well with multiple route options

**Key Differentiator**: Ang Mo Kio offers the shortest total journey time with the most direct route to Marina Bay, requiring fewer transfers than Bedok and better peak hour performance than Jurong East.

## 📊 QUICK COMPARISON
| BTO | Time | Walks | Transfers | Best Route |
|-----|------|-------|-----------|------------|
| Ang Mo Kio | 45min | 13min | 2 | Bus+MRT |
| Bedok | 52min | 8min | 3 | MRT+Bus |
| Jurong East | 58min | 15min | 2 | Bus+MRT |"
    }
    """)
    
    print("ERROR CASES:")
    print("Structure: {'error': 'Error message'}")
    print("Examples:")
    print("""
    # No data available
    {"error": "No transport data available for comparison"}
    
    # Invalid time period
    {"error": "Invalid time period: Invalid Time. Choose from ['Morning Peak', 'Evening Peak', 'Daytime Off-Peak', 'Nighttime Off-Peak']"}
    
    # API throttling
    {"error": "AI analysis failed: An error occurred (ThrottlingException) when calling the InvokeModel operation..."}
    """)

def analyze_internal_data_structures():
    """Analyze the internal data structures used for comparison"""
    print("\n" + "=" * 70)
    print("INTERNAL DATA STRUCTURES")
    print("=" * 70)
    
    print("1. BTO LOCATION DATA (from bto_data.json):")
    print("""
    {
        "name": "Ang Mo Kio",
        "town": "Ang Mo Kio", 
        "flatType": "2-Room Flexi, 3-Room, 4-Room",
        "region": "NORTH-EAST REGION",
        "lat": 1.37723,
        "lon": 103.852517
    }
    """)
    
    print("2. FORMATTED ROUTE DATA (stored for comparison):")
    print("""
    {
        "bto_name": "Ang Mo Kio",
        "flat_type": "3-Room",
        "bto_location": {"lat": 1.37723, "lon": 103.852517},
        "destination": {
            "lat": 1.2966,
            "lon": 103.7764,
            "address": "Marina Bay",
            "postal_code": "018956"
        },
        "time_period": "Morning Peak",
        "available_routes": [
            {
                "route_number": 1,
                "total_duration_minutes": 45.0,
                "walking_time_minutes": 13.0,
                "transit_time_minutes": 32.0,
                "waiting_time_minutes": 0.0,
                "transfers": 2,
                "walk_distance_meters": 869,
                "transport_modes": ["BUS", "RAIL"],
                "route_numbers": ["East-West Line"],
                "first_transport_mode": "BUS",
                "stop_sequence": ["Origin", "54359", "EW16", "EW14", "Destination"],
                "mrt_lines": ["EW"],
                "starting_stop": {
                    "code": "54359",
                    "line": null,
                    "walk_time_min": 13.0
                }
            }
        ],
        "best_route": {
            "route_number": 1,
            "total_duration_minutes": 45.0,
            "walking_time_minutes": 13.0,
            "transit_time_minutes": 32.0,
            "waiting_time_minutes": 0.0,
            "transfers": 2,
            "walk_distance_meters": 869,
            "transport_modes": ["BUS", "RAIL"],
            "route_numbers": ["East-West Line"],
            "first_transport_mode": "BUS",
            "stop_sequence": ["Origin", "54359", "EW16", "EW14", "Destination"],
            "mrt_lines": ["EW"],
            "starting_stop": {
                "code": "54359",
                "line": null,
                "walk_time_min": 13.0
            }
        }
    }
    """)

def show_usage_examples():
    """Show how to use the agents and handle their responses"""
    print("\n" + "=" * 70)
    print("USAGE EXAMPLES")
    print("=" * 70)
    
    print("1. SINGLE BTO ANALYSIS:")
    print("""
    from transport_evaluation_agents import analyze_bto_transport
    
    result = analyze_bto_transport("Ang Mo Kio", "018956", "Morning Peak")
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Analysis: {result['result']}")
    """)
    
    print("2. COMPARISON ANALYSIS:")
    print("""
    from transport_evaluation_agents import compare_bto_transports
    
    result = compare_bto_transports("Marina Bay (018956)", "Morning Peak")
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Comparison: {result['result']}")
    """)
    
    print("3. CHECKING FOR SUCCESS/ERROR:")
    print("""
    # Both agents return the same structure
    def handle_agent_response(response):
        if 'error' in response:
            return False, response['error']
        else:
            return True, response['result']
    
    # Usage
    success, data = handle_agent_response(result)
    if success:
        print(f"Success: {data}")
    else:
        print(f"Error: {data}")
    """)

def main():
    """Analyze all data structures"""
    print("🔍 BTO AGENTS DATA STRUCTURE ANALYSIS")
    print("=" * 70)
    
    analyze_single_bto_structure()
    analyze_comparison_structure()
    analyze_internal_data_structures()
    show_usage_examples()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("✅ Both agents return consistent Dict[str, str] structure")
    print("✅ Success: {'result': 'AI analysis text'}")
    print("✅ Error: {'error': 'Error message'}")
    print("✅ Easy to handle programmatically")
    print("✅ Rich internal data structures for detailed analysis")

if __name__ == "__main__":
    main()
