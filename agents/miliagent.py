
from dotenv import load_dotenv
load_dotenv()

import os
import json
import boto3
import requests

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

    walking_time = 5  # Placeholder
    return {"name": nearest["name"], "road": nearest["road"], "walking_time_min": walking_time}

#using nova premier
def call_bedrock(prompt):
    session = boto3.Session(profile_name="myisb01_IsbUsersPS-371061166839", region_name="us-east-1")
    bedrock = session.client("bedrock")
    
    response = bedrock.invoke_model_with_response_stream(
        modelId="amazon.nova-premier-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": prompt})
    )
    
    output = ""
    for event in response["events"]:
        if "body" in event:
            output += event["body"]
    
    return output

#agent logic (rough only just as placeholder)
BTO_LOCATIONS = [
    {"name": "Punggol", "lat": 1.4045, "lon": 103.9010},
    {"name": "Jurong East", "lat": 1.3345, "lon": 103.7420},
    {"name": "Tampines", "lat": 1.3530, "lon": 103.9450},
    # Add more BTOs here
]

DESTINATIONS = [
    "CBD", "Woodlands", "Changi Business Park", "Jurong Industrial Park", "Changi Airport"
]

def agentic_bto_ranking(choice_index):
    choice = DESTINATIONS[choice_index - 1]
    
    bto_scores = []
    for bto in BTO_LOCATIONS:
        mrt_info = get_nearest_mrt_walking_time(bto["lat"], bto["lon"])
        walking_time = mrt_info["walking_time_min"] if mrt_info else 999
        bto_scores.append({"name": bto["name"], "walking_time": walking_time})
    
    # prompt for Nova Premier
    prompt = (
        f"Rank the following BTO locations for commuting to {choice} based solely on walking time "
        f"to nearest MRT/bus stops. Provide a relative score out of 100 and short explanation.\n"
        f"{json.dumps(bto_scores, indent=2)}"
    )
    
    llm_output = call_bedrock(prompt)
    return llm_output


if __name__ == "__main__":
    print("Choose destination from:")
    for i, dest in enumerate(DESTINATIONS, 1):
        print(f"{i}. {dest}")
    
    choice = int(input("Enter number: "))
    result = agentic_bto_ranking(choice)
    print("\nBTO Rankings based on walking time:\n")
    print(result)
