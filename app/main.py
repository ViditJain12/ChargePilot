from app.config import (
    HOME_LAT,
    HOME_LNG,
    BATTERY_PERCENT,
    SEARCH_RADIUS_MILES,
)

from app.clients.tesla_graphql import fetch_nearby_superchargers
from app.services.radius_filter import filter_within_radius
from app.services.charger_selector import select_best_charger

def main():
    print(f"\nBattery: {BATTERY_PERCENT}%")
    print(f"Radius: {SEARCH_RADIUS_MILES} miles")
    print("Checking nearby superchargers...\n")

    chargers = fetch_nearby_superchargers(HOME_LAT, HOME_LNG)

    nearby = filter_within_radius(
        chargers,
        HOME_LAT,
        HOME_LNG,
        SEARCH_RADIUS_MILES,
    )

    best = select_best_charger(nearby)

    if not best:
        print("No charger currently at historical low.")
        return

    charger, distance = best

    print("Best charger found:")
    print(f"Name: {charger.name}")
    print(f"Price: ${charger.current_price}")
    print(f"Typical: ${charger.typical_price}")
    print(f"Distance: {distance} miles")
    print(f"Available stalls: {charger.available_stalls}")
    print("\nRecommendation: Leave now")

if __name__ == "__main__":
    main()