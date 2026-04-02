from dataclasses import dataclass

@dataclass
class Charger:
    station_id: str
    name: str
    latitude: float
    longitude: float
    distance_miles: float
    current_price: float
    usual_low_price: float
    typical_price: float
    available_stalls: int