import os
from dotenv import load_dotenv

load_dotenv()

TESLA_GRAPHQL_URL = os.getenv("TESLA_GRAPHQL_URL")
TESLA_AUTH_TOKEN = os.getenv("TESLA_AUTH_TOKEN")

HOME_LAT = float(os.getenv("HOME_LAT"))
HOME_LNG = float(os.getenv("HOME_LNG"))

BATTERY_PERCENT = int(os.getenv("BATTERY_PERCENT", 15))
SEARCH_RADIUS_MILES = float(os.getenv("SEARCH_RADIUS_MILES", 5))
