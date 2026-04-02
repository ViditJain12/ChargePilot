from app.clients.tesla_graphql import fetch_nearby_superchargers


def check_alerts(battery_percent, home_lat, home_lng, radius_miles):
    if battery_percent > 20:
        print(f"Battery at {battery_percent}%, no need to charge.")
        return

    chargers = fetch_nearby_superchargers(home_lat, home_lng)
    for c in chargers:
        print(c.name, c.distance_miles, c.current_price)

    nearby = [
        c for c in chargers
        if c.distance_miles <= radius_miles
    ]

    if not nearby:
        print("No chargers nearby.")
        return

    best = min(nearby, key=lambda x: x.current_price)

    print("=" * 50)
    print("TESLA CHARGE ALERT")
    print("=" * 50)
    print(f"Battery: {battery_percent}%")
    print(f"Best charger: {best.name}")
    print(f"Price: ${best.current_price}/kWh")
    print(f"Distance: {best.distance_miles:.2f} miles")
    print(f"Available stalls: {best.available_stalls}")
    print("=" * 50)