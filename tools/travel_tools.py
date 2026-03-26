import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import quote

import requests
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from config import (
    AMADEUS_CLIENT_ID,
    AMADEUS_CLIENT_SECRET,
    GOOGLE_API_KEY,
    REQUEST_TIMEOUT,
    UNSPLASH_ACCESS_KEY,
    interpret_weather_code,
)
from trip_models import TripPlan


def fetch_unsplash_image(query: str) -> str:
    if not UNSPLASH_ACCESS_KEY:
        return "https://example.com/placeholder.jpg"

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "client_id": UNSPLASH_ACCESS_KEY,
        "per_page": 5,
        "orientation": "landscape",
        "order_by": "popular",
    }
    try:
        res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
        results = res.get("results", [])
        if not results:
            return "https://example.com/placeholder.jpg"

        selected_photo = random.choice(results[:5])
        image_url = selected_photo.get("urls", {}).get("regular", "")
        return image_url if image_url else "https://example.com/placeholder.jpg"
    except Exception:
        return "https://example.com/placeholder.jpg"


def get_amadeus_token():
    if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
        return None

    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_CLIENT_ID,
        "client_secret": AMADEUS_CLIENT_SECRET,
    }

    try:
        response = requests.post(url, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception:
        return None


@tool
def check_weather(city: str):
    """
    Fetch detailed weather forecast for a specific city.
    """
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"

    try:
        geo_res = requests.get(geo_url, timeout=REQUEST_TIMEOUT).json()
        if not geo_res.get("results"):
            return f"Could not find coordinates for {city}."

        location = geo_res["results"][0]
        lat, lon = location["latitude"], location["longitude"]

        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,weathercode,windspeed_10m_max,humidity_2m_max",
            "timezone": "auto",
            "temperature_unit": "celsius",
        }

        w_res = requests.get(weather_url, params=params, timeout=REQUEST_TIMEOUT).json()

        daily = w_res.get("daily", {})
        times = daily.get("time", [])
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        rain_amounts = daily.get("precipitation_sum", [])
        wind_speeds = daily.get("windspeed_10m_max", [])
        humidity = daily.get("humidity_2m_max", [])
        weather_codes = daily.get("weathercode", [])

        forecast_report = f"🌍 Detailed Weather Forecast for {city}:\n\n"
        for i in range(min(5, len(times))):
            weather_desc = interpret_weather_code(weather_codes[i]) if i < len(weather_codes) else "Unknown"
            forecast_report += f"📅 {times[i]}:\n"
            forecast_report += f"  🌡️ Temperature: {temps_max[i]}°C (min: {temps_min[i]}°C)\n"
            forecast_report += f"  💧 Humidity: {humidity[i] if i < len(humidity) else 'N/A'}%\n"
            forecast_report += f"  💨 Wind Speed: {wind_speeds[i] if i < len(wind_speeds) else 'N/A'} km/h\n"
            forecast_report += f"  🌧️ Rain Probability: {rain_probs[i]}%\n"
            forecast_report += f"  📏 Rainfall: {rain_amounts[i] if i < len(rain_amounts) else 'N/A'} mm\n"
            forecast_report += f"  {weather_desc}\n"

            if weather_codes[i] in [95, 96, 99]:
                forecast_report += "  ⚠️ WARNING: Severe thunderstorm expected! Not recommended for outdoor activities.\n"
            elif rain_probs[i] > 80:
                forecast_report += "  ⚠️ WARNING: High chance of heavy rain. Plan indoor activities.\n"
            elif (wind_speeds[i] > 40) if i < len(wind_speeds) else False:
                forecast_report += "  ⚠️ WARNING: Strong winds expected. Be cautious with outdoor plans.\n"

            forecast_report += "\n"

        return forecast_report

    except Exception as e:
        return f"Error fetching weather: {str(e)}"


@tool
def google_places_search(query: str, location: str = None):
    """
    Search places, restaurants, hidden gems, or tourist spots with Google Places API.
    """
    if not GOOGLE_API_KEY:
        return "Error: Google API key not found."

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount",
    }

    text_query = f"{query} in {location}" if location else query
    payload = {"textQuery": text_query}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        data = response.json()

        places = data.get("places", [])
        if not places:
            return "No places found."

        result = f"Top results for '{text_query}':\n"
        for place in places[:5]:
            name = place.get("displayName", {}).get("text", "Unknown")
            address = place.get("formattedAddress", "No address")
            rating = place.get("rating", "N/A")
            result += f"- {name} (Rating: {rating}/5): {address}\n"

        return result
    except Exception as e:
        return f"Error connecting to Google Places: {e}"


@tool
def duckduckgo_web_search(query: str, max_results: int = 5):
    """
    Search the web using DuckDuckGo Instant Answer API.
    Useful for broad travel questions that are not tied to a single provider.
    """
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
        "no_redirect": "1",
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        lines = [f"DuckDuckGo results for '{query}':"]
        added = 0

        abstract_text = data.get("AbstractText")
        abstract_url = data.get("AbstractURL")
        if abstract_text:
            if abstract_url:
                lines.append(f"- {abstract_text} ({abstract_url})")
            else:
                lines.append(f"- {abstract_text}")
            added += 1

        related_topics = data.get("RelatedTopics", [])
        for topic in related_topics:
            if added >= max_results:
                break

            if "Topics" in topic:
                for nested in topic.get("Topics", []):
                    if added >= max_results:
                        break
                    text = nested.get("Text")
                    link = nested.get("FirstURL")
                    if text:
                        lines.append(f"- {text} ({link})" if link else f"- {text}")
                        added += 1
            else:
                text = topic.get("Text")
                link = topic.get("FirstURL")
                if text:
                    lines.append(f"- {text} ({link})" if link else f"- {text}")
                    added += 1

        if added == 0:
            fallback = data.get("Heading") or "No strong instant-answer results found. Try a more specific search query."
            lines.append(f"- {fallback}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error searching DuckDuckGo: {e}"


@tool
def get_map_view(location: str, zoom: int = 14):
    """
    Generate a Google Maps Static API URL for a location.
    """
    if not GOOGLE_API_KEY:
        return "Error: Google API key not found."

    encoded_loc = quote(location)
    url = (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={encoded_loc}&zoom={zoom}&size=600x400&maptype=roadmap&key={GOOGLE_API_KEY}"
    )

    return f"Here is a map view of {location}: {url}"


@tool
def find_hotels(city: str):
    """
    Find hotels in a specific city using Amadeus API.
    """
    token = get_amadeus_token()
    if not token:
        return "Error: Could not authenticate with Amadeus API. Check API keys."

    try:
        city_url = "https://test.api.amadeus.com/v1/reference-data/locations"
        headers = {"Authorization": f"Bearer {token}"}
        city_params = {"subType": "CITY", "keyword": city}

        city_res = requests.get(city_url, headers=headers, params=city_params, timeout=REQUEST_TIMEOUT).json()

        if not city_res.get("data"):
            return f"Could not find IATA code for city: {city}"

        iata_code = city_res["data"][0]["iataCode"]

        hotel_url = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
        hotel_params = {"cityCode": iata_code}

        hotel_res = requests.get(hotel_url, headers=headers, params=hotel_params, timeout=REQUEST_TIMEOUT).json()

        hotels = hotel_res.get("data", [])
        if not hotels:
            return f"No hotels found in {city} ({iata_code})."

        output = f"Hotels found in {city} ({iata_code}):\n"
        for hotel in hotels[:5]:
            name = hotel.get("name", "Unknown Hotel")
            hotel_id = hotel.get("hotelId", "")
            output += f"- {name} (ID: {hotel_id})\n"

        return output

    except Exception as e:
        return f"Error querying Amadeus: {e}"


@tool
def get_destination_photo(query: str):
    """
    Fetch a popular destination photo from Unsplash API.
    """
    if not UNSPLASH_ACCESS_KEY:
        return "Error: Unsplash API key not found."

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "client_id": UNSPLASH_ACCESS_KEY,
        "per_page": 10,
        "orientation": "landscape",
        "order_by": "popular",
    }

    try:
        res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
        results = res.get("results", [])
        if not results:
            return "No photos found."

        best_photo = max(results, key=lambda x: x.get("likes", 0))

        desc = best_photo.get("description") or best_photo.get("alt_description") or "Famous travel photo"
        image_url = best_photo.get("urls", {}).get("regular")
        credit = best_photo.get("user", {}).get("name")
        likes = best_photo.get("likes", 0)

        return f"![{desc}]({image_url})\n*Popular photo (⭐ {likes} likes) by {credit} on Unsplash*"
    except Exception as e:
        return f"Error fetching photo: {e}"


@tool
def get_current_date():
    """
    Return current date and date one week from now.
    """
    now = datetime.now()
    next_week = now + timedelta(days=7)
    return f"Today is {now.strftime('%Y-%m-%d')}. One week from now is {next_week.strftime('%Y-%m-%d')}."


@tool
def generate_trip_plan(destination: str, duration_days: int):
    """
    Generate a structured travel itinerary in JSON format.
    """
    structured_llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.7).with_structured_output(TripPlan)

    prompt = f"""
    Create a {duration_days}-day travel itinerary for {destination}.
    Be specific with restaurant names, tourist spots, and activities.
    Include exactly 3 categories with emojis like '🏖️ Beach', '🌲 Nature', '🍽️ Food' or similar relevant categories.
    Populate the 'tour_spots' list with the major places visited.
    Ensure the 'image_url' fields are left as 'PLACEHOLDER' so the tool can fill them.
    """

    try:
        plan: TripPlan = structured_llm.invoke(prompt)

        category_emoji_map = {
            "Beach": "🏖️",
            "Nature": "🌲",
            "Food": "🍽️",
            "Culture": "🏛️",
            "Art": "🎨",
            "Adventure": "⛰️",
            "Historical": "🏰",
            "Urban": "🏙️",
            "Nightlife": "🌙",
            "Shopping": "🛍️",
            "Sports": "⚽",
            "Photography": "📸",
            "Wildlife": "🦁",
            "Water": "🌊",
            "Mountains": "⛰️",
            "Desert": "🏜️",
            "Forest": "🌳",
            "Hiking": "🥾",
            "Yoga": "🧘",
            "Wellness": "💆",
            "Museums": "🏛️",
            "Gardens": "🌸",
            "Temples": "🛕",
            "Beaches": "🏖️",
            "Islands": "🏝️",
        }

        enhanced_categories = []
        for category in plan.trip.categories[:3]:
            if any(char in category for char in "🏖️🌲🍽️🏛️🎨⛰️🏰🏙️🌙🛍️⚽📸🦁🌊🏜️🌳🥾🧘💆🌸🛕🏝️"):
                enhanced_categories.append(category)
            else:
                emoji = ""
                for key, val in category_emoji_map.items():
                    if key.lower() in category.lower():
                        emoji = val
                        break
                if emoji:
                    enhanced_categories.append(f"{emoji} {category}")
                else:
                    enhanced_categories.append(f"✨ {category}")

        plan.trip.categories = enhanced_categories

        try:
            image_queries = [
                f"{destination} travel scenery",
                *[f"{destination} {day.title}" for day in plan.details.days],
            ]

            with ThreadPoolExecutor(max_workers=min(5, len(image_queries))) as executor:
                image_urls = list(executor.map(fetch_unsplash_image, image_queries))

            plan.trip.image_url = image_urls[0]
            for idx, day in enumerate(plan.details.days):
                day.image_url = image_urls[idx + 1]
        except Exception:
            plan.trip.image_url = fetch_unsplash_image(f"{destination} travel scenery")
            for day in plan.details.days:
                day.image_url = fetch_unsplash_image(f"{destination} {day.title}")

        if GOOGLE_API_KEY:
            encoded_dest = quote(destination)
            plan.details.static_map.image_url = (
                "https://maps.googleapis.com/maps/api/staticmap"
                f"?center={encoded_dest}&zoom=12&size=600x400&maptype=roadmap&key={GOOGLE_API_KEY}"
            )
        else:
            plan.details.static_map.image_url = "https://example.com/static_map_placeholder.png"

        return plan.model_dump_json(indent=2)

    except Exception as e:
        return f"Error generating trip plan: {e}"


TRAVEL_TOOLS = [
    check_weather,
    google_places_search,
    duckduckgo_web_search,
    get_map_view,
    find_hotels,
    get_destination_photo,
    get_current_date,
    generate_trip_plan,
]
