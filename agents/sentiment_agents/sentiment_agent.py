from __future__ import annotations
from typing import Any, Dict, List, Tuple
import re
import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from typing import Optional
from botocore.config import Config
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

load_dotenv(".env")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")  

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = os.getenv("CLAUDE_35")

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=AWS_REGION
)

model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    max_tokens=1024,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive")
    ),
    boto_session=session
)

user_input = "HDB BTO Toa Payoh July 2025 4-room flat reviews, MRT access, school proximity, resale value sentiment on TikTok and YouTube"

SYSTEM_PROMPT=(
        "You are a careful analyst. Determine sentiment about the topic represented by the documents. "
        "The following parameters/topic was given by the user:{user_input}"
        "Make sure the sentiment is regarding the prompter (e.g high demand btos may be low sentiment to prompter "
        "as chances of receiving bto is lower, High cost may be low sentiment as expensive, good facilities is good "
        "sentiment as dont need to travel far to use facilities, etc).\n"
        "Each document begins with a tag like `[N|URL]` or `[N]`. When you cite evidence, include `idx`=N. "
        "If a URL is present in the tag, include the same `url`; otherwise set `url` to an empty string.\n"
        "Include evidence and referenced links in your answer. Give as much details as possible."
        "Rules:\n"
        "- Keep quotes short and verbatim from the text.\n"
        "- Calibrate scores: positive≈0.3..1, negative≈-0.3..-1, mixed≈-0.29..0.29.\n"
        "NOTE: document may contain SPELLING ERRORS. (e.g Rich is actually Ridge), please fix the spelling errors!"
)

JUNK_LINE_REGEXES = [
    r"^\s*Advertisement\b.*$",
    r"^\s*About our ads\b.*$",
    r"^\s*Add or switch accounts\b.*$",
    r"^\s*Manage your account\b.*$",
    r"^\s*Sign out\b.*$",
    r"^\s*Return to homepage\b.*$",
    r"^\s*Skip to main\b.*$",
    r"^\s*Follow us on\b.*$",
    r"^\s*©\s*\d{4}.*$",
    r"^\s*Read also:\b.*$",
    r"^\s*Latest\b.*$",
    r"^\s*News\b.*$",
    r"^\s*Help\b.*$",
    r"^\s*Home\b.*$",
]

INLINE_JUNK_PATTERNS = [
    (r"\[\[nid:[^\]]+\]\]", ""),               # remove [[nid:...]]
    (r"\u200b|\u200c|\u200d|\ufeff", ""),       # zero‑width chars
    (r"\b\|\s*More\s*\b", " "),               # stray nav crumbs
    (r"\s+·\s+", " "),                           # dot separators
    (r"\b—\b", " - "),                           # em dash to hyphen
    (r"\s{2,}", " "),                             # collapse spaces
]



Sentiment=Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    callback_handler=PrintingCallbackHandler()
)


if __name__ == "__main__":
    bundle="""{
        "ok": True,
        "data": {
            "items": [
            {
                "url": "https://www.tiktok.com/discover/hdb-bto-july-2025",
                "kind": "tiktok_discover",
                "title": None,
                "source": None,
                "content": "TikTok - Make Your Day",
                "meta": {},
                "discover": {
                "ok": True,
                "data": {
                    "items": [
                    {
                        "id": "7506765058483997959",
                        "dom": {
                        "url": "https://www.tiktok.com/@faisalrealtor/video/7506765058483997959",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/oQEAt08CSBrAuwIU1IIAAiiAGYBcGFA86fMHwK~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=URHbJADjxtGZ%2Byq1WAzkCtcTAmI%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my2&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@faisalrealtor/video/7506765058483997959"
                    },
                    {
                        "id": "7514370621476752661",
                        "dom": {
                        "url": "https://www.tiktok.com/@audilatiff/video/7514370621476752661",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/oAGct4BlEiAQIGBJMAiIAaCAAzDGfI7I0gEBwR~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=KBbRxFkYnhhbrob8QzqPGgx7ZTk%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my2&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@audilatiff/video/7514370621476752661"
                    },
                    {
                        "id": "7532102220653907201",
                        "dom": {
                        "url": "https://www.tiktok.com/@desireeleung/video/7532102220653907201",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/owUmfADhQZqB0FRqoRYmcDUEgIyHBWJILEf2Eg~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=7%2BtK%2FG7mVf2IfDvm3%2Bf13eBqPJI%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my2&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@desireeleung/video/7532102220653907201"
                    },
                    {
                        "id": "7527042367883447557",
                        "dom": {
                        "url": "https://www.tiktok.com/@dti_besties2/video/7527042367883447557",
                        "cover": "https://p16-sign-va.tiktokcdn.com/tos-maliva-p-0068/oofIICYkF7RtRJE1R7AAIk4boCiTg0ArOsBkbi~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=509vjn1wBwhVvCLXy%2Fs4MjhfnWI%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my2&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@dti_besties2/video/7527042367883447557"
                    },
                    {
                        "id": "7530695072283659527",
                        "dom": {
                        "url": "https://www.tiktok.com/@ingenioustories/video/7530695072283659527",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/oAj1EAEERUrftdEqzgAmeQAgIAHonuDIzHoBFC~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=ni%2BNf0k5zjCvYECe1exWcQg9xs0%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my2&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@ingenioustories/video/7530695072283659527"
                    }
                    ]
                }
                },
                "videos": [
                {
                    "url": "https://www.tiktok.com/@faisalrealtor/video/7506765058483997959",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "Certainly! Here's a summarized version of the key points, locations, dates, figures, and caveats from the provided transcript, along with highlighted positives and negatives:\n\n### Key Points:\n- **Introduction of Sahota Southrishtrachia** from Argentina.\n- **Thank you** acknowledgment.\n\n### Locations:\n- **Argentina**: Mentioned as the country of origin for Sahota Southrishtrachia.\n\n### Dates:\n- **None specified** in the provided transcript.\n\n### Figures:\n- **None specified** in the provided transcript.\n\n### Caveats:\n- **Limited Information**: The transcript is very brief and lacks detailed context, specific dates, figures, or elaborate discussion points.\n\n### Positives:\n- **Introduction**: The acknowledgment and introduction suggest a formal or professional setting, indicating potential for further discussion or collaboration.\n\n### Negatives:\n- **Lack of Detail**: The transcript is extremely short and does not provide enough information to draw substantial conclusions or insights.\n\n---\n\nIf you have more content or specific sections you'd like to analyze, please provide additional context or transcript parts!"
                    }
                    }
                },
                {
                    "url": "https://www.tiktok.com/@audilatiff/video/7514370621476752661",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "### Key Points:\n- **Project Overview**: Discussion about a new Build-to-Order (BTO) project for the year 1995 in Tempunis.\n- **Location**: Primarily situated in Changi and Sibe, though referred to as Tempunis Town.\n- **Units**: The project consists of 380 units, including 2-room, 4-room, and 5-room flats.\n- **Transportation**: Accessible via MRT, with the nearest station approximately 1 km away.\n- **Educational Institutions**: Proximity to SUTD, Kangkat Primary School, and Kangkat Changi Secondary School (within 1 km).\n- **Commercial and Recreational Facilities**: \n  - Singapore Expo\n  - Changi City Point\n  - Changi Business Park\n- **Market Access**: Accessible via bus no. 2 to Kedok Market Place, approximately 10-15 minutes away.\n- **Construction Timeline**: The BTO project was launched in July 1995.\n\n### Positives:\n- **Variety of Unit Types**: Availability of 2-room, 4-room, and 5-room flats caters to different family sizes.\n- **Proximity to Educational Institutions**: Close to primary, secondary, and tertiary education facilities.\n- **Commercial Facilities**: Easy access to Singapore Expo, Changi City Point, and Changi Business Park.\n- **Market Access**: Convenient bus service to Kedok Market Place.\n- **Strategic Location**: Near MRT station and within a short distance to essential amenities.\n\n### Negatives:\n- **Smallest Project**: With only 380 units, it is the smallest BTO project mentioned.\n- **Distance to MRT**: The nearest MRT station is about 1 km away, which may be inconvenient for some residents.\n- **Market Distance**: Kedok Market Place is approximately 10-15 minutes away by bus, which might be a bit far for daily shopping.\n\n### Caveats:\n- The transcript contains some unclear or garbled text, which may affect the accuracy of the summary.\n- Specific details about the exact launch date in July 1995 are not provided beyond the month."
                    }
                    }
                },
                {
                    "url": "https://www.tiktok.com/@desireeleung/video/7532102220653907201",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "### Key Points:\n- **Second wave of BTO (Build-To-Order) and Sales of Balance flats announced.**\n- **BTO Flats:**\n  - Approximately 5,500 units available.\n  - Locations: Bukit Merah, Bukit Panjang, Clementi, Tampines, Toa Payoh, Sembawang, and Woodlands.\n- **Sales of Balance Flats:**\n  - Over 4,600 balanced flats available.\n  - Includes 1,733 completed units ready for immediate move-in.\n- **Additional Resource:**\n  - YouTube video on this year’s HDB market trends recommended for further insights.\n\n### Locations:\n- Bukit Merah\n- Bukit Panjang\n- Clementi\n- Tampines\n- Toa Payoh\n- Sembawang\n- Woodlands\n\n### Dates:\n- Specific application dates for the second wave of BTO and Sales of Balance flats are not provided in the transcript.\n\n### Figures:\n- **BTO Flats:** 5,500 units\n- **Sales of Balance Flats:** 4,600 units\n- **Completed Units (ready for move-in):** 1,733 units\n\n### Caveats:\n- Exact application dates and detailed pricing information are not provided.\n- Interested parties are directed to a YouTube video for more comprehensive market trends, indicating that the transcript may not cover all necessary details.\n\n### Positives:\n- **Large Number of Units:** Significant number of BTO and balanced flats available, providing ample choices for potential buyers.\n- **Variety of Locations:** Flats spread across multiple regions, catering to different preferences and needs.\n- **Immediate Move-In Options:** 1,733 completed units available for those needing to move in quickly.\n\n### Negatives:\n- **Lack of Specific Dates:** No clear information on application dates, which may cause uncertainty for potential applicants.\n- **Incomplete Information:** Reliance on an external YouTube video for full market insights suggests that the transcript alone may not provide all necessary details."
                    }
                    }
                },
                {
                    "url": "https://www.tiktok.com/@dti_besties2/video/7527042367883447557",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "Certainly! Here's a summary of the key points, locations, dates, figures, and caveats from the provided transcript, along with highlights of positives and negatives:\n\n---\n\n### Key Points:\n- **Behavioral Change**: The speaker is committed to changing their behavior by avoiding their phone.\n- **Action Plan**: \n  - Activate airplane mode on the phone.\n  - Engage in alternative activities to distract from phone use.\n\n### Locations:\n- **None specified** in the provided transcript.\n\n### Dates:\n- **None specified** in the provided transcript.\n\n### Figures:\n- **None specified** in the provided transcript.\n\n### Caveats:\n- **Lack of Specifics**: The transcript is very brief and lacks detailed information about the context, goals, or timeline for the behavioral change.\n- **Uncertainty**: The statement \"I know I can be a new\" is somewhat ambiguous and could use clarification.\n\n### Positives:\n- **Commitment to Change**: The speaker shows a clear intention to make a positive change in their habits.\n- **Proactive Steps**: Taking actionable steps like airplane mode and finding alternative activities indicates a proactive approach.\n\n### Negatives:\n- **Ambiguity**: The lack of specific details makes it hard to assess the full scope and effectiveness of the plan.\n- **Potential for Relapse**: Without a more detailed plan or support system, there may be a risk of reverting to old habits.\n\n---\n\nIf you have more context or additional parts of the transcript, please provide them for a more comprehensive analysis."
                    }
                    }
                },
                {
                    "url": "https://www.tiktok.com/@ingenioustories/video/7530695072283659527",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "### Key Points:\n- **Date:** 23rd of July\n- **Event:** HDB opened July BTO and Sears of Balance Flats application.\n- **Price Ranges:** Detailed price ranges for various flat types and locations have been tabulated.\n- **Projects:** Three PRIME BTO projects are highlighted.\n- **Eligibility:** \n  - Singles aged 35 years and above.\n  - Seniors aged 55 years and above may choose shorter leases (15 to 45 years).\n- **Popular Flats:** \n  - 3-room flats for singles, especially in Clemente starting from 388k.\n- **Standard Series BTO:** \n  - Estimated to be 50 to 60k cheaper than PRIME BTOs.\n- **Shorter Lease Flats:** \n  - Prices range from 50k to 65k.\n- **3-Room Standard Flats:** \n  - Available in the north, less than 100 units per town, starting from 267k.\n- **4-Room Standard Flats:** \n  - Woolen Storm has the most supply (420 units), Japanese BTO has 140 units starting from 529k.\n- **5-Room Standard Flats:** \n  - Prices range from 487k to 658k.\n- **3 Gen Standard Flat:** \n  - Available in Sambawang Beacon, 34 units for a 4-bedroom layout, requires 3-gen families to apply.\n\n### Locations:\n- Clemente\n- Woolen Storm\n- Japanese BTO\n- Sambawang Beacon\n- Northern towns (specific towns not mentioned)\n\n### Figures:\n- **Singles (35 years and above):** \n  - 3-room flat starting from 388k\n- **Seniors (55 years and above, shorter leases):** \n  - Starting from 69k\n- **Standard Series BTO:** \n  - 3-room flats from 267k\n  - 4-room flats from 529k\n  - 5-room flats from 487k to 658k\n- **3 Gen Standard Flat:** \n  - 4-bedroom layout, 34 units\n\n### Positives:\n- **Affordability:** \n  - Standard BTOs are estimated to be 50 to 60k cheaper than PRIME BTOs.\n- **Variety:** \n  - Multiple flat types and locations available.\n- **Efficient Layouts:** \n  - 5-room standard BTOs with efficient layouts may attract many applicants.\n\n### Negatives:\n- **Limited Units:** \n  - Some flat types have limited availability (e.g., 3-room standard flats in the north, 3 Gen flat in Sambawang Beacon).\n- **Eligibility Restrictions:** \n  - 3 Gen flats require applicants to be 3-gen families.\n- **Geographical Constraints:** \n  - Certain flat types are only available in specific locations (e.g., northern towns).\n\n### Caveats:\n- **Popularity:** \n  - Certain flats (e.g., 3-room flats in Clemente) may be highly sought after due to limited supply.\n- **Application Process:** \n  - Ensure eligibility criteria are met before applying."
                    }
                    }
                }
                ]
            },
            {
                "url": "https://www.tiktok.com/discover/bto-launch-singapore-2025",
                "kind": "tiktok_discover",
                "title": None,
                "source": None,
                "content": "TikTok - Make Your Day",
                "meta": {},
                "discover": {
                "ok": True,
                "data": {
                    "items": [
                    {
                        "id": "7540256883978800392",
                        "dom": {
                        "url": "https://www.tiktok.com/@edwinwee.sg/video/7540256883978800392",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/okg3SGfjnIWPIvIDERLAceD6FvfAAE1AFQRIAD~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=yIZ3miwzULCXK2%2B0n0kDcnD%2BkAM%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@edwinwee.sg/video/7540256883978800392"
                    },
                    {
                        "id": "7544315809196199186",
                        "dom": {
                        "url": "https://www.tiktok.com/@throwthunder/video/7544315809196199186",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/oIBdy0fWAJcW0iACp91BAiOliWIAyEvwImCAUl~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=T4C7tt3lkBmP3veX30RlBT6Q1e0%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@throwthunder/video/7544315809196199186"
                    },
                    {
                        "id": "7543475977205091602",
                        "dom": {
                        "url": "https://www.tiktok.com/@jng.realtor/video/7543475977205091602",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/o0EAvoiEWC8AEgRvkaIACFEB9zDZbrAE6fex3U~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=gyBXt2qlmn%2BoDxUlRrHEGb0M5z0%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@jng.realtor/video/7543475977205091602"
                    },
                    {
                        "id": "7537055318983904520",
                        "dom": {
                        "url": "https://www.tiktok.com/@black_murcielago/video/7537055318983904520",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/oseiwBG5ReGYvjzItfL9Jgg9G4ZYgAFpf1YQ1A~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=P7XHfhYk0mqTreGS%2BsAogAFDaxk%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@black_murcielago/video/7537055318983904520"
                    },
                    {
                        "id": "7506765058483997959",
                        "dom": {
                        "url": "https://www.tiktok.com/@faisalrealtor/video/7506765058483997959",
                        "cover": "https://p16-sign-sg.tiktokcdn.com/tos-alisg-p-0037/oQEAt08CSBrAuwIU1IIAAiiAGYBcGFA86fMHwK~tplv-photomode-zoomcover:720:720.jpeg?dr=14555&x-expires=1757084400&x-signature=URHbJADjxtGZ%2Byq1WAzkCtcTAmI%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=0d52deaf&idc=my&ftpl=1"
                        },
                        "url": "https://www.tiktok.com/@faisalrealtor/video/7506765058483997959"
                    }
                    ]
                }
                },
                "videos": [
                {
                    "url": "https://www.tiktok.com/@edwinwee.sg/video/7540256883978800392",
                    "video": {
                    "ok": False,
                    "error": "Error code: 429 - {'error': {'message': 'Rate limit reached for model `whisper-large-v3-turbo` in organization `org_01hxk43rj2fhsr8smsc4a2135t` service tier `on_demand` on seconds of audio per hour (ASPH): Limit 7200, Used 7170, Requested 230. Please try again in 1m39.738s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'seconds', 'code': 'rate_limit_exceeded'}}"
                    }
                },
                {
                    "url": "https://www.tiktok.com/@throwthunder/video/7544315809196199186",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "Certainly! Here's a summary of the key points, locations, dates, figures, and caveats from the provided transcript, highlighting the positives and negatives:\n\n### Key Points:\n- **Event Announcement**: Introduction of a significant event or initiative related to Música.\n- **Collaboration**: Mention of partnerships or collaborations with other entities.\n- **New Releases**: Announcement of new music releases or projects.\n- **Community Engagement**: Efforts to engage with the community through various activities.\n- **Future Plans**: Outline of upcoming plans or projects.\n\n### Locations:\n- **Primary Venue**: Specific location where the event or initiative will take place.\n- **Tour Stops**: If applicable, other locations where related events will occur.\n\n### Dates:\n- **Event Date**: Specific date when the main event or initiative will be launched.\n- **Release Dates**: Dates for new music releases or project milestones.\n\n### Figures:\n- **Attendee Estimates**: Expected number of attendees for the event.\n- **Budget**: Financial figures related to the event or initiative.\n- **Sales Projections**: Expected sales figures for new releases.\n\n### Caveats:\n- **Weather Dependencies**: Potential impact of weather on outdoor events.\n- **Logistical Challenges**: Possible difficulties in coordinating the event or initiative.\n- **Market Conditions**: Economic factors that could affect sales or attendance.\n\n### Positives:\n- **Strong Partnerships**: Beneficial collaborations that enhance the event or initiative.\n- **High Engagement**: Positive community response and high levels of engagement.\n- **Innovative Projects**: Introduction of new and creative music projects.\n\n### Negatives:\n- **Potential Delays**: Risks of delays in event scheduling or project releases.\n- **Budget Constraints**: Financial limitations that could impact the scale of the event.\n- **Market Saturation**: Challenges posed by a crowded market for new music releases.\n\nIf you provide more specific details or context from the transcript, I can offer a more tailored summary."
                    }
                    }
                },
                {
                    "url": "https://www.tiktok.com/@jng.realtor/video/7543475977205091602",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "### Key Points:\n- **Market Dynamics**: The HDB (Housing and Development Board) market is experiencing significant changes due to the latest VTO (Voluntary Trading Option) launches.\n- **Sellers' Opportunity**: Sellers who have been waiting for peak prices may find this a critical window to sell before increased supply affects the market.\n- **Buyers' Opportunity**: Buyers may have more negotiation power, particularly for older flats or units located further from MRT stations.\n- **Market Evolution**: The HDB market is rapidly changing, emphasizing the need for informed decision-making.\n\n### Locations:\n- **HDB Flats**: General reference to HDB resale market flats across various locations.\n\n### Dates:\n- **Current Period**: Implied to be the present time with recent VTO launches.\n\n### Figures:\n- **None specified** in the transcript.\n\n### Caveats:\n- **Market Volatility**: The market is evolving fast, suggesting that conditions can change rapidly.\n- **Need for Consultation**: Emphasizes the importance of seeking professional advice before making decisions.\n\n### Positives:\n- **Opportunity for Sellers**: Potential last window for high sales prices before increased supply.\n- **Negotiation Power for Buyers**: Chance to negotiate better deals, especially for less desirable units.\n\n### Negatives:\n- **Market Uncertainty**: Rapid changes may lead to unpredictable market conditions.\n- **Need for Expert Guidance**: Highlights the complexity and risk involved, necessitating professional consultation."
                    }
                    }
                },
                {
                    "url": "https://www.tiktok.com/@black_murcielago/video/7537055318983904520",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "Certainly! Here's a summary of the key points, locations, dates, figures, and caveats from the provided transcript, along with highlights of positives and negatives:\n\n### Key Points:\n- **Introduction and Closing:** The transcript appears to be an introductory or concluding segment, indicated by the phrase \"I'll see you next time.\"\n- **Lack of Specific Content:** The provided text does not contain detailed information about events, discussions, or specific topics.\n\n### Locations:\n- **None specified:** The transcript does not mention any specific locations.\n\n### Dates:\n- **None specified:** No dates are provided in the transcript.\n\n### Figures:\n- **None specified:** There are no numerical figures or statistics mentioned.\n\n### Caveats:\n- **Incomplete Information:** The transcript is very brief and lacks detailed context, making it difficult to draw comprehensive conclusions.\n- **Potential for Misinterpretation:** Without more context, any analysis based on this transcript could be misleading.\n\n### Positives:\n- **Engagement:** The phrase \"I'll see you next time\" suggests a continuation, indicating ongoing engagement or a series.\n- **Anticipation:** The closing statement may create anticipation for future content.\n\n### Negatives:\n- **Lack of Detail:** The transcript is too short and vague to provide meaningful analysis or insights.\n- **Insufficient Context:** Without more information, it’s challenging to understand the full scope or purpose of the discussion.\n\n### Summary:\nThe provided transcript is extremely limited in content and lacks specific details, making a thorough analysis impossible. The only clear point is the indication of a continuation, which is a minor positive. However, the overall lack of information is a significant negative, as it prevents any meaningful conclusions from being drawn."
                    }
                    }
                },
                {
                    "url": "https://www.tiktok.com/@faisalrealtor/video/7506765058483997959",
                    "video": {
                    "ok": True,
                    "data": {
                        "nova": "Certainly! Here's a summary based on the provided transcript snippet, though it's quite limited in detail:\n\n### Key Points:\n- The transcript appears to be incomplete or lacks specific context.\n- No clear information or actionable insights can be derived from the given text.\n\n### Locations:\n- None specified.\n\n### Dates:\n- None specified.\n\n### Figures:\n- None specified.\n\n### Caveats:\n- The transcript is extremely brief and does not provide enough information to form a comprehensive summary.\n- It's possible that the full context is missing, which could alter the interpretation of the content.\n\n### Positives:\n- None identifiable from the given snippet.\n\n### Negatives:\n- The snippet is too short to draw any meaningful conclusions or identify positives and negatives.\n\n**Note:** More context or a complete transcript is needed to provide a detailed and accurate summary."
                    }
                    }
                }
                ]
            },
            {
                "url": "https://www.tiktok.com/@ingenioustories/video/7508303390917610759",
                "kind": "tiktok_video",
                "title": None,
                "source": None,
                "content": "TikTok - Make Your Day",
                "meta": {},
                "video": {
                "ok": True,
                "data": {
                    "nova": "### Key Points:\n- **Sales Launch**: Approximately 3,000 balance flats and 5,400 Build-To-Order (BTO) flats will be launched in July 2025.\n- **Previous Round**: In February, 5,590 units attracted 22,000 applicants, making it about 4 times oversubscribed.\n- **BTO Sets**: Eight BTO project sites will be launched in July 2025.\n- **Application Service**: HFE letter application e-service will be temporarily unavailable during the 8-day application period for the July sales exercise.\n\n### Locations:\n1. **Bukit Merah**: Diagonally opposite APSN Tungling School and near Brighill MRT.\n2. **Bukit Bera 2nd site**: Located beside Crescent Girls School.\n3. **Bukit Panjang**: Between B-Com Primary School and Zhenhua Nature Park, near Bancit LRT.\n4. **Clemente**: Besides Clemente Town Secondary School and near Clemente MRT.\n5. **Sambawang**: Opposite Sambawang Mark, beside Endeavor Premier School.\n6. **Tempening**: At the former Changkak Changi Premier and Secondary School site.\n7. **Topayo**: Near Keltacourt MRT.\n8. **Woollen**: Beside MRT Park and near Woodlands North MRT.\n\n### Dates:\n- **Launch Date**: July 2025\n- **Application Period**: 8 days starting from the launch date\n\n### Figures:\n- **Total Units**: 8,400 units (3,000 balance flats + 5,400 BTO flats)\n- **Applicants in Previous Round**: 22,000 for 5,590 units\n\n### Positives:\n- **High Demand**: Previous round was 4 times oversubscribed, indicating strong demand.\n- **Variety of Units**: Mix of 2-room flexi, 3-room, 4-room, and 5-room flats available.\n- **Good Locations**: Proximity to schools, MRT stations, and nature parks.\n\n### Negatives:\n- **High Competition**: Expect intense competition given the oversubscription in the previous round.\n- **Temporary Service Unavailability**: HFE letter application e-service will be unavailable during the application period.\n\n### Caveats:\n- Ensure to submit HFE applications before the launch to avoid inconvenience during the application window."
                }
                }
            },
            {
                "url": "https://www.tiktok.com/@househuntwithjoo/video/7530547547404864776",
                "kind": "tiktok_video",
                "title": None,
                "source": None,
                "content": "TikTok - Make Your Day",
                "meta": {},
                "video": {
                "ok": False,
                "error": "Error code: 429 - {'error': {'message': 'Rate limit reached for model `whisper-large-v3-turbo` in organization `org_01hxk43rj2fhsr8smsc4a2135t` service tier `on_demand` on seconds of audio per hour (ASPH): Limit 7200, Used 7180, Requested 147. Please try again in 1m3.101s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'seconds', 'code': 'rate_limit_exceeded'}}"
                }
            },
            {
                "url": "https://www.tiktok.com/@uchify.sg/video/7525394629789764871",
                "kind": "tiktok_video",
                "title": None,
                "source": None,
                "content": "TikTok - Make Your Day",
                "meta": {},
                "video": {
                "ok": True,
                "data": {
                    "nova": "### Key Points:\n- **Project Name:** Toa Payo Ridge\n- **Launch Date:** February 2020\n- **Completion Date:** Recently completed\n- **Location:** Junction of Lorong One, Toa Payo, and Toa Payo Rise\n- **Units:** 920 units (2-room flexi, 3-room, and 4-room flats)\n- **Amenities:** \n  - Rooftop viewing decks\n  - Children's playground\n  - Fitness corner\n- **Accessibility:**\n  - Near Caldecott and Brattle MRT stations\n- **Proximity to Schools:**\n  - Raffles Girls School\n  - CHIJ Secondary\n  - Marymount Convent\n  - SJI International\n\n### Positives:\n- **Amenities:** Wide range of facilities within the estate.\n- **Accessibility:** Short stroll to Caldecott and Brattle MRT stations.\n- **Education:** Close proximity to several reputable schools.\n- **Community:** Balanced environment with good accessibility and amenities.\n\n### Negatives:\n- **Unit Variety:** Limited to 2-room flexi, 3-room, and 4-room flats; no larger units available.\n- **Caveats:** \n  - Specific details on unit sizes and pricing are not provided.\n  - Potential for crowding given the number of units (920) in a relatively small area."
                }
                }
            },
            {
                "url": "https://www.youtube.com/watch?v=mPcp0WA2Icw",
                "kind": "youtube_video",
                "title": None,
                "source": None,
                "content": "July 2025 BTO Preview: Toa Payoh BTO Singapore HDB Analysis Review - YouTube About Press Copyright Contact us Creator Advertise Developers Terms Privacy Policy & Safety How YouTube works Test new features © 2025 Google LLC",
                "meta": {},
                "video": {
                "ok": False,
                "error": "Error code: 429 - {'error': {'message': 'Rate limit reached for model `whisper-large-v3-turbo` in organization `org_01hxk43rj2fhsr8smsc4a2135t` service tier `on_demand` on seconds of audio per hour (ASPH): Limit 7200, Used 7158, Requested 484. Please try again in 3m40.507s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'seconds', 'code': 'rate_limit_exceeded'}}"
                }
            },
            {
                "url": "https://sg.news.yahoo.com/hdb-launches-2-601-prime-055814067.html",
                "kind": "article",
                "title": None,
                "source": None,
                "content": "HDB launches 2,601 Prime BTO flats in July 2025 exercise; 10,209 BTO and SBF flats launched Search query Search the web Skip to main News Finance More -1 Manage your account Help Add or switch accounts Sign out Search the web Advertisement Advertisement Return to homepage HDB launches 2,601 Prime BTO flats in July 2025 exercise; 10,209 BTO and SBF flats launched Timothy Tay Wed, 23 July 2025 at 5:58 am UTC 5 min read An artist impression of Toa Payoh Ascent. (Picture: HDB) Four Prime Build-to-Order (BTO) projects totalling 2,601 flats have been launched as part of the July 2025 BTO sales exercise. This is the highest proportion of Prime flats offered in a single BTO exercise since the new classification was introduced in October 2024. Two Prime projects are in Bukit Merah, namely the 498-unit Alexandra Peaks and the 609-unit Alexandra Vista, as well as the 753-unit Clementi Emerald in Clementi and the 741-unit Toa Payoh\nAscent\nin Toa Payoh. Advertisement Advertisement Advertisement Advertisement In total, HDB is offering 10,209 BTO flats in this sales exercise, which comprises 5,547 new BTO flats across eight projects and 4,662 Sale of Balance (SBF) flats across the country. Applications for this BTO sales exercise open on July 23 and close on July 30. Read also:\nHDB launches 2,601 Prime BTO flats in July 2025 exercise; 10,209 BTO and SBF flats launched Eugene Lim, key executive officer at ERA Singapore, observes that the total number of SBF flats offered this year has risen to 10,252 — comprising 5,590 flats in February and 4,662 this month. “It is the highest supply since 2021 and reflects a strong and concerted push to ramp up public housing supply in Singapore,” he says. PropNex estimates that the BTO application rate could be around 3 to 3.5 times, slightly higher than the application rate of 2.6 times for the February 2025 BTO exercise. Prime flats in Bukit Merah, Clementi, Toa Payoh Bounded by\nAlexandra Road\nand Prince Charles Crescent, Alexandra Peaks comprises two blocks of 38- and 46-stories with a mix of 76 three-room flats and 422 four-room flats. HDB says that, excluding grants, three-room flats may be priced from $403,000 while four-room flats may be priced from $560,000. Advertisement Advertisement Advertisement Advertisement Meanwhile, Alexandra Vista is bounded by Tanglin Road and Jervois Lane. The project comprises a trio of 32-storey blocks, and its unit mix includes 248 two-room flexi, 93 three-room flats and 268 four-room flats. Indicative prices (excluding grants) start from $205,000 for the two-room flexi, $420,000 for the three-room and $547,000 for the four-room flats. An artist impression of Alexandra Vista. (Picture: HDB) Clementi Emerald is one of two projects in this sales exercise with a wait time of less than three years. The other project is the 643-unit Bangkit Breeze, a Standard project in Bukit Panjang. Clementi Emerald consists of four blocks with a mix of two-room flexi (from $214,000), three-room flats ($388,000) and four-room flats ($562,000). Sitting at the junction of Toa Payoh Rise and Braddell Rise, Toa Payoh Ascent features twin 40-story towers with a mix of 195 two-room flexi, 78 three-room flats and 468 four-room flats. Indicative prices excluding grants start from $212,000 to $777,000. Advertisement Advertisement Advertisement Advertisement Read also:\nOctober 2024 BTO sales exercise will comprise 1 Prime project, 7 Plus projects, and 7 Standard projects; first BTO launch under location-based classification “Toa Payoh is also a heavily subscribed town when it comes to BTO launches,” says Lim of ERA Singapore. The last project in this neighbourhood, Kim Keat Heights in May 2022, recorded a high subscription rate of 9.7. He expects Toa Payoh Ascent to see similar interest and be a hotly contested project this time around. The other BTO projects in this month’s sales exercise include the 775-unit Sembawang Beacon, the 380-unit Simei Symphony and the 1,148-unit Woodlands North Grove. Increase in subsidy clawback For this sales exercise, HDB says the additional subsidies for Prime flats will be increased to 11% for Alexandra Peaks, Alexandra Vista and Toa Payoh Crescent, while the additional subsidy for Clementi Emerald is 12%. These rates are nearly double compared to the 6% subsidy clawback when Prime flats were first introduced in 2022. Advertisement Advertisement Advertisement Advertisement The subsidy clawback in this exercise is the highest to date, says Lee Sze Teck, senior director of data analytics at Huttons Asia. He adds that Clementi Emerald has a higher clawback subsidy than the other three Prime BTO projects despite being the furthest from the city centre. An artist impression of Clementi Emerald. (Picture: HDB) Moreover, four-room flats in Clementi Emerald are priced higher compared to the four-room flats in Alexandra Peak and Alexandra Vista. Lee notes that the clawback subsidy for a different tranche of flats at Alexandra Peak that were launched in December 2023 was 8%, but the latest flats in that estate are now hit with an 11% subsidy clawback. However, the higher subsidy clawback rate is unlikely to deter flat applicants as these projects are in attractive locations, says Kelvin Fong, CEO of PropNex. He points out that prior to the July 2025 BTO exercise, the subsidy recovery rate for Prime flats under the new classification framework was 9% and under the prime location public housing (PLH) model, the subsidy recovery rate ranged from 6% to 9%. Advertisement Advertisement Advertisement Advertisement Read also:\nHDB to increase yearly BTO supply by 35% over next two years This month’s BTO sales exercise also sees changes to the deferred income assessment (DIA) scheme for young couples. Under the new rule, couples can choose to delay their income assessment for a housing loan until just before key collection, shifting the assessment focus from immediate to future income. Christine Sun, chief researcher and strategist at Realion Group, says: “We expect more couples to opt for larger or pricier flats, as they are more likely to qualify for a higher loan amount, given that many would have been working for some time by then”. HDB’s next BTO sales exercise is set for October, with 9,100 flats to be launched across eight towns: Ang Mo Kio, Bedok, Bishan, Bukit Merah, Jurong East, Sengkang, Toa Payoh and Yishun. The exercise will be closely watched as it includes two highly anticipated projects: the first-ever BTO flats in the Greater Southern Waterfront and the debut development in Mount Pleasant. See Also: Singapore Property for Sale & Rent, Latest Property News, Advanced Analytics Tools New Launch Condo & Landed Property in Singapore (COMPLETE list & updates) HDB launches 2,601 Prime BTO flats in July 2025 exercise; 10,209 BTO and SBF flats launched October 2024 BTO sales exercise will comprise 1 Prime project, 7 Plus projects, and 7 Standard projects; first BTO launch under location-based classification HDB to increase yearly BTO supply by 35% over next two years En Bloc Calculator, Find Out If Your Condo Will Be The Next en-bloc HDB Resale Flats Up For Sale, Affordable Units Available Advertisement About our ads Advertisement Advertisement Advertisement Home Singapore Mental health Sports Gaming Fitspo World Shopping Videos Weather Help Share your feedback About our ads Follow us on © 2025 Yahoo. All rights reserved.",
                "meta": {},
                "note": "no video ingestion"
            },
            {
                "url": "https://www.asiaone.com/money/hdb-bto-july-2025-review-locations-resale-values-amenities-and-more",
                "kind": "article",
                "title": None,
                "source": None,
                "content": "HDB BTO July 2025 review: Locations, resale, values, amenities and more, Money News - AsiaOne Latest ··· News ··· Entertainment ··· Lifestyle ··· Video ··· Digicult ··· EarthOne ··· More ··· money HDB BTO July 2025 review: Locations, resale, values, amenities and more PHOTO:\nUnsplash PUBLISHED ON May 21, 2025\n3:38 AM BY Vanessa Nah Prospective home buyers, your next big opportunity is here. The July 2025 HDB Build-to-Order (BTO) launch is just around the corner — and it's shaping up to be one of the year's most anticipated housing events.\nHDB will be offering around 5,400 BTO flats across eight towns islandwide, including mature estates like Bukit Merah and Toa Payoh, as well as more budget-friendly areas like Woodlands, Bukit Panjang, and Sembawang. Whether you're looking for city-fringe convenience or green-space tranquillity, this launch offers something for everyone.\nAnd that's not all. A concurrent Sale of Balance Flats (SBF) exercise will also be happening — with about 3,000 flats up for grabs. These include units from previous projects that are either already completed or under construction, so they're ideal for those who want to move in sooner.\nIf you're still comparing locations or haven't chosen your favourite estate, don't worry — this guide is here to help. We'll cover what to expect from each BTO site, including locations, flat types, and who each project is best suited for.\n1. What's on offer at the Jul 2025 BTO launch?\nFor the first BTO launch of 2025, we're looking at eight projects in seven towns: Bukit Merah, Bukit Panjang, Clementi, Sembawang, Tampines, Toa Payoh, Woodlands.\nHere's a summary of all the Jul 2025 HDB BTO flat types, classification, and number of units:\nClassification\nLocation\nUnits\nFlat Types\nPrime\nBukit Merah (Tanglin)\n590\n2-, 3-, 4-room\nPrime\nBukit Merah (Alexandra)\n490\n3, 4-room\nPlus/Prime\nToa Payoh\n720\n2-, 3-, 4-room\nPlus\nClementi\n750\n2-, 3-, 4-room\nStandard\nBukit Panjang\n620\n2-, 3-, 4-, 5-room\nStandard\nSembawang\n750\n2-, 3-, 4-, 5-room, 3Gen\nStandard\nTampines\n380\n2, 4, 5-room\nStandard\nWoodlands\n1,130\n2-, 3-, 4-, 5-room\nUnit counts are estimated based on HDB map images and launch briefs; final numbers to be confirmed by HDB.\nThere may be only five projects, but there are many factors to consider. To make sense of all that's on offer, we'll review the July 2025 BTO projects in terms of:\nWho it's best for : Families with school-going kids, seniors, nature-lovers, and more.\nLocation : Generally, we assume the more central the better. Most Singaporeans don't like to live somewhere too\nulu , and all of us need to go to town for catch-ups, work and more. We'll also let you know which projects are Plus or Prime projects — these locations are choicier, but come with a 10-year minimum occupancy period (MOP) and stricter rental conditions.\nAmenities : We look at the nearest MRT station(s), nearby schools, shopping malls, markets and other amenities.\nDate of completion : The sooner it’s done, the better.\nPrice : The lower the better.\nResale value : The higher the better. We reference the latest HDB resale statistics from\nQ1 2025\nto give you an idea. You can also check the resale flat prices for individual units sold within the past two years using HDB's Resale Flat Prices service.\nApplication rate : The lower the better — there ' s no point in a great flat that you can’t even get because it's so oversubscribed. The application rate is calculated by taking the number of applicants divided by the number of flats available. Simply, it reflects the number of applicants vying for one unit. If the application rate is 3, there are three applicants vying for one unit. We will report these once the BTO applications open and HDB reports the rates\nOne more thing...  sun direction\nis also a factor you might want to consider. Look out for when HDB releases detailed site plans of each of the projects. East- and west-facing units will be at the sun’s mercy, while north- and south-facing flats will be the least affected by direct sunlight.\n2. [Prime] Bukit Merah - July 2025 HDB BTO review\nBukit Merah - July 2025 HDB BTO\nOverall rating : ★★★★☆ (3.3) Best for : City commuters, young couples, and buyers prioritising resale value.\nLocation\n★★★★★\nAlexandra project : Bounded by Alexandra Road and Prince Charles Crescent Tanglin project : Along Tanglin Road Travel time to CBD : Under 30min by public transport, 15 minutes by car\nNearest MRT station : Redhill\nAmenities\n★★☆☆☆ (14 nearby schools on HDB’s map)\nNearby schools : Crescent Girls’ School, APSN (Tanglin School), Alexandra Hill Primary School, Gan Eng Seng School, Alexandra Primary School, Zhangde Primary School, Queenstown Secondary School, Gan Eng Seng Primary School, Bukit Merah Secondary School\n★★★★☆\nNearby shopping malls, markets and other amenities : Delta Sport Centre, IKEA Alexandra, Alexandra Central, Tiong Bahru Plaza\nResale value (based on Q1 2025 median resale prices)\n★★★★★\n2-room Flexi : – 3-room : $430,000 4-room : $925,000 5-room : –\nFlat types\nBukit Merah has two BTO projects up for offer in this July 2025 sales exercise:\nNumber of units\nFlat type\nAlexandra\nTanglin\n2-room Flexi (Type 1)\n_\n240\n3-room\n70\n90\n4-room\n420\n260\nTotal\n490\n590\nBukit Merah is one of Singapore's most sought-after mature estates — and with just 490 and 590 units available across its two July 2025 BTO plots, demand is expected to be intense. The Alexandra site is tucked beside Alexandra Canal Corridor and Ikea Alexandra is just five minutes away by car or 10 minutes by public transport.\nThe Tanglin plot is located a bit farther from Redhill MRT, but includes added conveniences — a preschool, eating house, supermarket, and shops within the development.\nIf you lived in this area, commuting is an absolute breeze. You only need under 30 minutes to get to the CBD by public transport, or just 15 minutes by car. Due to the excellent location, we can be pretty confident that these will be classified as Prime flats.\nThat means a longer minimum occupancy period of 10 years, and be prepared for the government to claw back a portion of the flat subsidy if/when you sell your property.\nSpeaking of, if you're thinking long-term, the potential resale value speaks volumes. As of Q1 2025, 4-room resale flats in Bukit Merah had a median price of $925,000 — second only to Queenstown and Toa Payoh.\nNote that these projects don't have the same availability of room type. The Alexandra site does not have any 2-room units available — you'll have to turn to the Tanglin one for that. Neither site is offering any 5-room flats.\nPSA: For the Bukit Merah BTOs, you'll be applying for the town, not your preferred site. That means you can't choose between the Alexandra and Tanglin plots — you'll be balloted for either. If your preferred project runs out of units before your turn, you may be left with the alternative. Declining to book a flat risks losing your first-timer priority, and you face a 1-year application ban if you do that twice.\n3. [Plus/Prime] Toa Payoh - July 2025 HDB BTO review\nToa Payoh - July 2025 HDB BTO\nOverall rating : ★★★★☆ Best for : Families and those seeking centrality, but without being in an overtly prime location.\nLocation\n★★★★☆\nBounded by Raffles Rise and Toa Payoh Rise. Travel time to CBD : Around 30 min by public transport, 20 minutes by car\nNearest MRT station : Caldecott\nAmenities\n★★★☆☆ (19 nearby schools on HDB’s map)\nNearby schools : Raffles Girl’s School (Secondary), Marymount Convent School, Lighthouse School, CHIJ Primary and Secondary Schools (Toa Payoh), Kheng Cheng School, Beatty Secondary School\n★★★★☆\nNearby shopping malls, markets and other amenities : Toa Payoh Central, Toa Payoh Public Library, Mount Alvernia Hospital\nResale value (based on Q1 2025 median resale prices)\n★★★★★\n2-room Flexi : – 3-room : $398,000 4-room : $948,000 5-room : –\nFlat types\nToa Payoh—Jul 2025 BTO\nFlat type\nNumber of units\n2-room Flexi\n190\n3-room\n70\n4-room\n460\nTotal\n730\nLocated in one of Singapore's most established and centrally positioned towns, the Toa Payoh BTO project is expected to be one of the most popular in the July 2025 launch.\nWith Caldecott MRT just a short walk away and Toa Payoh MRT within reach, this site enjoys excellent connectivity — you can get to the CBD in about 30 minutes by public transport, or 20 minutes by car.\nWhat makes this launch especially appealing for families is the strong lineup of nearby schools. You'll find CHIJ Primary and Secondary (Toa Payoh) close by, as well as Marymount Convent School. Within the development itself, future residents can look forward to a preschool, eating house, and shops — bringing daily essentials right to your doorstep.\nLiving near Toa Payoh MRT also means access to a well-developed cluster of amenities, including Toa Payoh Central, the public library, sports complex, and hawker centres.\nThis BTO site blends convenience with community infrastructure, making it a top choice for families looking to settle in a town that has everything.\nToa Payoh doesn't just score high on convenience and connectivity — it also boasts one of the highest HDB resale values in Singapore. In Q1 2025, the median resale price for a 4-room flat in the estate was a remarkable $948,000.\nThat places it at the top of the resale charts, ahead of even Bukit Merah and just behind Queenstown, making this BTO project an attractive long-term investment as well.\nWith its strong location, full suite of facilities, proximity to top schools, and strong resale potential, this is a project that's bound to be oversubscribed.\n[[nid:715968]]\n4. [Plus] Clementi - Feb 2025 HDB BTO review\nClementi - July 2025 HDB BTO\nOverall rating : ★★★★☆ Best for : Parents of school-age kids and west-side dwellers.\nLocation\n★★★★☆\nAlong Clementi Avenue. Travel time to CBD : Just over 30 minutes by public transport, around 20 minutes by car\nNearest MRT station : Clementi\nAmenities\n★★★☆☆ (16 nearby schools on HDB’s map)\nNearby schools : Clementi Town Secondary School, Clementi Primary School, Nan Hua Primary School, Pei Tong Primary School & MK @ Pei Tong, School of Science & Technology, Singapore Polytechnic, New Town Secondary School, Qifa Primary School, Nan Hua High School, NUS High School of Mathematics and Science, Kent Ridge Secondary School, National University of Singapore\n★★★★☆\nNearby shopping malls, markets and other amenities : The Clementi Mall, Grantral Mall, 321 Clementi, Clementi Sports Hall, Clementi Swimming Complex, Clementi Stadium\nResale value (based on Q1 2025 median resale prices)\n★★★★★\n2-room Flexi : – 3-room : $428,000 4-room : $917,400 5-room : –\nFlat types and facilities\nClementi—Jul 2025 BTO\nFlat type\nNumber of units\n2-room Flexi\n420\n3-room\n110\n4-room\n220\nTotal\n750\nThe Clementi BTO site is located in one of Singapore's most established west-side neighbourhoods — making it a strong contender for buyers who want both connectivity and community.\nWith Clementi MRT and Clementi Mall just a short walk away, residents will enjoy easy access to daily essentials, retail, dining, and transport. Travelling to the CBD takes just over 30 minutes by public transport, or around 20 minutes by car.\nEducation is a major advantage here. The site is surrounded by reputable institutions, including Nan Hua High School, Kent Ridge Secondary School, and even the National University of Singapore (NUS). This makes it an excellent long-term option for families planning to stay through multiple schooling stages.\nActive folks will appreciate being near Clementi Stadium, Sports Hall, and Swimming Complex, while foodies and convenience-seekers will be happy to know that the BTO project itself is expected to come with an eating house, minimart, and preschool — perfect for busy families.\nThis site is expected to be classified as a Plus project, which means a 10-year Minimum Occupation Period (MOP) and subsidy recovery on resale.\nHowever, given Clementi's enduring popularity and strong fundamentals, we doubt these rules will do much to curb demand. The numbers back this up — 4-room resale flats here fetched a median of $917,400 in Q1 2025.\nIf you're eyeing the west, this launch should be on your radar.\n5. [Standard] Bukit Panjang - July 2025 HDB BTO review\nBukit Panjang - July 2025 HDB BTO\nOverall rating : ★★☆☆☆ Best for : Nature-lovers and families looking for space and value.\nLocation\n★★☆☆☆\nAlong Bukit Panjang Ring Road. Travel time to CBD : Around 40 minutes by public transport, 30 minutes by car\nNearest MRT/LRT station : Bangkok LRT, Fajar LRT\nAmenities\n★★☆☆☆ (14 nearby schools on HDB’s map)\nNearby schools : Zhenghua Primary School, Beacon Primary School, Greenridge Primary School, West Spring Primary School, Zhenghua Secondary School, West Spring Secondary School, Greenridge Secondary School, Bukit Panjang Primary School\n★★★☆☆\nNearby shopping malls, markets and other amenities : Bukit Panjang Hawker Centre and Market, Bukit Panjang Community Club, Pang Sua Park Connector, Bukit panjang Plaza, Pubkit Panjang Public Library, Greenridge Shopping Centre\nResale value (based on Q1 2025 median resale prices)\n★★☆☆☆\n2-room Flexi : – 3-room : – 4-room : $561,000 5-room : $687,800\nFlat types\nBukit Panjang—Jul 2025 BTO\nFlat type\nNumber of units\n2-room Flexi\n120\n3-room\n90\n4-room\n230\n5-room\n180\nTotal\n620\nIf you're a nature-lover or looking for a quieter, family-oriented neighbourhood, the Bukit Panjang BTO project might just be your match. Nestled right next to Zhenghua Nature Park, this site offers easy access to greenery and park connector trails — perfect for morning jogs, evening walks, or weekend cycling.\nTransport-wise, the nearest stations are Bangkit LRT and Fajar LRT, which link you to Choa Chu Kang MRT and the North-South Line. From there, Lot One mall is within reach. However, getting to the CBD can take about 40 minutes by public transport, or 30 minutes by car, so connectivity isn't its strongest suit.\nWhat it does offer is everyday convenience. Within the BTO development itself, you'll find a preschool, eating house, minimart, shops, and a residents' network centre — all the essentials right at your doorstep. Beacon Primary School is located just next door, which makes this a top pick for young families. Bukit Panjang Hawker Centre and Market is also just down the road.\nIn Q1 2025, 4-room flats in the area had a median resale price of $561,000. While this is on the lower end, if you're thinking about resale value, we also expect flats here to be priced lower.\nAs this will likely be a Standard project with a 5-year Minimum Occupation Period (MOP) and no resale clawback, this BTO offers solid value.\n[[nid:717703]]\n6. [Standard] Sembawang - July 2025 HDB BTO review\nSembawang—Jul 2025 HDB BTO\nOverall rating : ★★☆☆☆ Best for : Singles or young couples who prioritise affordability.\nLocation\n★★☆☆☆\nBounded by Admiralty Link, Admiralty Lane, and Canberra Road. Travel time to CBD : Almost 1 hour by public transport, 40 minutes by car\nNearest MRT/LRT station : Sembawang MRT\nAmenities\n★☆☆☆☆ (8 nearby schools on HDB’s map)\nNearby schools : Endeavour Primary School, Rainbow Centre Admiral Hill, Northoaks Primary School, Canberra Primary and Secondary School, Wellington Primary School, Sembawang Primary and Secondary School\n★★☆☆☆\nNearby shopping malls, markets and other amenities : Sembawang Mart, Sun Plaza, Sembawang Public Library, Canberra Community Club\nResale value (based on Q1 2025 median resale prices)\n★★★☆☆\n2-room Flexi : $362,400 3-room : $520,000\n4-room : $638,400 5-room : $669,000\nFlat types\nSembawang—Jul 2025 BTO\nFlat type\nNumber of units\n2-room Flexi\n160\n3-room\n80\n4-room\n280\n5-room\n200\n3Gen\n30\nTotal\n750\nTucked away in Singapore's northern heartlands, the Sembawang BTO project offers a peaceful, low-density lifestyle that may appeal to families who value space and tranquillity over city buzz.\nBut it comes with a trade-off: connectivity to the CBD isn't the best. Commuting takes almost an hour by public transport, and around 40 minutes by car.\nThe nearest MRT station is Sembawang, though it's not exactly a stone's throw away — you'll likely need to take a bus or commit to a longer walk. That said, the estate is still fairly self-contained. Sun Plaza, the area's main shopping mall, is located at the MRT and covers most daily needs.\nFor families, there are a few schools in the area, and the project will feature an integrated preschool — a plus for those with young children. While this development does not include an eating house, it still delivers solid fundamentals for quiet living.\nNotably, this is one of the few July 2025 BTO projects to offer 3Gen flats, making it an attractive choice for multi-generational households. It's expected to be a Standard project, with a 5-year Minimum Occupation Period (MOP).\nIn terms of long-term value, 4-room flats in Sembawang had a median resale price of $638,400 in Q1 2025-outperforming areas like Bukit Panjang.\n7. [Standard] Tampines - July 2025 HDB BTO review\nTampines - July 2025 HDB BTO\nOverall rating : ★★★★☆ Best for : Easties who want greenery and/or schools.\nLocation\n★★★☆☆\nBounded by Simei Road and Upper Changi Road East. Travel time to CBD : Just over 30 minutes by public transport, just under 30 minutes by car\nNearest MRT/LRT station : Upper Changi MRT\nAmenities\n★★★★★ (40 nearby schools on HDB’s map)\nNearby schools : Singapore University of Technology and Design, Changkat and Primary Secondary School, ITE College East, East Spring Primary and Secondary School, Ngee Ann Secondary School, Temasek Junior College (Holding), Dunman Secondary School, Chongzheng Primary School Yumi Primary School\n★★★☆☆\nNearby shopping malls, markets and other amenities : Singapore Expo, Eastpoint Mall, Changi Seimei Community Club, Changi General Hospital, St Andrew’s Community Hospital\nResale value (based on Q1 2025 median resale prices)\n★★★☆☆\n2-room Flexi : – 3-room : $485,000\n4-room : $688,400 5-room : $800,000\nFlat types and facilities\nTampines—Jul 2025 BTO\nFlat type\nNumber of units\n2-room Flexi\n140\n4-room\n140\n5-room\n100\nTotal\n380\nThis July 2025 BTO launch in Tampines is set to be one of the most limited offerings — only 380 units are available. Despite the small number, it ticks a lot of boxes, especially for those who work or study in the East.\nThe project is situated near Upper Changi MRT and within easy reach of Expo MRT, connecting residents to both the Downtown and East-West lines.\nIt's also close to Singapore University of Technology and Design (SUTD), making it a solid choice for academics, students, or professionals working in nearby business parks.\nOn-site amenities are another highlight. The development will feature a preschool, eating house, supermarket, shops, and even a restaurant or fast food outlet — bringing all your day-to-day essentials right to your doorstep.\nWhile Tampines is known as a mature and well-connected town, this particular site sits on the eastern fringe, closer to Changi than to the main Tampines Central area. That said, the convenience of nearby MRT stations and the Expo area's growing vibrancy make up for it.\nIn terms of value, it's strong: Q1 2025 resale data shows a 4-room flat median price of $688,400-higher than towns like Bukit Panjang and Sembawang. With its low unit count and strong location, this one may to go fast.\n[[nid:718077]]\n8. [Standard] Woodlands - July 2025 HDB BTO review\nWoodlands - July 2025 HDB BTO\nOverall rating : ★★★☆☆ Best for : JB day-trippers, nature-lovers, and budget-conscious buyers.\nLocation\n★★☆☆☆\nNear Admiralty Park. Travel time to CBD : 1 hour by public transport, 40 minutes by car\nNearest MRT/LRT station :  Woodlands North MRT\nAmenities\n★★★★★ (27 nearby schools on HDB’s map)\nNearby schools : Republic Polytechnic, Woodlands Secondary School, Marsiling Secondary School, Marsiling Primary School, Riverside Secondary School, Qihua Primary School, Si Ling Primary School, Fuchun Secondary School, Fuchun Primary School, Singapore Sports School, Evergreen Primary and Secondary School, Woodgrove primary School\n★★☆☆☆\nNearby shopping malls, markets and other amenities : Admiralty Park, Causeway Point, Woodlands Civic Centre, Woodlands Sports Centre, Woodlands Waterfront Park\nResale value (based on Q1 2025 median resale prices)\n★★☆☆☆\n2-room Flexi : – 3-room : $441,000 4-room : $552,000 5-room : $658,300\nFlat types and facilities\nWoodlands—Jul 2025 BTO\nFlat type\nNumber of units\n2-room Flexi\n220\n3-room\n80\n4-room\n420\n5-room\n410\nTotal\n1,130\nThe Woodlands BTO project in the July 2025 launch is one of the largest offerings, with 1,130 units-giving applicants a better chance of securing a flat. Located near Woodlands Checkpoint, it's a prime spot for JB regulars or families who enjoy cross-border convenience.\nThat said, it's far from the CBD, with commutes taking about an hour by public transport or 40 minutes by car. Still, the area is being reshaped under the Woodlands North Coast Master Plan, which aims to introduce new job centres, green spaces, and waterfront attractions-making this a strong long-term play for value-focused buyers.\nNearby educational institutions like Republic Polytechnic add to its appeal, especially for families",
                "meta": {},
                "note": "no video ingestion"
            }
            ]
        },
        "meta": {
            "component": "orchestrator",
            "version": "1.0.0"
        },
        "error": None
        }"""

    sent = Sentiment(bundle)

    logging.info(f"Sentiment analysis result: {sent}")

    