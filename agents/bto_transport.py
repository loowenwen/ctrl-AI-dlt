import argparse
import asyncio
import json
import os
import random
from openai import max_retries
import requests
import subprocess
from datetime import datetime, time as dt_time
import time
from typing import Dict, List
import boto3
from dotenv import load_dotenv


class Config:
    """Configuration for OneMap API and BTO data settings."""
    def __init__(self):
        load_dotenv()
        self.onemap_email = os.getenv("ONEMAP_EMAIL")
        self.onemap_password = os.getenv("ONEMAP_PASSWORD")
        self.onemap_auth_url = "https://www.onemap.gov.sg/api/auth/post/getToken"
        self.onemap_search_url = "https://www.onemap.gov.sg/api/common/elastic/search"
        self.onemap_route_url = "https://www.onemap.gov.sg/api/public/routingsvc/route"
        # Make JSON paths relative to this script's folder
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.bto_data_file = os.path.join(base_dir, "bto_data.json")
        self.comparison_data_file = os.path.join(base_dir, "bto_transport_data_for_comparison.json")
        self.time_periods = {
            "Morning Peak": "07:30:00",
            "Evening Peak": "18:00:00",
            "Daytime Off-Peak": "12:00:00",
            "Nighttime Off-Peak": "20:00:00"
        }

class OneMapAPI:
    """Handle OneMap API interactions."""
    def __init__(self, config: Config):
        self.config = config

    def get_auth_token(self) -> str:
        """Fetch OneMap API authentication token."""
        if not self.config.onemap_email or not self.config.onemap_password:
            raise ValueError("Missing ONEMAP_EMAIL or ONEMAP_PASSWORD")
        response = requests.post(
            self.config.onemap_auth_url,
            json={"email": self.config.onemap_email, "password": self.config.onemap_password},
            timeout=10
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def get_coordinates_from_postal(self, postal_code: str) -> Dict[str, float | str]:
        """Fetch coordinates and address for a postal code."""
        token = self.get_auth_token()
        params = {"searchVal": postal_code, "returnGeom": "Y", "getAddrDetails": "Y"}
        headers = {"Authorization": token}
        response = requests.get(self.config.onemap_search_url, params=params, headers=headers, timeout=10)
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

    def get_route_data(self, start: str, end: str, time_period: str) -> List[dict]:
        """Fetch route data for given start/end coordinates and time period."""
        if time_period not in self.config.time_periods:
            raise ValueError(f"Invalid time period: {time_period}. Choose from {list(self.config.time_periods.keys())}")
        token = self.get_auth_token()
        params = {
            "start": start,
            "end": end,
            "routeType": "pt",
            "date": datetime.now().strftime("%m-%d-%Y"),
            "time": self.config.time_periods[time_period],
            "mode": "TRANSIT",
            "maxWalkDistance": 1000,
            "numItineraries": 3
        }
        headers = {"Authorization": token}
        response = requests.get(self.config.onemap_route_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["plan"]["itineraries"] if "plan" in data and "itineraries" in data["plan"] else []

class BTOTransportService:
    """Service for loading and processing BTO transport data."""
    def __init__(self, config: Config):
        self.config = config
        self.api = OneMapAPI(config)

    def load_bto_locations(self) -> List[dict]:
        """Load and validate BTO location data from JSON file."""
        try:
            with open(self.config.bto_data_file, "r", encoding="utf-8") as f:
                bto_data = json.load(f)
        except FileNotFoundError:
            raise ValueError(f"BTO data file '{self.config.bto_data_file}' not found")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in BTO data file")
        required_fields = ["name", "lat", "lon"]
        processed_data = []
        for bto in bto_data:
            if all(field in bto for field in required_fields):
                bto["flatType"] = bto.get("flatType", "N/A")
                processed_data.append(bto)
        if not processed_data:
            raise ValueError("No valid BTO entries found")
        return processed_data

    def get_bto_by_name(self, name: str) -> List[dict]:
        """Get BTO(s) by name, returning all matches."""
        btos = self.load_bto_locations()
        return [bto for bto in btos if bto["name"].lower() == name.lower()]

    def get_transport_data(self, bto_lat: float, bto_lon: float, postal_code: str, time_period: str) -> Dict:
        """Fetch transport data for a BTO location to a destination postal code."""
        try:
            destination_coords = self.api.get_coordinates_from_postal(postal_code)
            start_coords = f"{bto_lat},{bto_lon}"
            end_coords = f"{destination_coords['lat']},{destination_coords['lon']}"
            routes = self.api.get_route_data(start_coords, end_coords, time_period)
            if not routes:
                return {"error": "No routes found"}
            return {
                "bto_coordinates": {"lat": bto_lat, "lon": bto_lon},
                "destination": destination_coords,
                "time_period": time_period,
                "routes": routes
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to fetch transport data: {str(e)}"}

    def format_route_data(self, transport_data: Dict, bto_name: str, flat_type: str) -> Dict:
        """Format transport data into an AI-friendly structure."""
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
            mrt_lines = list(set(filter(None, mrt_lines)))
            formatted_routes.append({
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
            })
        return {
            "bto_name": bto_name,
            "flat_type": flat_type,
            "bto_location": transport_data["bto_coordinates"],
            "destination": transport_data["destination"],
            "time_period": transport_data["time_period"],
            "available_routes": formatted_routes,
            "best_route": min(formatted_routes, key=lambda x: x["total_duration_minutes"])
        }

    def save_comparison_data(self, formatted_data: Dict) -> None:
        """Save formatted transport data for comparison."""
        try:
            all_data = self.load_comparison_data()
            all_data.append(formatted_data)
            with open(self.config.comparison_data_file, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save comparison data: {str(e)}")

    def load_comparison_data(self) -> List[dict]:
        """Load formatted transport data for comparison."""
        try:
            if os.path.exists(self.config.comparison_data_file):
                with open(self.config.comparison_data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            raise ValueError(f"Failed to load comparison data: {str(e)}")

class BTOTransportAnalyzer:

    
    """AI-based analyzer for BTO transport data."""
    def __init__(self, config):
        self.config = config
        self.service = BTOTransportService(config)

    def invoke_with_backoff(self, client, payload, max_retries=5):
        """Invoke Bedrock model with exponential backoff on throttling."""
        retry = 0
        while retry < max_retries:
            try:
                response = client.invoke_model(**payload)
                return json.loads(response["body"].read())["content"][0]["text"]
            except client.exceptions.ThrottlingException:
                wait_time = (2 ** retry) + random.uniform(0, 1)  # exponential backoff with jitter
                print(f"Throttled. Waiting {wait_time:.1f}s before retry {retry+1}...")
                time.sleep(wait_time)
                retry += 1
        raise Exception("Max retries reached. Please try again later.")

    def analyze_all_btos(self, postal_code: str, time_period: str) -> Dict[str, str]:
        """Generate transport analysis reports for ALL BTOs in the dataset."""

        if not (postal_code.isdigit() and len(postal_code) == 6):
            raise ValueError("Postal code must be a 6-digit number")
        if time_period not in self.config.time_periods:
            raise ValueError(f"Invalid time period: {time_period}. Choose from {list(self.config.time_periods.keys())}")

        btos = self.service.load_bto_locations()
        if not btos:
            return {"error": "No BTO data available"}

        all_reports = []
        agent = self.create_single_bto_agent()

        for bto in btos:
            transport_data = self.service.get_transport_data(bto["lat"], bto["lon"], postal_code, time_period)
            if "error" in transport_data:
                all_reports.append({"bto_name": bto["name"], "error": transport_data["error"]})
                continue

            formatted_data = self.service.format_route_data(
                transport_data, bto["name"], bto.get("flatType", "N/A")
            )

            destination_address = formatted_data["destination"].get("address", postal_code)

            analysis_prompt = f"""
You are a Singapore public transport specialist analyzing BTO commuting accessibility.

TASK: Provide a clear, concise, but detailed transport report for {bto['name']} (Flat: {bto.get('flatType', 'N/A')}) 
to {destination_address} during {time_period}.

Transport Data:
{json.dumps(formatted_data, indent=2)}

Return ONLY a valid JSON object with this structure:

{{
  "bto_name": "string",
  "summary": "string (3–4 sentences, concise but insightful)",
  "journey_time": "string",
  "starting_point": "string",
  "transfers": "string",
  "transport_modes": ["string"],
  "pros": ["string"],
  "cons": ["string"]
}}
"""

            try:
                raw_analysis = agent(analysis_prompt)
                try:
                    parsed = json.loads(raw_analysis)
                    all_reports.append(parsed)
                except json.JSONDecodeError:
                    all_reports.append({"bto_name": bto["name"], "raw_text": raw_analysis})
            except Exception as e:
                all_reports.append({"bto_name": bto["name"], "error": str(e)})

        return {"reports": all_reports}

    def create_single_bto_agent(self) -> callable:
        """Create AI agent for single BTO transport analysis using boto3."""
        client = boto3.client("bedrock-runtime", region_name="us-east-1")
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

Provide a detailed description of the transport route details, connectivity, and accessibility based purely on public transport efficiency for this single location."""

        def invoke(prompt: str) -> str:
            payload = {
                "modelId": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "body": json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}]
                })
            }
            return self.invoke_with_backoff(client, payload)

        return invoke

    def create_comparison_agent(self) -> callable:
        """Create AI agent for comparing multiple BTO transport analyses using boto3."""
        client = boto3.client("bedrock-runtime", region_name="us-east-1")
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

        def invoke(prompt: str) -> str:
            payload = {
                "modelId": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "body": json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}]
                })
            }
            return self.invoke_with_backoff(client, payload)

        return invoke

    def analyze_single_bto(self, name: str, postal_code: str, time_period: str) -> Dict[str, str]:
        """Analyze transport accessibility for a single BTO by name."""
        if not (postal_code.isdigit() and len(postal_code) == 6):
            raise ValueError("Postal code must be a 6-digit number")
        if time_period not in self.config.time_periods:
            raise ValueError(f"Invalid time period: {time_period}. Choose from {list(self.config.time_periods.keys())}")
        
        btos = self.service.get_bto_by_name(name)
        if not btos:
            raise ValueError(f"BTO with name '{name}' not found")
        if len(btos) > 1:
            raise ValueError(f"Multiple BTOs found for '{name}'. Please specify lat and lon.")

        
        bto = btos[0]
        transport_data = self.service.get_transport_data(bto["lat"], bto["lon"], postal_code, time_period)
        if "error" in transport_data:
            raise ValueError(transport_data["error"])

        formatted_data = self.service.format_route_data(transport_data, bto["name"], bto.get("flatType", "N/A"))
        self.service.save_comparison_data(formatted_data)

        destination_address = formatted_data["destination"].get("address", postal_code)
        analysis_prompt = f"""
You are a Singapore public transport specialist analyzing BTO commuting accessibility.

TASK: Analyze transport accessibility for {bto['name']} (Flat: {bto.get('flatType', 'N/A')}) commuting to {destination_address} during {time_period}.

Transport Data:
{json.dumps(formatted_data, indent=2)}

Return ONLY a valid JSON object with this structure:

{{
    "daily_commute": {{
        "summary": "string",
        "total_time_minutes": number,
        "feeling": "string"
    }},
    "key_details": {{
        "journey_time": "string",
        "starting_point": {{
            "station_code": "string",
            "station_name": "string", 
            "walking_distance_meters": number,
            "walking_time_minutes": number,
            "accessibility_note": "string"
        }},
        "transfers": {{
            "count": number,
            "complexity": "string",
            "frequency": "string"
        }},
        "transport_options": {{
            "modes": ["string"],
            "reliability": "string",
            "backup_routes": boolean
        }}
    }},
    "pros_and_cons": {{
        "pros": ["string"],
        "cons": ["string"]
    }},
    "decision_tip": "string"
}}

Focus ONLY on transport factors. Use actual data from the transport information provided.
"""
        try:
            agent = self.create_single_bto_agent()
            analysis = agent(analysis_prompt)
            
            # Parse JSON response
            try:
                parsed_analysis = json.loads(analysis)
                return {"result": parsed_analysis}
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw text as fallback
                return {"result": analysis, "format": "text", "note": "JSON parsing failed, returning raw text"}
                
        except Exception as e:
            return {"error": f"AI analysis failed: {str(e)}"}

    def compare_btos(self, destination_address: str, time_period: str) -> Dict[str, str]:
        """Compare transport accessibility across multiple BTOs."""
        if time_period not in self.config.time_periods:
            raise ValueError(f"Invalid time period: {time_period}. Choose from {list(self.config.time_periods.keys())}")

        # Load saved comparison data
        all_transport_data = self.service.load_comparison_data()
        if not all_transport_data:
            raise ValueError("No transport data available for comparison")
        analysis_prompt = f"""
You are a Singapore public transport specialist analyzing BTO locations for commuting accessibility.

TASK: Rank these {len(all_transport_data)} BTO locations from BEST to WORST for commuting to {destination_address} during {time_period}.

Transport Data:
{json.dumps(all_transport_data, indent=2)}

RANKING CRITERIA (in order of importance):
1. Total Journey Time - Shorter is better
2. Walking Distance to First Transport - Shorter walks are more convenient  
3. Number of Transfers - Fewer transfers = less complexity
4. Transport Mode Variety - More options = better reliability
5. Peak Hour Performance - How well it handles rush hour

Return ONLY a valid JSON object with this structure:

{{
    "ranking": [
        {{
            "rank": number,
            "bto_name": "string",
        
        }}
    ],
    "winner_analysis": {{
        "bto_name": "string",
        "advantages": {{
            "journey_time": {{
                "minutes": number,
                "vs_others": [number],
                "advantage": "string"
            }},
            "starting_point": {{
                "station_code": "string",
                "station_name": "string",
                "walking_distance_meters": number,
                "walking_time_minutes": number,
                "advantage": "string"
            }},
            "transfers": {{
                "count": number,
                "vs_others": [number],
                "advantage": "string"
            }},
            "transport_options": {{
                "modes": ["string"],
                "reliability": "string",
                "backup_routes": boolean,
                "advantage": "string"
            }},
            "peak_performance": "string"
        }},
        "key_differentiator": "string"
    }},
    "comparison_table": [
        {{
            "bto_name": "string",
            "total_time_minutes": number,
            "walking_time_minutes": number,
            "transfers": number,
            "best_route": "string",
        }}
    ],
    "summary": {{ 
        "overall_assessment": "string" (This overall assessment should be detailed, informative and 3 lines long)
    }}
}}

Focus ONLY on transport factors. Use actual data from the transport information provided.
"""
        try:
            agent = self.create_comparison_agent()
            raw_response = agent(analysis_prompt)

            # Try to parse the response as JSON
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                result = {"raw_text": raw_response}

            return {"result": result}
        except Exception as e:
            return {"error": f"AI analysis failed: {str(e)}"}

    def clear_comparison_data(self) -> None:
        """Clear the comparison data file."""
        try:
            if os.path.exists(self.config.comparison_data_file):
                os.remove(self.config.comparison_data_file)
        except Exception as e:
            raise ValueError(f"Failed to clear comparison data: {str(e)}")

def get_bto_locations() -> List[dict]:
    """Load BTO locations for external use."""
    config = Config()
    service = BTOTransportService(config)
    return service.load_bto_locations()

def analyze_bto_transport(name: str, postal_code: str, time_period: str) -> Dict[str, str]:
    """Analyze transport for a single BTO location by name."""
    config = Config()
    analyzer = BTOTransportAnalyzer(config)
    return analyzer.analyze_single_bto(name, postal_code, time_period)

def compare_bto_transports(destination_address: str, time_period: str) -> Dict[str, str]:
    """Compare transport accessibility for multiple BTOs."""
    config = Config()
    analyzer = BTOTransportAnalyzer(config)
    return analyzer.compare_btos(destination_address, time_period)

def clear_comparison_data() -> None:
    """Clear stored comparison data."""
    config = Config()
    analyzer = BTOTransportAnalyzer(config)
    analyzer.clear_comparison_data()


def analyze_all_bto_transports(postal_code: str, time_period: str) -> Dict[str, str]:
    """Analyze transport for ALL BTO locations with automatic retry/backoff to handle AWS throttling."""
    config = Config()
    analyzer = BTOTransportAnalyzer(config)
    results = {}

    btos = get_bto_locations()
    
    for bto in btos:
        name = bto["name"]
        retry = 0
        max_retries = 5

        while retry < max_retries:
            try:
                results[name] = analyzer.analyze_single_bto(name, postal_code, time_period)
                
                # If successful, break out of retry loop
                break
            except Exception as e:
                # Check if it's a throttling exception
                if "ThrottlingException" in str(e) or "too many requests" in str(e).lower():
                    wait_time = (2 ** retry) + random.uniform(0, 1)  # exponential backoff + jitter
                    time.sleep(wait_time)
                    retry += 1
                else:
                    # Other errors, log and skip
                    results[name] = {"error": str(e)}
                    break
        else:
            # Max retries reached
            results[name] = {"error": "Max retries reached due to throttling. Try again later."}

        # small random delay between BTOs to reduce chance of throttling
        inter_bto_wait = random.uniform(0.5, 1.2)
        print(f"⏳ Waiting {inter_bto_wait:.2f}s before next BTO request...")
        time.sleep(inter_bto_wait)

    return results
