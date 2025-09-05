#!/usr/bin/env python3
"""
Test script for the Enhanced BTO Cost Estimator using your specific data format
"""

import pandas as pd
from bto_cost_estimator_agent import EnhancedBTOCostEstimator
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)

def create_sample_data():
    """Create a sample CSV file matching your format for testing"""
    sample_data = [
        {
            'exercise': 'Feb 2025',
            'project_type': 'standard projects', 
            'project': 'woodlands north verge',
            'waiting_time': '47/48',
            'flat_type': '2-room flexi',
            'estimated_floor_area': 40.0,
            'estimated_internal_floor_area': 38.0,
            'units': 67,
            'min_price': 140000,
            'max_price': 204000,
            'exercise_date': '2025-02-01',
            'avg_price': 172000.0,
            'avg_floor_area': 39.0
        },
        # Add more sample data for testing
        {
            'exercise': 'May 2024',
            'project_type': 'standard projects',
            'project': 'toa payoh bidadari',
            'waiting_time': '36/40',
            'flat_type': '4-room',
            'estimated_floor_area': 93.0,
            'estimated_internal_floor_area': 70.0,
            'units': 150,
            'min_price': 520000,
            'max_price': 580000,
            'exercise_date': '2024-05-01',
            'avg_price': 550000.0,
            'avg_floor_area': 81.5
        },
        {
            'exercise': 'Aug 2024',
            'project_type': 'plus projects',
            'project': 'kallang riverside',
            'waiting_time': '30/32',
            'flat_type': '3-room',
            'estimated_floor_area': 67.0,
            'estimated_internal_floor_area': 55.0,
            'units': 80,
            'min_price': 420000,
            'max_price': 480000,
            'exercise_date': '2024-08-01',
            'avg_price': 450000.0,
            'avg_floor_area': 61.0
        },
        {
            'exercise': 'Nov 2024',
            'project_type': 'prime projects',
            'project': 'queenstown peak',
            'waiting_time': '25/28',
            'flat_type': '4-room',
            'estimated_floor_area': 93.0,
            'estimated_internal_floor_area': 70.0,
            'units': 45,
            'min_price': 720000,
            'max_price': 850000,
            'exercise_date': '2024-11-01',
            'avg_price': 785000.0,
            'avg_floor_area': 81.5
        }
    ]
    
    df = pd.DataFrame(sample_data)
    df.to_csv('sample_bto_data.csv', index=False)
    print("Created sample_bto_data.csv for testing")
    return 'sample_bto_data.csv'

def test_estimator_with_your_data_format(csv_path):
    """Test the estimator with your data format"""
    
    print("\n" + "="*60)
    print("TESTING BTO ESTIMATOR WITH YOUR DATA FORMAT")
    print("="*60)
    
    try:
        # Initialize the estimator
        estimator = EnhancedBTOCostEstimator(csv_path)
        
        # Test 1: Estimate for a location that exists in the data
        print("\n📊 TEST 1: Existing location estimation")
        print("-" * 40)
        
        estimate1 = estimator.estimate_cost(
            project_location="woodlands",  # Part of "woodlands north verge"
            flat_type="2-room flexi",
            exercise_date="2025-10-01"
        )
        
        print(f"Location: {estimate1.project_location}")
        print(f"Flat Type: {estimate1.flat_type}")
        print(f"Project Tier: {estimate1.project_tier}")
        print(f"Sample Size: {estimate1.sample_size}")
        if estimate1.estimated_price:
            print(f"Estimated Price: ${estimate1.estimated_price:,.0f}")
            if estimate1.confidence_interval[0] and estimate1.confidence_interval[1]:
                lower, upper = estimate1.confidence_interval
                print(f"95% CI: ${lower:,.0f} - ${upper:,.0f}")
            print(f"Trend: {estimate1.historical_trend}")
        
        # Test 2: Estimate for different flat types in same tier
        print("\n📊 TEST 2: Different flat types, same tier")
        print("-" * 40)
        
        flat_types = ["2-room flexi", "3-room", "4-room", "5-room"]
        
        for flat_type in flat_types:
            try:
                estimate = estimator.estimate_cost(
                    project_location="standard projects",  # This should match standard tier
                    flat_type=flat_type,
                    exercise_date="2025-10-01"
                )
                
                price_str = f"${estimate.estimated_price:,.0f}" if estimate.estimated_price else "N/A"
                print(f"{flat_type:<12}: {price_str:<12} (samples: {estimate.sample_size})")
                
            except Exception as e:
                print(f"{flat_type:<12}: Error - {str(e)}")
        
        # Test 3: Test different project tiers
        print("\n📊 TEST 3: Different project tiers")
        print("-" * 40)
        
        tier_locations = [
            ("standard projects", "Standard"),
            ("plus projects", "Plus"), 
            ("prime projects", "Prime")
        ]
        
        for location_hint, expected_tier in tier_locations:
            try:
                estimate = estimator.estimate_cost(
                    project_location=location_hint,
                    flat_type="4-room",
                    exercise_date="2025-10-01"
                )
                
                price_str = f"${estimate.estimated_price:,.0f}" if estimate.estimated_price else "N/A"
                print(f"{expected_tier:<8}: {price_str:<12} (samples: {estimate.sample_size})")
                
            except Exception as e:
                print(f"{expected_tier:<8}: Error - {str(e)}")
        
        # Test 4: Show data processing results
        print("\n📊 TEST 4: Data processing summary")
        print("-" * 40)
        
        df = estimator.df
        print(f"Total records loaded: {len(df)}")
        print(f"Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
        print(f"Unique locations: {df['project_location'].nunique()}")
        print(f"Unique flat types: {df['flat_type'].nunique()}")
        print(f"Project tiers: {df['project_tier'].value_counts().to_dict()}")
        
        print(f"\nPrice ranges by tier:")
        for tier in df['project_tier'].unique():
            tier_data = df[df['project_tier'] == tier]
            min_price = tier_data['median_price'].min()
            max_price = tier_data['median_price'].max()
            avg_price = tier_data['median_price'].mean()
            print(f"  {tier}: ${min_price:,.0f} - ${max_price:,.0f} (avg: ${avg_price:,.0f})")
        
    except Exception as e:
        print(f"❌ Error testing estimator: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_your_data_structure(csv_path):
    """Analyze the structure of your CSV data"""
    
    print("\n" + "="*60)
    print("ANALYZING YOUR DATA STRUCTURE")
    print("="*60)
    
    try:
        df = pd.read_csv(csv_path)
        
        print(f"\n📋 Basic Info:")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        
        print(f"\n📊 Data Types:")
        for col, dtype in df.dtypes.items():
            print(f"  {col}: {dtype}")
        
        print(f"\n📈 Sample Data (first 3 rows):")
        print(df.head(3).to_string())
        
        print(f"\n🏗️ Project Types:")
        if 'project_type' in df.columns:
            print(df['project_type'].value_counts().to_string())
        
        print(f"\n🏠 Flat Types:")
        if 'flat_type' in df.columns:
            print(df['flat_type'].value_counts().to_string())
        
        print(f"\n💰 Price Statistics:")
        if 'avg_price' in df.columns:
            print(df['avg_price'].describe())
        
        print(f"\n📅 Date Range:")
        if 'exercise_date' in df.columns:
            df['exercise_date'] = pd.to_datetime(df['exercise_date'])
            print(f"  From: {df['exercise_date'].min()}")
            print(f"  To: {df['exercise_date'].max()}")
            print(f"  Span: {(df['exercise_date'].max() - df['exercise_date'].min()).days} days")
        
    except Exception as e:
        print(f"❌ Error analyzing data: {str(e)}")

if __name__ == "__main__":
    print("BTO Cost Estimator Test Suite")
    print("=" * 40)
    
    # Option 1: Test with sample data (if you don't have your CSV ready)
    print("\nOption 1: Test with sample data")
    sample_csv = create_sample_data()
    analyze_your_data_structure(sample_csv)
    test_estimator_with_your_data_format(sample_csv)
    
    # Option 2: Test with your actual CSV (uncomment and modify path)
    # print("\nOption 2: Test with your actual CSV")
    # your_csv_path = "path/to/your/bto_data.csv"
    # analyze_your_data_structure(your_csv_path)
    # test_estimator_with_your_data_format(your_csv_path)