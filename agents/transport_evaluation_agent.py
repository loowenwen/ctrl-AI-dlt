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

def load_bto_locations(json_file_path="bto_data.json"):
    """Load BTO location data from a JSON file."""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            bto_data = json.load(f)
        
        # Ensure required fields and add default price_range if missing
        required_fields = ["name", "lat", "lon", "launch_date"]
        processed_data = []
        for bto in bto_data:
            # Check for required fields
            if all(field in bto for field in required_fields):
                # Add default price_range if not present
                if "price_range" not in bto:
                    bto["price_range"] = "$unknown"
                processed_data.append(bto)
            else:
                print(f"Warning: Skipping invalid BTO entry: {bto.get('name', 'Unknown')} (missing required fields)")
        
        if not processed_data:
            raise ValueError("No valid BTO entries found in the JSON file")
        
        print(f"Loaded {len(processed_data)} BTO locations from {json_file_path}")
        return processed_data
    
    except FileNotFoundError:
        print(f"Error: BTO data file '{json_file_path}' not found. Please run bto_launch_websearch_agent.py first.")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON from '{json_file_path}': {e}")
        raise
    except Exception as e:
        print(f"Error loading BTO locations: {e}")
        raise

def get_route_data(start: str, end: str, time_period: str):
    """Fetch route data from OneMap API for BTO transport analysis."""
    date = "03-24-2025"
    routeType = "pt"
    mode = "TRANSIT"
    maxWalkDistance = 1000
    numItineraries = 3

    time_periods = {
        "Morning Peak (6:30-8:30am)": "07:30:00",
        "Evening Peak (5-7pm)": "18:00:00",
        "Daytime Off-Peak (8:30am-5pm)": "12:00:00",
        "Nighttime Off-Peak (7pm-6:30am)": "20:00:00"
    }

    if time_period not in time_periods:
        raise ValueError(f"Invalid time_period provided: {time_period}")
    time = time_periods[time_period]

    token = get_auth_token()
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
            result = data["results"][0]
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
    destination_coords = search_destination(destination_name)
    if not destination_coords:
        return {"error": "Destination not found"}
    
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
        duration_min = round(route["duration"] / 60, 1)
        walk_time_min = round(route["walkTime"] / 60, 1)
        transit_time_min = round(route["transitTime"] / 60, 1)
        waiting_time_min = round(route.get("waitingTime", 0) / 60, 1)
        
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

def select_bto_locations(bto_locations: list) -> list:
    """Let user select which BTOs to analyze."""
    print("\n🏘️ Available BTO Locations:")
    print("-" * 60)
    
    for i, bto in enumerate(bto_locations, 1):
        flat_type = bto.get("flatType", "N/A")
        print(f"{i:2d}. {bto['name']:<20} | {flat_type:<30} | Launch: {bto['launch_date'][:10]}")
    
    print(f"\n🔢 Select up to 3 BTO locations to analyze (enter numbers separated by commas):")
    print("💡 Tip: Choose locations based on area, flat types, or launch date")
    
    while True:
        try:
            user_input = input("Enter BTO numbers (e.g., 1,3,5): ").strip()
            selected_indices = [int(x.strip()) - 1 for x in user_input.split(',')]
            
            if len(selected_indices) > 3:
                print("❌ Please select maximum 3 BTOs")
                continue
                
            if any(idx < 0 or idx >= len(bto_locations) for idx in selected_indices):
                print("❌ Invalid BTO number. Please check your selection.")
                continue
            
            selected_bto_locations = [bto_locations[idx] for idx in selected_indices]
            
            print(f"\n✅ Selected BTOs for analysis:")
            for i, bto in enumerate(selected_bto_locations, 1):
                flat_type = bto.get("flatType", "N/A")
                print(f"  {i}. {bto['name']} - {flat_type}")
            
            return selected_bto_locations
            
        except ValueError:
            print("❌ Please enter valid numbers separated by commas")
        except Exception as e:
            print(f"❌ Error: {e}")

def analyze_bto_transport(agent: Agent, selected_bto_locations: list, destination_name: str, time_period: str) -> str:
    """Use AI agent to analyze ONLY transport accessibility for selected BTOs."""
    all_transport_data = []
    
    for bto in selected_bto_locations:
        print(f"🔍 Analyzing transport for {bto['name']}...")
        
        transport_data = get_transport_data_for_bto(
            bto["lat"], bto["lon"], destination_name, time_period
        )
        
        if "error" not in transport_data:
            formatted_data = format_route_data_for_ai(transport_data)
            formatted_data["bto_name"] = bto["name"]
            formatted_data["flat_type"] = bto.get("flatType", "N/A")
            all_transport_data.append(formatted_data)
        else:
            print(f"❌ Error getting data for {bto['name']}: {transport_data['error']}")
    
    if not all_transport_data:
        return "No transport data available for the selected BTOs."

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

    Provide a clear ranking with transport-specific explanations, including flat types for reference.
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
    try:
        bto_locations = load_bto_locations()
    except Exception as e:
        print(f"Failed to load BTO locations: {e}")
        return
    
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
    
    selected_bto_locations = select_bto_locations(bto_locations)
    
    print(f"\n🚇 Analyzing TRANSPORT ACCESSIBILITY for {len(selected_bto_locations)} selected BTOs...")
    print(f"Destination: {selected_destination}")
    print(f"Time Period: {selected_period}")
    print("Focus: Public transport efficiency and accessibility only")
    
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