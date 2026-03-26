import os
import uuid
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

REQUEST_TIMEOUT = 5
DEFAULT_SESSION_ID = str(uuid.uuid4())

WEATHER_CODE_MAP = {
    0: "☀️ Clear Sky",
    1: "🌤️ Partly Cloudy",
    2: "☁️ Cloudy",
    3: "☁️ Overcast",
    45: "🌫️ Foggy", 48: "🌫️ Foggy",
    51: "🌧️ Drizzle", 53: "🌧️ Drizzle", 55: "🌧️ Drizzle",
    61: "🌧️ Rain", 63: "🌧️ Rain", 65: "🌧️ Rain",
    71: "❄️ Snow/Sleet", 73: "❄️ Snow/Sleet", 75: "❄️ Snow/Sleet", 77: "❄️ Snow/Sleet",
    80: "⛈️ Heavy Rain Showers", 81: "⛈️ Heavy Rain Showers", 82: "⛈️ Heavy Rain Showers",
    85: "❄️ Snow Showers", 86: "❄️ Snow Showers",
    95: "⚡ THUNDERSTORM (Bad Weather)", 96: "⚡ THUNDERSTORM (Bad Weather)", 99: "⚡ THUNDERSTORM (Bad Weather)",
}


def interpret_weather_code(code: int) -> str:
    return WEATHER_CODE_MAP.get(code, "❓ Unknown")
