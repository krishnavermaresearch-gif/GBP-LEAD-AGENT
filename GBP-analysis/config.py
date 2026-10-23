GOOGLE_SHEET_ID = "Enter sheet id  "
SHEET_INPUT_TAB = "Results"
SHEET_OUTPUT_CORE = "Clean Leads Tier 1"
SHEET_OUTPUT_ADVANCED = "Established Leads Tier 2"

import os
AGENT_1_DIR = os.path.join(os.path.dirname(__file__), "..", "GBP lead agent")
CREDENTIALS_FILE = os.path.join(AGENT_1_DIR, "credentials.json")
TOKEN_FILE = os.path.join(AGENT_1_DIR, "token.json")

BIG_BRANDS = [
    "Boots", "Starbucks", "McDonald's", "McDonalds", "KFC", "Subway", 
    "Burger King", "Reliance", "Tata", "Walmart", "Target", "Domino's", 
    "Pizza Hut", "Apollo Pharmacy", "MedPlus", "Max", "Lifestyle"
]

import os
CLOUD_API_URL = os.getenv("CLOUD_API_URL", "")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", "")
CLOUD_MODEL = os.getenv("CLOUD_MODEL", "")

CORE_HEADERS = [
    "Lead ID", "Business Name", "Phone", "GBP Link", "Contacted (Yes/No)", "Location", "Problem", "Suggested Plan", 
    "Score", "Priority", "Contact Ready", "Estimated Deal Value", "Next Action"
]

ADVANCED_HEADERS = [
    "Lead ID", "Business Name", "Phone", "Website Link", "GBP Link", "Contacted (Yes/No)",
    "Website Analysis", "Custom Pitch", "Opportunity Type", 
    "Opportunity Strength", "Estimated Deal Value", "Next Action"
]
