def select_best(chargers):
    return min(chargers, key=lambda x: x.get('current_price', float('inf'))) if chargers else None
