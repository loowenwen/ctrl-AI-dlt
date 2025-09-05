from dotenv import load_dotenv
load_dotenv()
import os
import json
import requests
from strands import Agent
from strands.models import BedrockModel
from datetime import datetime

def get_auth_token():
    """Fetch OneMap API authentication token."""
    email = os.getenv("ONEMAP_EMAIL")
    password = os.getenv("ONEMAP_PASSWORD")
    if not email or not password:
        raise Exception("ONEMAP_EMAIL or ONEMAP_PASSWORD not set")
    
    auth_url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    try:
        response = requests.post(auth_url, json={"email": email, "password": password}, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException as e:
        raise Exception(f"Failed to authenticate: {e}")

def get_coordinates_from_postal(postal_code: str) -> dict:
    """Fetch coordinates and address for a postal code using OneMap API."""
    try:
        token = get_auth_token()
        base_url = "https://www.onemap.gov.sg/api/common/elastic/search"
        params = {
            "searchVal": postal_code,
            "returnGeom": "Y",
            "getAddrDetails": "Y"
        }
        headers = {"Authorization": token}
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("found", 0) == 0 or not data["results"]:
            raise ValueError(f"No results found for postal code {postal_code}")
        
        result = data["results"][0]
        return {
            "lat": float(result["LATITUDE"]),
            "lon": float(result["LONGITUDE"]),
            "address": result["ADDRESS"],
            "postal_code": postal_code
        }
    except requests.RequestException as e:
        print(f"Error fetching coordinates for postal code {postal_code}: {e}")
        return None
    except ValueError as e:
        print(f"Error: {e}")
        return None

def load_bto_locations(json_file_path="bto_data.json"):
    """Load BTO location data from a JSON file."""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            bto_data = json.load(f)
        
        required_fields = ["name", "lat", "lon", "launch_date"]
        processed_data = []
        for bto in bto_data:
            if all(field in bto for field in required_fields):
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
    date = datetime.now().strftime("%m-%d-%Y")
    routeType = "pt"
    mode = "TRANSIT"
    maxWalkDistance = 1000
    numItineraries = 3

    time_periods = {
        "Morning Peak": "07:30:00",
        "Evening Peak": "18:00:00",
        "Daytime Off-Peak": "12:00:00",
        "Nighttime Off-Peak": "20:00:00"
    }

    if time_period not in time_periods:
        raise ValueError(f"Invalid time period provided: {time_period}. Choose from {list(time_periods.keys())}")
    time = time_periods[time_period]

    try:
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
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if "plan" in data and "itineraries" in data["plan"]:
            return data["plan"]["itineraries"]
        else:
            print("Itineraries not found in the response.")
            return None
    except requests.RequestException as e:
        print(f"Error fetching route data: {e}")
        return None

def get_transport_data_for_bto(bto_lat: float, bto_lon: float, postal_code: str, time_period: str) -> dict:
    """Get comprehensive transport data for a BTO location using postal code."""
    destination_coords = get_coordinates_from_postal(postal_code)
    if not destination_coords:
        return {"error": f"Destination postal code '{postal_code}' not found"}
    
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
    """Format complex route data into AI-friendly structure with specific MRT/bus stop codes."""
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
        stop_sequence = ["Origin"]
        mrt_lines = []
        starting_stop = None
        
        for j, leg in enumerate(route["legs"]):
            mode = leg["mode"]
            if mode != "WALK":
                transport_modes.append(mode)
                if leg.get("route"):
                    route_numbers.append(leg["route"])
                
                # Extract stop codes and MRT lines
                if mode == "RAIL":
                    if leg.get("from", {}).get("stopCode"):
                        stop_code = leg["from"]["stopCode"]
                        mrt_line = ''.join(filter(str.isalpha, stop_code)) if stop_code else None
                        stop_sequence.append(stop_code)
                        mrt_lines.append(mrt_line)
                        if j == 0 or (j == 1 and route["legs"][0]["mode"] == "WALK"):
                            starting_stop = {"code": stop_code, "line": mrt_line, "walk_time_min": walk_time_min}
                    if leg.get("intermediateStops"):
                        for stop in leg["intermediateStops"]:
                            if stop.get("stopCode"):
                                stop_code = stop["stopCode"]
                                mrt_line = ''.join(filter(str.isalpha, stop_code)) if stop_code else None
                                stop_sequence.append(stop_code)
                                mrt_lines.append(mrt_line)
                elif mode == "BUS":
                    if leg.get("from", {}).get("stopCode"):
                        stop_code = leg["from"]["stopCode"]
                        stop_sequence.append(stop_code)
                        if j == 0 or (j == 1 and route["legs"][0]["mode"] == "WALK"):
                            starting_stop = {"code": stop_code, "line": None, "walk_time_min": walk_time_min}
                    if leg.get("intermediateStops"):
                        for stop in leg["intermediateStops"]:
                            if stop.get("stopCode"):
                                stop_sequence.append(stop["stopCode"])
        
        stop_sequence.append("Destination")
        mrt_lines = list(set(filter(None, mrt_lines)))  # Unique, non-empty MRT lines
        
        formatted_route = {
            "route_number": i + 1,
            "total_duration_minutes": duration_min,
            "walking_time_minutes": walk_time_min,
            "transit_time_minutes": transit_time_min,
            "waiting_time_minutes": waiting_time_min,
            "transfers": route["transfers"],
            "walk_distance_meters": route["walkDistance"],
            "transport_modes": list(set(transport_modes)),
            "route_numbers": list(set(route_numbers)),
            "first_transport_mode": transport_modes[0] if transport_modes else "WALK",
            "stop_sequence": stop_sequence,
            "mrt_lines": mrt_lines,
            "starting_stop": starting_stop
        }
        
        formatted_routes.append(formatted_route)
    
    return {
        "bto_name": transport_data["bto_name"],
        "flat_type": transport_data["flat_type"],
        "bto_location": transport_data["bto_coordinates"],
        "destination": transport_data["destination"],
        "time_period": transport_data["time_period"],
        "available_routes": formatted_routes,
        "best_route": min(formatted_routes, key=lambda x: x["total_duration_minutes"])
    }

def create_single_bto_transport_agent() -> Agent:
    """Create the AI agent for single BTO transport analysis using Claude."""
    bedrock_model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature=0.7,
        region_name="us-east-1"
    )
    
    system_prompt = """You are a Singapore public transport specialist focusing ONLY on transport accessibility and connectivity for a single BTO location.

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
- Comparisons to other locations

Provide a detailed description of the transport route details, connectivity, and accessibility based purely on public transport efficiency for this single location."""
    
    return Agent(model=bedrock_model, system_prompt=system_prompt)

def create_comparison_transport_agent() -> Agent:
    """Create the AI agent for comparing multiple BTO transport analyses using Claude."""
    bedrock_model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
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

Provide a relative ranking of the provided BTO locations based purely on public transport efficiency and accessibility."""
    
    return Agent(model=bedrock_model, system_prompt=system_prompt)

def select_single_bto_location(bto_locations: list, selected_index: int) -> dict:
    """Validate and return the selected BTO based on user input index."""
    if selected_index < 0 or selected_index >= len(bto_locations):
        raise ValueError(f"Invalid BTO number {selected_index + 1}. Choose between 1 and {len(bto_locations)}.")
    selected_bto = bto_locations[selected_index]
    print(f"\n✅ Selected BTO for analysis: {selected_bto['name']} - {selected_bto.get('flatType', 'N/A')}")
    return selected_bto

def analyze_single_bto_transport(agent: Agent, selected_bto: dict, postal_code: str, time_period: str) -> str:
    """Use AI agent to analyze ONLY transport accessibility for a single BTO."""
    print(f"🔍 Analyzing transport for {selected_bto['name']}...")
    
    transport_data = get_transport_data_for_bto(
        selected_bto["lat"], selected_bto["lon"], postal_code, time_period
    )
    
    if "error" in transport_data:
        return f"❌ Error getting data for {selected_bto['name']}: {transport_data['error']}"
    
    transport_data["bto_name"] = selected_bto["name"]
    transport_data["flat_type"] = selected_bto.get("flatType", "N/A")
    formatted_data = format_route_data_for_ai(transport_data)
    
    # Save the formatted data for later comparison
    save_formatted_data_for_comparison(formatted_data)
    
    destination_address = formatted_data["destination"].get("address", postal_code)
    
    analysis_prompt = f"""
You are helping a potential BTO buyer in Singapore decide if the transport accessibility of a specific BTO location fits their lifestyle. Provide a clear, concise, and relatable commute guide that focuses on how the commute impacts their daily routine. Use simple language, short sentences, and a structure that’s easy to scan. Include specific MRT station or bus stop codes and MRT lines where applicable.

Describe the public transport accessibility for this SINGLE BTO location: {selected_bto['name']} (Flat type: {selected_bto.get('flatType', 'N/A')}) commuting to {destination_address} (Postal: {postal_code}) during {time_period}.

Transport Data:
{json.dumps(formatted_data, indent=2)}

Structure your response exactly like this for clarity and decision-making:
1. **Your Daily Commute**: Summarize the best route in 2-3 sentences, specifying the starting MRT station or bus stop by its code and MRT line if applicable (e.g., 'Walk 10 min to EW16 (East-West Line)'). Describe what the commute feels like (e.g., 'A 59-min trip with a quick MRT ride').
2. **Key Details for Your Decision**:
   - **Journey Time**: How long it takes.
   - **Starting Point**: Exact MRT station or bus stop code, MRT line if applicable, and walking distance/time (e.g., 'EW16 (East-West Line), 500m, 5 min – easy even in rain').
   - **Transfers**: How complex and frequent (e.g., '1 transfer – simple, with buses every 5 min').
   - **Transport Options**: Modes and reliability (e.g., 'MRT + bus – dependable, with backup routes').
3. **Is This BTO Right for You?**: 2-3 bullet points on transport-related pros and cons for their lifestyle (e.g., 'Pro: Flexible routes for shift workers; Con: Longer walks may tire you').
4. **Decision Tip**: One sentence on who this BTO suits (e.g., 'Ideal for those who value reliable MRT access and don’t mind a 10-min walk').

Consider ONLY:
1. Total journey time
2. Walking accessibility to transport nodes (include specific station/stop codes and MRT lines)
3. Transfer complexity and frequency
4. Transport mode variety and reliability

DO NOT consider price, fares, amenities, or any non-transport factors.
DO NOT compare to other locations.
DO NOT include a numerical score or rating.
Focus purely on how easy it is to get from this BTO to the destination using public transport.
Keep the response under 300 words for quick reading.
"""
    
    try:
        response = agent(analysis_prompt)
        return response
    except Exception as e:
        print(f"AI analysis failed: {str(e)}")
        return f"❌ AI analysis failed: {str(e)}"

def save_formatted_data_for_comparison(formatted_data: dict):
    """Append the formatted transport data to a JSON file for comparison."""
    data_file = "bto_transport_data_for_comparison.json"
    try:
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        else:
            all_data = []
        
        all_data.append(formatted_data)
        
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2)
        
        print(f"✅ Saved transport data for {formatted_data['bto_name']} to {data_file}")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def load_formatted_data_for_comparison() -> list:
    """Load the list of formatted transport data from the JSON file."""
    data_file = "bto_transport_data_for_comparison.json"
    try:
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as f:
                all_data = json.load(f)
            print(f"Loaded {len(all_data)} BTO transport analyses from {data_file}")
            return all_data
        else:
            print(f"No comparison data file found at {data_file}. Run the single BTO analyzer first.")
            return []
    except Exception as e:
        print(f"Error loading comparison data: {e}")
        return []

def analyze_multiple_bto_transport(agent: Agent, all_transport_data: list, destination_address: str, time_period: str) -> str:
    """Use AI agent to rank multiple BTO transport data."""
    if not all_transport_data:
        return "No transport data available for comparison."

    analysis_prompt = f"""
Analyze and rank the public transport accessibility for these {len(all_transport_data)} BTO locations commuting to {destination_address} during {time_period}.

Transport Data:
{json.dumps(all_transport_data, indent=2)}

Provide a relative ranking considering ONLY:
1. Total journey time (lower is better)
2. Walking accessibility to transport nodes (shorter distances are better)
3. Transfer complexity and frequency (fewer transfers are better)
4. Transport mode variety and reliability (more options are better)

DO NOT consider price, amenities, or any non-transport factors.
Focus purely on how easy it is to get from each BTO to the destination using public transport.

Provide a clear ranking with transport-specific explanations, including flat types for reference.
"""
    
    try:
        response = agent(analysis_prompt)
        return response
    except Exception as e:
        print(f"AI analysis failed: {str(e)}")
        return f"❌ AI analysis failed: {str(e)}"

def main_single_bto():
    """Main function for single BTO transport analysis with single user input."""

    try:
        bto_locations = load_bto_locations()
    except Exception as e:
        print(f"Failed to load BTO locations: {e}")
        return
    
    time_periods = [
        "Morning Peak",
        "Evening Peak",
        "Daytime Off-Peak",
        "Nighttime Off-Peak"
    ]
    
    print("\n🏘️ Available BTO Locations:")
    print("-" * 60)
    for i, bto in enumerate(bto_locations, 1):
        flat_type = bto.get("flatType", "N/A")
        print(f"{i:2d}. {bto['name']:<20} | {flat_type:<30} | Launch: {bto['launch_date'][:10]}")
    
    print(f"\n⏰ Available time periods: {', '.join(time_periods)}")
    print("\n📝 Enter your choice in this format: postal code, time period, BTO number")
    print("Example: 529889, Morning Peak, 2")
    
    while True:
        try:
            user_input = input("\nEnter your choice: ").strip()
            parts = [part.strip() for part in user_input.split(",")]
            if len(parts) != 3:
                raise ValueError("Input must have exactly 3 parts: postal code, time period, BTO number")
            
            postal_code, time_period, bto_number = parts
            # Validate postal code format (6 digits for Singapore)
            if not (postal_code.isdigit() and len(postal_code) == 6):
                raise ValueError("Postal code must be a 6-digit number")
            if time_period not in time_periods:
                raise ValueError(f"Invalid time period '{time_period}'. Choose from {time_periods}")
            try:
                bto_index = int(bto_number) - 1
            except ValueError:
                raise ValueError("BTO number must be a valid number")
            
            # Validate postal code with API
            destination_coords = get_coordinates_from_postal(postal_code)
            if not destination_coords:
                raise ValueError(f"Invalid postal code {postal_code}. No location found.")
            
            selected_bto = select_single_bto_location(bto_locations, bto_index)
            break
        except ValueError as e:
            print(f"❌ Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    destination_address = destination_coords.get("address", postal_code)
    print(f"Destination: {destination_address} (Postal: {postal_code}) (Time Period: {time_period})")

    agent = create_single_bto_transport_agent()
    analysis_result = analyze_single_bto_transport(agent, selected_bto, postal_code, time_period)

    print("\nRun this script again to analyze another BTO and save for comparison.")

def main_compare_btos():
    """Main function for comparing multiple BTO transport analyses."""

    print("Focus: Relative Ranking Based on Public Transport")
    
    all_transport_data = load_formatted_data_for_comparison()
    if not all_transport_data:
        print("No data to compare. Please run the single BTO analyzer first.")
        return
    
    destination_address = all_transport_data[0]["destination"]["address"]
    selected_period = all_transport_data[0]["time_period"]

    print(f"Destination: {destination_address} (Time Period: {selected_period})")


    agent = create_comparison_transport_agent()
    analysis_result = analyze_multiple_bto_transport(agent, all_transport_data, destination_address, selected_period)

    if input("\nClear the comparison data file for next session? (y/n): ").lower() == 'y':
        try:
            os.remove("bto_transport_data_for_comparison.json")
            print("Data file cleared.")
        except Exception as e:
            print(f"Error clearing data file: {e}")

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Analyze a single BTO")
    print("2. Compare previously analyzed BTOs")
    choice = input("Enter 1 or 2: ").strip()
    
    if choice == "1":
        main_single_bto()
    elif choice == "2":
        main_compare_btos()
    else:
        print("Invalid choice. Please run again and select 1 or 2.")