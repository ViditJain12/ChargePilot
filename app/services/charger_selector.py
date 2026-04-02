from app.services.pricing_logic import is_lowest_live_price

def select_best_charger(chargers_with_distance):
    valid = []

    for charger, distance in chargers_with_distance:
        if is_lowest_live_price(
            charger.current_price,
            charger.usual_low_price,
        ):
            valid.append((charger, distance))

    if not valid:
        return None

    return min(valid, key=lambda x: x[0].current_price)