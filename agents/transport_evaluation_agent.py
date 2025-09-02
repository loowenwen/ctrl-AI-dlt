from dotenv import load_dotenv
load_dotenv()

import os
import json
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

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to authenticate: {response.status_code}")

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

def get_route_data(start: str, end: str, time_period: str):
    """Fetch route data from OneMap API for BTO transport analysis."""
    # Fixed defaults for BTO analysis
    date = "03-24-2025"
    routeType = "pt"
    mode = "TRANSIT"
    maxWalkDistance = 1000
    numItineraries = 3

    # Map human-readable time period → representative time
    time_periods = {
        "Morning Peak (6:30-8:30am)": "07:30:00",
        "Evening Peak (5-7pm)": "18:00:00",
        "Daytime Off-Peak (8:30am-5pm)": "12:00:00",
        "Nighttime Off-Peak (7pm-6:30am)": "20:00:00"
    }

    if time_period not in time_periods:
        raise ValueError(f"Invalid time_period provided: {time_period}")
    time = time_periods[time_period]

    # Use your existing auth function
    token = get_auth_token()

    # Construct request
    base_url = "https://www.onemap.gov.sg/api/public/routingsvc/route"
    params = {
        "start": start,
        "end": end,
        "routeType": routeType,
        "date": date,
        "time": time,
        "mode": mode,
        "maxWalkDistance": maxWalkDistance,
        "numItineraries": numItineraries
    }
    headers = {"Authorization": token}

    response = requests.get(base_url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if "plan" in data and "itineraries" in data["plan"]:
            return data["plan"]["itineraries"]
        else:
            print("Itineraries not found in the response.")
            return None
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

def search_destination(destination_name: str) -> dict:
    """Search for destination coordinates using OneMap search API."""
    token = get_auth_token()
    url = "https://www.onemap.gov.sg/api/common/elastic/search"
    
    params = {
        "searchVal": destination_name,
        "returnGeom": "Y",
        "getAddrDetails": "Y",
        "pageNum": 1
    }
    
    headers = {"Authorization": token}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data.get("found") > 0 and data["results"]:
            result = data["results"][0]  # Get first result
            return {
                "lat": float(result["LATITUDE"]),
                "lon": float(result["LONGITUDE"]),
                "address": result["ADDRESS"]
            }
        
        return None
        
    except Exception as e:
        print(f"Destination search error: {e}")
        return None

def get_transport_data_for_bto(bto_lat: float, bto_lon: float, destination_name: str, time_period: str) -> dict:
    """Get comprehensive transport data for a BTO location."""
    # Search for destination coordinates
    destination_coords = search_destination(destination_name)
    if not destination_coords:
        return {"error": "Destination not found"}
    
    # Get route data
    start_coords = f"{bto_lat},{bto_lon}"
    end_coords = f"{destination_coords['lat']},{destination_coords['lon']}"
    
    routes = get_route_data(start_coords, end_coords, time_period)
    if not routes:
        return {"error": "No routes found"}
    
    return {
        "bto_coordinates": {"lat": bto_lat, "lon": bto_lon},
        "destination": destination_coords,
        "time_period": time_period,
        "routes": routes
    }

def format_route_data_for_ai(transport_data: dict) -> dict:
    """Format complex route data into AI-friendly structure."""
    if "error" in transport_data:
        return transport_data
    
    formatted_routes = []
    
    for i, route in enumerate(transport_data["routes"]):
        # Convert seconds to minutes for readability
        duration_min = round(route["duration"] / 60, 1)
        walk_time_min = round(route["walkTime"] / 60, 1)
        transit_time_min = round(route["transitTime"] / 60, 1)
        waiting_time_min = round(route.get("waitingTime", 0) / 60, 1)
        
        # Extract transport modes and routes
        transport_modes = []
        route_numbers = []
        
        for leg in route["legs"]:
            if leg["mode"] != "WALK":
                transport_modes.append(leg["mode"])
                if leg.get("route"):
                    route_numbers.append(leg["route"])
        
        formatted_route = {
            "route_number": i + 1,
            "total_duration_minutes": duration_min,
            "walking_time_minutes": walk_time_min,
            "transit_time_minutes": transit_time_min,
            "waiting_time_minutes": waiting_time_min,
            "transfers": route["transfers"],
            "walk_distance_meters": route["walkDistance"],
            "fare": route.get("fare", "N/A"),
            "transport_modes": list(set(transport_modes)),
            "route_numbers": list(set(route_numbers)),
            "first_transport_mode": transport_modes[0] if transport_modes else "WALK"
        }
        
        formatted_routes.append(formatted_route)
    
    return {
        "bto_location": transport_data["bto_coordinates"],
        "destination": transport_data["destination"],
        "time_period": transport_data["time_period"],
        "available_routes": formatted_routes,
        "best_route": min(formatted_routes, key=lambda x: x["total_duration_minutes"])
    }

def create_transport_analysis_agent() -> Agent:
    """Create the AI agent for transport analysis."""
    bedrock_model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        temperature=0.7,
        region_name="us-east-1"
    )
    
    system_prompt = """You are a Singapore transport analyst specializing in BTO location evaluation. 

Your expertise includes:
- Analyzing public transport accessibility
- Evaluating journey efficiency and complexity
- Ranking locations by transport convenience
- Providing actionable insights for homebuyers

When analyzing transport data, consider:
1. Total journey time (lower is better)
2. Walking accessibility (shorter walks preferred)
3. Transfer complexity (fewer transfers preferred)
4. Transport mode variety (more options preferred)
5. Time period impact (peak vs off-peak performance)

Provide clear, logical rankings with specific explanations for each BTO location."""

    return Agent(model=bedrock_model, system_prompt=system_prompt)

def select_bto_locations(bto_locations: list) -> list:
    """Let user select which BTOs to analyze."""
    print("\n🏘️ Available BTO Locations:")
    print("-" * 60)
    
    for i, bto in enumerate(bto_locations, 1):
        print(f"{i:2d}. {bto['name']:<20} | {bto['price_range']:<15} | Launch: {bto['launch_date']}")
    
    print(f"\n�� Select up to 3 BTO locations to analyze (enter numbers separated by commas):")
    print("💡 Tip: Choose locations that interest you based on price, area, or launch date")
    
    while True:
        try:
            user_input = input("Enter BTO numbers (e.g., 1,3,5): ").strip()
            
            # Parse comma-separated numbers
            selected_indices = [int(x.strip()) - 1 for x in user_input.split(',')]
            
            # Validate selections
            if len(selected_indices) > 3:
                print("❌ Please select maximum 3 BTOs")
                continue
                
            if any(idx < 0 or idx >= len(bto_locations) for idx in selected_indices):
                print("❌ Invalid BTO number. Please check your selection.")
                continue
            
            # Get selected BTOs
            selected_bto_locations = [bto_locations[idx] for idx in selected_indices]
            
            print(f"\n✅ Selected BTOs for analysis:")
            for i, bto in enumerate(selected_bto_locations, 1):
                print(f"  {i}. {bto['name']} - {bto['price_range']}")
            
            return selected_bto_locations
            
        except ValueError:
            print("❌ Please enter valid numbers separated by commas")
        except Exception as e:
            print(f"❌ Error: {e}")



##Creating the transport analysis agent
def create_transport_analysis_agent() -> Agent:
    """Create the AI agent for transport-only analysis."""
    bedrock_model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        temperature=0.7,
        region_name="us-east-1"
    )
    
    system_prompt = """You are a Singapore public transport specialist focusing ONLY on transport accessibility.

Your expertise is LIMITED to:
- Public transport journey times
- Walking distances to transport nodes
- Transfer complexity and frequency
- Transport mode availability and variety
- Peak vs off-peak transport performance

DO NOT consider:
- Price, affordability, or value
- Neighborhood amenities or lifestyle
- School quality or family factors
- Future development potential
- Any non-transport factors

Provide clear transport rankings based purely on public transport efficiency and accessibility."""

    return Agent(model=bedrock_model, system_prompt=system_prompt)

def analyze_bto_transport(agent: Agent, selected_bto_locations: list, destination_name: str, time_period: str) -> str:
    """Use AI agent to analyze ONLY transport accessibility for selected BTOs."""
    
    #getting the route data 
    all_transport_data = []
    
    for bto in selected_bto_locations:
        print(f"🔍 Analyzing transport for {bto['name']}...")
        
        transport_data = get_transport_data_for_bto(
            bto["lat"], bto["lon"], destination_name, time_period
        )
        
        if "error" not in transport_data:
            formatted_data = format_route_data_for_ai(transport_data)
            formatted_data["bto_name"] = bto["name"]
            # Remove price range since we're not considering it
            all_transport_data.append(formatted_data)
        else:
            print(f"❌ Error getting data for {bto['name']}: {transport_data['error']}")
    
    if not all_transport_data:
        return "No transport data available for the selected BTOs."

    #prompt for transport analysis
    analysis_prompt = f"""
    Analyze ONLY the public transport accessibility for these {len(all_transport_data)} BTO locations commuting to {destination_name} during {time_period}.

    Transport Data:
    {json.dumps(all_transport_data, indent=2)}

    Provide a transport-focused ranking considering ONLY:
    1. Total journey time (lower is better)
    2. Walking accessibility to transport nodes
    3. Transfer complexity and frequency
    4. Transport mode variety and reliability
    5. Peak vs off-peak performance differences

    DO NOT consider price, amenities, or any non-transport factors.
    Focus purely on how easy it is to get from each BTO to the destination using public transport.

    Provide clear rankings with transport-specific explanations.
    """
    
    try:
        response = agent(analysis_prompt)
        return response
    except Exception as e:
        return f"AI analysis failed: {str(e)}"




def main():
    """Main function focused on transport-only analysis"""
    print("🚇 BTO TRANSPORT ACCESSIBILITY ANALYZER")
    print("="*60)
    print("Focus: Public Transport Analysis Only")
    print("="*60)
    
    print("\n🏘️ Loading BTO location data...")
    bto_locations = get_dummy_bto_locations()
    print(f"Loaded {len(bto_locations)} BTO locations")
    
    # Simple destination list
    destinations = [
        "CBD", "Woodlands", "Changi Business Park", "Jurong Industrial Park", 
        "Changi Airport", "One-North", "Marina Bay", "Sentosa"
    ]
    
    print(f"\n🎯 Available destinations:")
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
    
    # Get time period for transport analysis
    print("\n⏰ Choose your typical commute time:")
    time_periods = [
        "Morning Peak (6:30-8:30am)",
        "Evening Peak (5-7pm)", 
        "Daytime Off-Peak (8:30am-5pm)",
        "Nighttime Off-Peak (7pm-6:30am)"
    ]
    
    for i, period in enumerate(time_periods, 1):
        print(f"{i}. {period}")
    
    while True:
        try:
            time_choice = int(input(f"\nEnter your choice (1-{len(time_periods)}): "))
            if 1 <= time_choice <= len(time_periods):
                selected_period = time_periods[time_choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(time_periods)}")
        except ValueError:
            print("Please enter a valid number")
    
    selected_destination = destinations[choice - 1]
    
    # Let user select which BTOs to analyze
    selected_bto_locations = select_bto_locations(bto_locations)
    
    print(f"\n🚇 Analyzing TRANSPORT ACCESSIBILITY for {len(selected_bto_locations)} selected BTOs...")
    print(f"Destination: {selected_destination}")
    print(f"Time Period: {selected_period}")
    print("Focus: Public transport efficiency and accessibility only")
    
    # Create AI agent and analyze transport
    print("\n🤖 AI Transport Specialist is analyzing public transport data...")
    agent = create_transport_analysis_agent()
    analysis_result = analyze_bto_transport(agent, selected_bto_locations, selected_destination, selected_period)
    
    print("\n" + "="*60)
    print("PUBLIC TRANSPORT ACCESSIBILITY ANALYSIS RESULTS")
    print("="*60)
    print("Note: Analysis focuses purely on transport factors")
    print("="*60)
    print(analysis_result)

if __name__ == "__main__":
    main()