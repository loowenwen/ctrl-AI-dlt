from dotenv import load_dotenv
load_dotenv()

import os
import json
import boto3
import requests
from strands import Agent
from strands.models import BedrockModel

def get_auth_token():
    email = os.getenv("ONEMAP_EMAIL")
    password = os.getenv("ONEMAP_PASSWORD")
    if not email or not password:
        raise Exception("ONEMAP_EMAIL or ONEMAP_PASSWORD not set")
    
    auth_url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    response = requests.post(auth_url, json={"email": email, "password": password})
    
    auth_url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    response = requests.post(auth_url, json={"email": email, "password": password})
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to authenticate: {response.status_code}")


def get_nearest_mrt_walking_time(lat, lon):
    token = get_auth_token()
    url = "https://www.onemap.gov.sg/api/public/nearbysvc/getNearestMrtStops"
    params = {"latitude": lat, "longitude": lon, "radius_in_meters": 2000}
    headers = {"Authorization": token}
    
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    
    if not data:
        return None
    
    nearest = data[0]
    walking_time = 5  
    return {"name": nearest["name"], "road": nearest["road"], "walking_time_min": walking_time}


def get_dummy_bto_locations():
    """Return comprehensive dummy BTO location data"""
    return [
        {"name": "Punggol North", "lat": 1.4045, "lon": 103.9010, "launch_date": "2024", "price_range": "$300k-$500k"},
        {"name": "Jurong East", "lat": 1.3345, "lon": 103.7420, "launch_date": "2024", "price_range": "$400k-$600k"},
        {"name": "Tampines", "lat": 1.3530, "lon": 103.9450, "launch_date": "2024", "price_range": "$350k-$550k"},
        {"name": "Woodlands", "lat": 1.4361, "lon": 103.7860, "launch_date": "2024", "price_range": "$320k-$480k"},
        {"name": "Sengkang", "lat": 1.3980, "lon": 103.8950, "launch_date": "2024", "price_range": "$330k-$520k"},
        {"name": "Punggol South", "lat": 1.3950, "lon": 103.9050, "launch_date": "2024", "price_range": "$310k-$490k"},
        {"name": "Jurong West", "lat": 1.3400, "lon": 103.7000, "launch_date": "2024", "price_range": "$380k-$580k"},
        {"name": "Tampines North", "lat": 1.3600, "lon": 103.9500, "launch_date": "2024", "price_range": "$370k-$570k"},
        {"name": "Woodlands North", "lat": 1.4500, "lon": 103.7800, "launch_date": "2024", "price_range": "$300k-$480k"},
        {"name": "Sengkang East", "lat": 1.4000, "lon": 103.9000, "launch_date": "2024", "price_range": "$340k-$540k"},
        {"name": "Punggol Central", "lat": 1.4100, "lon": 103.8900, "launch_date": "2024", "price_range": "$320k-$500k"},
        {"name": "Jurong Central", "lat": 1.3300, "lon": 103.7500, "launch_date": "2024", "price_range": "$420k-$620k"},
        {"name": "Tampines Central", "lat": 1.3500, "lon": 103.9400, "launch_date": "2024", "price_range": "$360k-$560k"},
        {"name": "Woodlands Central", "lat": 1.4400, "lon": 103.7900, "launch_date": "2024", "price_range": "$310k-$490k"},
        {"name": "Sengkang Central", "lat": 1.3950, "lon": 103.8900, "launch_date": "2024", "price_range": "$350k-$550k"}
    ]


def get_personalized_destinations():
    """Interactive function to get personalized destinations based on user profile"""
    print("\n" + "="*60)
    print("🎯 PERSONALIZED DESTINATION RECOMMENDATION")
    print("="*60)
    
    #Ask the user some questions
    print("\nLet me understand your lifestyle to recommend the best destinations:")
    
    #Work-related
    work_sector = input("What industry do you work in? (e.g., Finance, Tech, Healthcare, Education): ").strip()
    work_preference = input("Do you prefer working in CBD or industrial areas? (CBD/Industrial/Both): ").strip()
    
    #lifestyle
    age_group = input("What's your age group? (20s/30s/40s/50s+): ").strip()
    family_status = input("Are you single, married, or have children? (Single/Married/With Kids): ").strip()
    
    #transportation preference
    transport_mode = input("How do you prefer to commute? (MRT/Bus/Car/Bicycle): ").strip()
    
    #get the AI to generate personalised destination list
    prompt = f"""
    Based on this user profile, recommend 5-7 personalized destinations in Singapore:
    - Industry: {work_sector}
    - Work preference: {work_preference}
    - Age group: {age_group}
    - Family status: {family_status}
    - Transport mode: {transport_mode}
    
    Consider:
    1. Work opportunities in their industry
    2. Lifestyle amenities suitable for their age/family status
    3. Transportation accessibility
    4. Popular areas for their demographic
    
    Return only a JSON array of destination names, no explanations or markdown formatting.
    """
    
    destinations = call_bedrock(prompt)
    
    # Try to parse JSON, fallback to hardcoded if parsing fails
    try:
        import re
        # First try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', destinations, re.DOTALL)
        if json_match:
            destinations_list = json.loads(json_match.group(1))
        else:
            # Try to find just the JSON array
            json_match = re.search(r'\[.*?\]', destinations, re.DOTALL)
            if json_match:
                destinations_list = json.loads(json_match.group())
            else:
                # Try direct parsing
                destinations_list = json.loads(destinations)
        
        print(f"✅ Successfully parsed AI recommendations: {destinations_list}")
        
    except Exception as e:
        print(f"AI parsing failed: {e}")
        print("Using fallback destinations...")
        destinations_list = [
            "CBD", "Woodlands", "Changi Business Park", "Jurong Industrial Park", 
            "Changi Airport", "One-North", "Marina Bay", "Sentosa"
        ]
    
    return destinations_list


def call_bedrock(prompt):
    """Use Strands BedrockModel for AI responses"""
    bedrock_model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        temperature=0.7,
        region_name="us-east-1"
    )
    
    agent = Agent(model=bedrock_model, system_prompt="You are a helpful assistant that provides clear, concise responses.")
    
    try:
        response = agent(prompt)
        return response
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return f"Error: {str(e)}"


def agentic_bto_ranking(choice_index, bto_locations, destinations):
    """Enhanced BTO ranking with more detailed analysis"""
    choice = destinations[choice_index - 1]
    
    print(f"\n🔍 Analyzing BTO locations for commuting to {choice}...")
    
    bto_scores = []
    for bto in bto_locations:
        mrt_info = get_nearest_mrt_walking_time(bto["lat"], bto["lon"])
        walking_time = mrt_info["walking_time_min"] if mrt_info else 999
        
    
        accessibility_score = max(0, 100 - (walking_time * 10))  # Higher score for shorter walking time
        
        bto_scores.append({
            "name": bto["name"], 
            "walking_time": walking_time,
            "accessibility_score": accessibility_score,
            "price_range": bto["price_range"],
            "launch_date": bto["launch_date"]
        })
    
    # Enhanced prompt for better analysis
    prompt = f"""
    Analyze and rank these BTO locations for commuting to {choice}:
    
    BTO Locations with details:
    {json.dumps(bto_scores, indent=2)}
    
    Provide:
    1. A ranked list (1st, 2nd, 3rd...) with scores out of 100
    2. Brief explanation for each ranking considering:
       - Walking time to MRT/bus stops
       - Accessibility score
       - Price range affordability
       - Launch date (newer projects might be preferred)
    3. Overall recommendation for the best location
    4. Consider walking time, accessibility, and commute convenience
    
    Format your response clearly with rankings and explanations.
    """
    
    llm_output = call_bedrock(prompt)
    return llm_output


def main():
    """Main function with enhanced user experience"""
    print("🏠 BTO LOCATION ANALYZER & RECOMMENDER")
    print("="*60)
    
    
    print("\n🏘️ Loading BTO location data...")
    bto_locations = get_dummy_bto_locations()
    print(f"Loaded {len(bto_locations)} BTO locations:")
    for i, bto in enumerate(bto_locations[:5], 1):  # Show first 5
        print(f"  {i}. {bto['name']} - {bto['price_range']}")
    if len(bto_locations) > 5:
        print(f"  ... and {len(bto_locations) - 5} more locations")
    
    #Get personalized destinations
    destinations = get_personalized_destinations()
    
    
    print(f"\n🎯 Based on your profile, here are recommended destinations:")
    for i, dest in enumerate(destinations, 1):
        print(f"{i}. {dest}")
    

    while True:
        try:
            choice = int(input(f"\nEnter destination number (1-{len(destinations)}): "))
            if 1 <= choice <= len(destinations):
                break
            else:
                print(f"Please enter a number between 1 and {len(destinations)}")
        except ValueError:
            print("Please enter a valid number")
    
    
    print("\n🤖 Generating AI-powered BTO analysis...")
    result = agentic_bto_ranking(choice, bto_locations, destinations)
    
    print("\n" + "="*60)
    print("�� BTO RANKINGS & RECOMMENDATIONS")
    print("="*60)
    print(result)


if __name__ == "__main__":
    main()
