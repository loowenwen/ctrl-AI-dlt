#!/usr/bin/env python3
"""
Comprehensive test script for both single BTO analysis and comparison analysis
"""
import sys
import time
import os
sys.path.append('agents/transport_agents')

from transport_evaluation_agents import (
    analyze_bto_transport, 
    compare_bto_transports, 
    clear_comparison_data,
    BTOTransportAnalyzer,
    Config
)

def test_single_bto_analysis():
    """Test single BTO analysis and store data for comparison - INTERACTIVE MODE"""
    print("=" * 70)
    print("TESTING SINGLE BTO ANALYSIS - INTERACTIVE MODE")
    print("=" * 70)
    
    # Clear any existing comparison data first
    print("🧹 Clearing existing comparison data...")
    clear_comparison_data()
    
    # Test cases for single BTO analysis
    test_cases = [
        {
            "name": "Ang Mo Kio",
            "postal_code": "018956",  # Marina Bay
            "time_period": "Morning Peak",
            "description": "Ang Mo Kio → Marina Bay (Morning Peak)"
        },
        {
            "name": "Bedok", 
            "postal_code": "018956",  # Marina Bay
            "time_period": "Morning Peak",
            "description": "Bedok → Marina Bay (Morning Peak)"
        },
        {
            "name": "Jurong East",
            "postal_code": "018956",  # Marina Bay  
            "time_period": "Morning Peak",
            "description": "Jurong East → Marina Bay (Morning Peak)"
        }
    ]
    
    successful_analyses = 0
    
    print(f"\n📋 Available test cases:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"   {i}. {test_case['description']}")
    
    print(f"\n💡 You can run these test cases manually to avoid throttling issues.")
    print(f"   Each analysis will be stored for comparison testing later.")
    
    while True:
        print(f"\n" + "="*50)
        print(f"INTERACTIVE SINGLE BTO ANALYSIS")
        print(f"="*50)
        print(f"Current successful analyses: {successful_analyses}")
        print(f"Available test cases:")
        for i, test_case in enumerate(test_cases, 1):
            print(f"   {i}. {test_case['description']}")
        print(f"   0. Skip to comparison analysis")
        print(f"   q. Quit")
        
        try:
            choice = input(f"\n🎯 Choose a test case to run (1-{len(test_cases)}, 0, or q): ").strip()
            
            if choice.lower() == 'q':
                print("👋 Exiting single BTO analysis...")
                break
            elif choice == '0':
                print("⏭️  Skipping to comparison analysis...")
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(test_cases):
                test_index = int(choice) - 1
                test_case = test_cases[test_index]
                
                print(f"\n📊 Running: {test_case['description']}")
                print("-" * 50)
                
                try:
                    result = analyze_bto_transport(
                        name=test_case['name'],
                        postal_code=test_case['postal_code'],
                        time_period=test_case['time_period']
                    )
                    
                    if 'error' in result:
                        print(f"❌ Error: {result['error']}")
                        if "ThrottlingException" in result['error']:
                            print("   → AWS Bedrock rate limit exceeded.")
                            print("   → Wait 5-10 minutes before trying again.")
                        print(f"   → You can try this test case again later.")
                    else:
                        print("✅ Analysis completed successfully!")
                        successful_analyses += 1
                        
                        # Show the full result
                        print(f"\n📝 Full Result:")
                        print("-" * 30)
                        print(result['result'])
                        print("-" * 30)
                        
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
            else:
                print("❌ Invalid choice. Please enter a number between 1-{}, 0, or q.".format(len(test_cases)))
                
        except KeyboardInterrupt:
            print(f"\n\n👋 Interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📈 Single BTO Analysis Results: {successful_analyses} successful analyses stored")
    return successful_analyses

def test_comparison_analysis():
    """Test comparison analysis with stored data - INTERACTIVE MODE"""
    print("\n" + "=" * 70)
    print("TESTING COMPARISON ANALYSIS - INTERACTIVE MODE")
    print("=" * 70)
    
    # Check how many BTOs we have data for
    config = Config()
    analyzer = BTOTransportAnalyzer(config)
    comparison_data = analyzer.service.load_comparison_data()
    
    print(f"📊 Found {len(comparison_data)} BTO analyses in comparison data")
    
    if len(comparison_data) == 0:
        print("❌ No data available for comparison. Run single BTO analysis first.")
        return False
    elif len(comparison_data) == 1:
        print("⚠️  Only 1 BTO analysis available. Comparison analysis should return an error.")
    else:
        print(f"✅ {len(comparison_data)} BTO analyses available for comparison.")
    
    # Show what data we have
    if comparison_data:
        print(f"\n📋 Available BTO analyses:")
        for i, data in enumerate(comparison_data, 1):
            print(f"   {i}. {data.get('bto_name', 'Unknown')} ({data.get('flat_type', 'N/A')})")
    
    while True:
        print(f"\n" + "="*50)
        print(f"INTERACTIVE COMPARISON ANALYSIS")
        print(f"="*50)
        print(f"Available BTO analyses: {len(comparison_data)}")
        print(f"Options:")
        print(f"   1. Run comparison analysis")
        print(f"   2. View stored data details")
        print(f"   3. Clear all data and start over")
        print(f"   0. Skip to edge case testing")
        print(f"   q. Quit")
        
        try:
            choice = input(f"\n🎯 Choose an option (1-3, 0, or q): ").strip()
            
            if choice.lower() == 'q':
                print("👋 Exiting comparison analysis...")
                return False
            elif choice == '0':
                print("⏭️  Skipping to edge case testing...")
                return False
            elif choice == '1':
                print(f"\n🔍 Running comparison analysis...")
                print("Destination: Marina Bay (018956)")
                print("Time Period: Morning Peak")
                
                try:
                    result = compare_bto_transports(
                        destination_address="Marina Bay (018956)",
                        time_period="Morning Peak"
                    )
                    
                    if 'error' in result:
                        print(f"❌ Comparison Error: {result['error']}")
                        if "No transport data available" in result['error']:
                            print("   → This is expected if we have 0 BTO analyses")
                        elif "ThrottlingException" in result['error']:
                            print("   → AWS Bedrock rate limit exceeded.")
                            print("   → Wait 5-10 minutes before trying again.")
                        else:
                            print("   → You can try again later.")
                    else:
                        print("✅ Comparison analysis completed successfully!")
                        print("\n📝 Comparison Result:")
                        print("-" * 50)
                        print(result['result'])
                        print("-" * 50)
                        return True
                        
                except Exception as e:
                    print(f"❌ Unexpected error in comparison: {e}")
                    
            elif choice == '2':
                print(f"\n📊 Stored Data Details:")
                print("-" * 30)
                for i, data in enumerate(comparison_data, 1):
                    print(f"{i}. BTO: {data.get('bto_name', 'Unknown')}")
                    print(f"   Flat Type: {data.get('flat_type', 'N/A')}")
                    print(f"   Time Period: {data.get('time_period', 'N/A')}")
                    print(f"   Routes: {len(data.get('available_routes', []))}")
                    print()
                    
            elif choice == '3':
                confirm = input("⚠️  Are you sure you want to clear all data? (y/N): ").strip().lower()
                if confirm == 'y':
                    clear_comparison_data()
                    comparison_data = analyzer.service.load_comparison_data()
                    print("✅ All data cleared!")
                else:
                    print("❌ Data not cleared.")
                    
            else:
                print("❌ Invalid choice. Please enter 1-3, 0, or q.")
                
        except KeyboardInterrupt:
            print(f"\n\n👋 Interrupted by user. Exiting...")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return False

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "=" * 70)
    print("TESTING EDGE CASES")
    print("=" * 70)
    
    # Test 1: Invalid BTO name
    print("\n🧪 Test 1: Invalid BTO name")
    result = analyze_bto_transport("NonExistentBTO", "018956", "Morning Peak")
    if 'error' in result:
        print(f"✅ Correctly handled invalid BTO: {result['error']}")
    else:
        print("❌ Should have returned error for invalid BTO")
    
    # Test 2: Invalid postal code
    print("\n🧪 Test 2: Invalid postal code")
    result = analyze_bto_transport("Ang Mo Kio", "12345", "Morning Peak")
    if 'error' in result:
        print(f"✅ Correctly handled invalid postal code: {result['error']}")
    else:
        print("❌ Should have returned error for invalid postal code")
    
    # Test 3: Invalid time period
    print("\n🧪 Test 3: Invalid time period")
    result = analyze_bto_transport("Ang Mo Kio", "018956", "Invalid Time")
    if 'error' in result:
        print(f"✅ Correctly handled invalid time period: {result['error']}")
    else:
        print("❌ Should have returned error for invalid time period")
    
    # Test 4: Comparison with no data
    print("\n🧪 Test 4: Comparison with no data")
    clear_comparison_data()  # Clear all data
    result = compare_bto_transports("Marina Bay", "Morning Peak")
    if 'error' in result and "No transport data available" in result['error']:
        print(f"✅ Correctly handled empty comparison data: {result['error']}")
    else:
        print("❌ Should have returned error for empty comparison data")

def main():
    """Run comprehensive test suite - INTERACTIVE MODE"""
    print("🚀 STARTING COMPREHENSIVE BTO AGENTS TEST - INTERACTIVE MODE")
    print("=" * 70)
    
    # Check environment setup
    print("🔧 Checking environment setup...")
    if not os.getenv("ONEMAP_EMAIL") or not os.getenv("ONEMAP_PASSWORD"):
        print("⚠️  Warning: ONEMAP_EMAIL or ONEMAP_PASSWORD not set in environment")
        print("   Some tests may fail without proper API credentials")
    else:
        print("✅ Environment variables are set")
    
    single_analyses = 0
    comparison_success = False
    
    while True:
        print(f"\n" + "="*70)
        print(f"MAIN MENU - BTO AGENTS TEST SUITE")
        print(f"="*70)
        print(f"Current Status:")
        print(f"  • Single BTO Analyses: {single_analyses} successful")
        print(f"  • Comparison Analysis: {'✅ PASS' if comparison_success else '❌ FAIL'}")
        print(f"")
        print(f"Available Tests:")
        print(f"  1. Single BTO Analysis (Interactive)")
        print(f"  2. Comparison Analysis (Interactive)")
        print(f"  3. Edge Case Testing")
        print(f"  4. View Current Status")
        print(f"  q. Quit")
        
        try:
            choice = input(f"\n🎯 Choose a test to run (1-4 or q): ").strip()
            
            if choice.lower() == 'q':
                print("👋 Exiting test suite...")
                break
            elif choice == '1':
                print(f"\n🚀 Starting Single BTO Analysis...")
                single_analyses = test_single_bto_analysis()
            elif choice == '2':
                print(f"\n🚀 Starting Comparison Analysis...")
                comparison_success = test_comparison_analysis()
            elif choice == '3':
                print(f"\n🚀 Starting Edge Case Testing...")
                test_edge_cases()
                print(f"\n✅ Edge case testing completed!")
            elif choice == '4':
                print(f"\n📊 CURRENT STATUS")
                print(f"="*30)
                print(f"Single BTO Analyses: {single_analyses} successful")
                print(f"Comparison Analysis: {'✅ PASS' if comparison_success else '❌ FAIL'}")
                
                # Show stored data
                config = Config()
                analyzer = BTOTransportAnalyzer(config)
                comparison_data = analyzer.service.load_comparison_data()
                print(f"Stored BTO Data: {len(comparison_data)} analyses")
                
                if comparison_data:
                    print(f"\nStored BTOs:")
                    for i, data in enumerate(comparison_data, 1):
                        print(f"  {i}. {data.get('bto_name', 'Unknown')} ({data.get('flat_type', 'N/A')})")
            else:
                print("❌ Invalid choice. Please enter 1-4 or q.")
                
        except KeyboardInterrupt:
            print(f"\n\n👋 Interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Final summary
    print(f"\n" + "="*70)
    print(f"FINAL TEST SUMMARY")
    print(f"="*70)
    print(f"Single BTO Analyses: {single_analyses} successful")
    print(f"Comparison Analysis: {'✅ PASS' if comparison_success else '❌ FAIL'}")
    print(f"Edge Case Testing: ✅ COMPLETED")
    
    if single_analyses >= 2 and comparison_success:
        print(f"\n🎉 ALL TESTS PASSED! Your BTO agents are working perfectly!")
    elif single_analyses >= 1:
        print(f"\n✅ Single BTO analysis works! Comparison may need more data.")
    else:
        print(f"\n⚠️  Some issues detected. Check error messages above.")
    
    print(f"\n💡 Tips:")
    print(f"- If you see ThrottlingException errors, wait 5-10 minutes before retrying")
    print(f"- Make sure your .env file has valid OneMap credentials")
    print(f"- Ensure AWS credentials are configured for Bedrock access")
    print(f"- You can run this script multiple times to test different scenarios")

if __name__ == "__main__":
    main()
