import requests
from tool_decorator import tool
from tools.get_location_by_ip import get_location_by_ip

@tool("Checks the weather using Open-Meteo API for given latitude and longitude. If not provided, uses IP-based geolocation.")
def check_weather_open_meteo(latitude:str=None, longitude:str=None):
    if latitude is None or longitude is None:
        location = get_location_by_ip()
        if "error" in location:
            return {"error": "Failed to get location from IP: " + location["error"]}
        latitude = location.get("latitude")
        longitude = location.get("longitude")
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
