import requests

from tool_decorator import tool

@tool("Fetches approximate latitude and longitude based on public IP address")
def get_location_by_ip():
    try:
        response = requests.get('https://ipinfo.io/json')
        response.raise_for_status()
        data = response.json()
        loc = data.get('loc')
        if loc:
            latitude, longitude = map(float, loc.split(','))
            return {"latitude": latitude, "longitude": longitude}
        else:
            return {"error": "Location data not found in IP info response"}
    except Exception as e:
        return {"error": str(e)}
