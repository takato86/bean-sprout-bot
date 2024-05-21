import os
import requests

LAT = 35.6968973
LON = 139.9197909
TOKEN = os.getenv("OPEN_WEATHER_MAP_API_KEY")

def get_current_weather():
    payload = {
        "lat": LAT, "lon": LON,
        "appid": TOKEN
    }

    response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params=payload  
    )
    
    if response.status_code != 200:
        raise Exception(response.status_code)
    
    content = response.json()
    return content["weather"][0]
