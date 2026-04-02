from app.utils.geo import haversine_miles

def filter_within_radius(chargers, home_lat, home_lng, radius):
    valid = []

    for charger in chargers:
        distance = haversine_miles(
            home_lat,
            home_lng,
            charger.latitude,
            charger.longitude,
        )

        if distance <= radius:
            valid.append((charger, round(distance, 2)))

    return valid