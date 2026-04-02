def is_best_live_price(charger):
    return charger.current_price <= 0.34 and charger.available_stalls >= 5