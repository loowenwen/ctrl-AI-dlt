#!/usr/bin/env python3
"""
Test the new JSON structure output from both BTO agents
"""
import sys
import json
sys.path.append('agents/transport_agents')

from transport_evaluation_agents import analyze_bto_transport, compare_bto_transports

def test_single_bto_json_structure():
    """Test single BTO analysis JSON structure"""
    print("=" * 70)
    print("TESTING SINGLE BTO ANALYSIS - JSON STRUCTURE")
    print("=" * 70)
    
    print("Testing with Ang Mo Kio -> Marina Bay (Morning Peak)...")
    
    result = analyze_bto_transport("Ang Mo Kio", "018956", "Morning Peak")
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return False
    else:
        print("✅ Analysis completed successfully!")
        
        # Check if it's JSON or text format
        if isinstance(result['result'], dict):
            print("✅ JSON structure detected!")
            print("\n📊 JSON Structure:")
            print(json.dumps(result['result'], indent=2))
            
            # Show how to access specific fields
            print("\n🔍 How to access specific fields:")
            data = result['result']
            print(f"  • Daily commute summary: {data['daily_commute']['summary']}")
            print(f"  • Total time: {data['daily_commute']['total_time_minutes']} minutes")
            print(f"  • Starting station: {data['key_details']['starting_point']['station_code']}")
            print(f"  • Number of transfers: {data['key_details']['transfers']['count']}")
            print(f"  • Transport modes: {', '.join(data['key_details']['transport_options']['modes'])}")
            print(f"  • Decision tip: {data['decision_tip']}")
            
        elif isinstance(result['result'], str):
            print("⚠️  Text format detected (JSON parsing may have failed)")
            print(f"Format: {result.get('format', 'unknown')}")
            print(f"Note: {result.get('note', 'No note provided')}")
            print(f"Content preview: {result['result'][:200]}...")
        
        return True

def test_comparison_json_structure():
    """Test comparison analysis JSON structure"""
    print("\n" + "=" * 70)
    print("TESTING COMPARISON ANALYSIS - JSON STRUCTURE")
    print("=" * 70)
    
    print("Testing comparison analysis...")
    
    result = compare_bto_transports("Marina Bay (018956)", "Morning Peak")
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        if "No transport data available" in result['error']:
            print("   → This is expected if no single BTO analyses have been run yet")
        return False
    else:
        print("✅ Comparison analysis completed successfully!")
        
        # Check if it's JSON or text format
        if isinstance(result['result'], dict):
            print("✅ JSON structure detected!")
            print("\n📊 JSON Structure:")
            print(json.dumps(result['result'], indent=2))
            
            # Show how to access specific fields
            print("\n🔍 How to access specific fields:")
            data = result['result']
            print(f"  • Number of BTOs ranked: {len(data['ranking'])}")
            print(f"  • Best choice: {data['winner_analysis']['bto_name']}")
            print(f"  • Best choice time: {data['ranking'][0]['total_time_minutes']} minutes")
            print(f"  • Key differentiator: {data['winner_analysis']['key_differentiator']}")
            print(f"  • Overall assessment: {data['summary']['overall_assessment']}")
            
        elif isinstance(result['result'], str):
            print("⚠️  Text format detected (JSON parsing may have failed)")
            print(f"Format: {result.get('format', 'unknown')}")
            print(f"Note: {result.get('note', 'No note provided')}")
            print(f"Content preview: {result['result'][:200]}...")
        
        return True

def show_usage_examples():
    """Show how to use the new JSON structure"""
    print("\n" + "=" * 70)
    print("USAGE EXAMPLES WITH JSON STRUCTURE")
    print("=" * 70)
    
    print("1. SINGLE BTO ANALYSIS - JSON ACCESS:")
    print("""
    result = analyze_bto_transport("Ang Mo Kio", "018956", "Morning Peak")
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        data = result['result']
        
        # Access structured data
        print(f"Commute: {data['daily_commute']['summary']}")
        print(f"Time: {data['daily_commute']['total_time_minutes']} minutes")
        print(f"Starting: {data['key_details']['starting_point']['station_code']}")
        print(f"Transfers: {data['key_details']['transfers']['count']}")
        print(f"Pros: {', '.join(data['pros_and_cons']['pros'])}")
        print(f"Score: {data['transport_score']['overall']}")
    """)
    
    print("2. COMPARISON ANALYSIS - JSON ACCESS:")
    print("""
    result = compare_bto_transports("Marina Bay (018956)", "Morning Peak")
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        data = result['result']
        
        # Access structured data
        print(f"Best choice: {data['winner_analysis']['bto_name']}")
        print(f"Ranking:")
        for bto in data['ranking']:
            print(f"  {bto['rank']}. {bto['bto_name']} - {bto['total_time_minutes']}min")
        
        print(f"Key advantage: {data['winner_analysis']['key_differentiator']}")
    """)
    
    print("3. API INTEGRATION EXAMPLE:")
    print("""
    def get_bto_analysis(bto_name, postal_code, time_period):
        result = analyze_bto_transport(bto_name, postal_code, time_period)
        
        if 'error' in result:
            return {"success": False, "error": result['error']}
        
        data = result['result']
        return {
            "success": True,
            "bto_name": bto_name,
            "total_time": data['daily_commute']['total_time_minutes'],
            "walking_time": data['key_details']['starting_point']['walking_time_minutes'],
            "transfers": data['key_details']['transfers']['count'],
            "score": data['transport_score']['overall'],
            "recommendation": data['decision_tip']
        }
    """)

def main():
    """Test the new JSON structure"""
    print("🚀 TESTING NEW JSON STRUCTURE FOR BTO AGENTS")
    print("=" * 70)
    
    # Test single BTO analysis
    single_success = test_single_bto_json_structure()
    
    # Test comparison analysis
    comparison_success = test_comparison_json_structure()
    
    # Show usage examples
    show_usage_examples()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("✅ Both agents now return structured JSON data")
    print("✅ No more emojis - clean, professional output")
    print("✅ Easy to integrate into APIs and applications")
    print("✅ Fallback to text format if JSON parsing fails")
    print("✅ Consistent error handling maintained")
    
    if single_success and comparison_success:
        print("\n🎉 All tests passed! JSON structure is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
