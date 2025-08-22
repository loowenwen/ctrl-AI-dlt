#!/usr/bin/env python

"""
Singapore Weather Agent using NEA (National Environment Agency) data.

Provides weather forecasts for Singapore using official government data from data.gov.sg:
- 2-hour forecasts for immediate weather conditions by area
- 24-hour forecasts with temperature ranges and general conditions  
- 4-day outlook for planning ahead

Example usage:
    python nea_agent.py

Raw data can be retrieved from NEA using
    curl https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast | jq .
    curl https://api-open.data.gov.sg/v2/real-time/api/twenty-four-hr-forecast | jq .
    curl https://api-open.data.gov.sg/v2/real-time/api/four-day-outlook | jq .
"""

import boto3
import json
import logging
import os
import requests

from botocore.config import Config
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def get_area_metadata() -> str:
    url = 'https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast'
    response = requests.get(url)
    data = response.json().get('data')
    area_metadata = data.get('area_metadata')
    logger.debug(area_metadata)
    return json.dumps(area_metadata, indent=2, default=str)


def convert_weather_data(data: dict) -> dict:
    """
    Convert the weather data from the input file format to the required output format.
    
    Args:
        input_file (str): Path to the input JSON file
        output_file (str): Path to save the output JSON file
    """

    # Create a dictionary to map area names to their coordinates
    area_coords = {}
    for area in data['data']['area_metadata']:
        area_coords[area['name']] = {
            'latitude': area['label_location']['latitude'],
            'longitude': area['label_location']['longitude']
        }
    
    # Extract the forecast data and valid period
    forecasts = data['data']['items'][0]['forecasts']
    valid_period = data['data']['items'][0]['valid_period']
    start_time = valid_period['start']
    end_time = valid_period['end']
    
    # Create the new data structure
    weather_data_2hr = []
    
    for forecast_item in forecasts:
        area_name = forecast_item['area']
        if area_name in area_coords:
            weather_data_2hr.append({
                'location_name': area_name,
                'latitude': area_coords[area_name]['latitude'],
                'longitude': area_coords[area_name]['longitude'],
                'forecast': forecast_item['forecast'],
                'start_time': start_time,
                'end_time': end_time
            })
    return weather_data_2hr


@tool
def get_nea_2hr() -> dict:
    """Get 2-hour weather forecast from data.gov.sg API.

    Retrieves the 2-hour weather forecast for Singapore from the data.gov.sg API.
    The forecast provides weather predictions for the next 2 hours across different
    areas in Singapore.

    Returns:
        dict: JSON response containing the 2-hour weather forecast data including:
            - area_metadata: List of areas and their coordinates
            - items: List of forecast periods with predictions
            - api_info: API version and status information

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    url = 'https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast'
    response = requests.get(url)
    weather_data_2hr = convert_weather_data(response.json())
    return weather_data_2hr


def organize_weather_by_region(data: dict) -> dict:
    """
    Organizes 24hr weather forecast data by regions (west, east, central, south, north).
    
    Args:
        data (dict): Dictionary containing weather data in the format of 24hr-realtime.json
        
    Returns:
        dict: Dictionary organized by regions with all relevant weather forecast information
    """
    if not data or 'data' not in data or 'records' not in data['data'] or not data['data']['records']:
        return None

    # Get the first record (most recent forecast)
    record = data['data']['records'][0]
    
    # Extract general weather information
    general_info = record.get('general', {})
    
    # Initialize the result structure
    result = {
        'timestamp': record.get('timestamp'),
        'date': record.get('date'),
        'updatedTimestamp': record.get('updatedTimestamp'),
        'general': general_info,
        'regions': {
            'west': {'forecasts': []},
            'east': {'forecasts': []},
            'central': {'forecasts': []},
            'south': {'forecasts': []},
            'north': {'forecasts': []}
        }
    }
    
    # Process each time period
    for period in record.get('periods', []):
        time_period = period.get('timePeriod', {})
        regions_data = period.get('regions', {})
        
        # For each region, add the forecast for this time period
        for region in ['west', 'east', 'central', 'south', 'north']:
            if region in regions_data:
                forecast_entry = {
                    'timePeriod': time_period,
                    'forecast': regions_data[region]
                }
                result['regions'][region]['forecasts'].append(forecast_entry)
    
    return result


@tool
def get_nea_24hr() -> dict:
    """Get 24-hour weather forecast from data.gov.sg API.
    
    Retrieves the 24-hour weather forecast for Singapore from the data.gov.sg API.
    The forecast provides weather predictions for the next 24 hours.

    Returns:
        dict: JSON response containing the 24-hour weather forecast data

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    url = 'https://api-open.data.gov.sg/v2/real-time/api/twenty-four-hr-forecast'
    response = requests.get(url).json()
    weather_data_24hr = organize_weather_by_region(response)
    logger.debug(weather_data_24hr)
    return weather_data_24hr  # json.dumps(weather_data_24hr, indent=2, default=str)


@tool
def get_nea_4day() -> str:
    """Get 4-day weather forecast from data.gov.sg API.
    
    Retrieves the 4-day weather forecast for Singapore from the data.gov.sg API.
    The forecast provides weather predictions for the next 4 days.

    Returns:
        dict: JSON response containing the 4-day weather forecast data

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    url = 'https://api-open.data.gov.sg/v2/real-time/api/four-day-outlook'
    response = requests.get(url).json()
    logger.debug(response)
    return json.dumps(response, indent=2, default=str)


# AWS Bedrock configuration
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-lite-v1:0')

# Create AWS session
session = boto3.Session()

# Create Bedrock model
model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    max_tokens=2048,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive"),
    ),
    boto_session=session
)


# Create agent
SYSTEM_PROMPT = """
You are a Singapore weather assistant powered by NEA (National Environment Agency) data from data.gov.sg.
You can provide accurate, real-time weather information for Singapore using official government data.

Your capabilities:
- 2-hour weather forecasts for specific areas in Singapore
- 24-hour weather forecasts with temperature ranges and general conditions
- 4-day weather outlook for planning ahead

When users ask about weather:
- Always specify which forecast period you're using (2-hour, 24-hour, or 4-day)
- Mention specific Singapore areas when relevant (e.g., Jurong, Changi, City, etc.)
- Include temperature ranges when available
- Explain weather conditions in simple terms

Example interactions:
- "What's the weather like now?" → Use 2-hour forecast for current conditions
- "Should I bring an umbrella tomorrow?" → Use 24-hour forecast for rain probability
- "Planning a weekend trip, how's the weather?" → Use 4-day outlook
- "Is it raining in Jurong?" → Check 2-hour forecast for specific area

Always provide helpful, location-specific advice based on the official NEA data.
""".strip()

nea_agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_nea_2hr, get_nea_24hr, get_nea_4day],
    callback_handler=PrintingCallbackHandler()
)

prompts = [
    "What's the current weather in Singapore?",
    "Will it rain tomorrow? Should I bring an umbrella?",
    "How's the weather looking for the weekend?"
]

def demo_2hr():
    response = get_nea_2hr()
    print(json.dumps(response, indent=2, default=str))

def demo_24hr():
    response = get_nea_24hr()
    print(json.dumps(response, indent=2, default=str))

def main():
    for prompt in prompts:
        print(f'**Prompt**: {prompt}')
        response = nea_agent(prompt)
        print('\n' + '-' * 80 + '\n')

if __name__ == '__main__':
    main()
