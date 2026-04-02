from app.services.alert_service import check_alerts

if __name__ == "__main__":
    battery_percent = 15
    home_lat = 37.72577667236328
    home_lng = -121.93241119384766
    radius_miles = 7

    check_alerts(
        battery_percent=battery_percent,
        home_lat=home_lat,
        home_lng=home_lng,
        radius_miles=radius_miles,
    )