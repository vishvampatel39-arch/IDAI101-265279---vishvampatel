"""
Outside services for MedTimer: the Medji AI advisor (NVIDIA API), emergency
detection and numbers, and a nearby pharmacy search (OpenStreetMap).
Nothing here stores or logs an API key.
"""
import math
import os
import re
from urllib.parse import quote

import requests

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
UA = {"User-Agent": "MedTimer-student-project/1.0"}

SYSTEM_PROMPT = (
    "You are Medji, a small, friendly health helper inside the MedTimer app. "
    "You give general information about GENERIC medicines only (uses, common side effects, cautions, "
    "how anticholinergic medicines can affect memory). You are not a doctor. Never diagnose, never give or change doses, "
    "and never tell anyone to start or stop a medicine. Keep answers short, plain and kind, under 200 words. "
    "If something sounds serious or the person is unsure, tell them to call or visit a doctor or pharmacist. "
    "If it sounds like an emergency, tell them to call their local emergency number right now."
)

EMERGENCY_NUMBERS = {  # country: (general emergency, ambulance)
    "India": ("112", "108"), "USA": ("911", "911"), "UK": ("999", "999"),
    "Europe": ("112", "112"), "Australia": ("000", "000"),
}
EMERGENCY_WORDS = [
    "chest pain", "can't breathe", "cant breathe", "cannot breathe", "trouble breathing", "difficulty breathing",
    "shortness of breath", "unconscious", "passed out", "fainted", "overdose", "too many tablets", "too many pills",
    "seizure", "stroke", "face drooping", "slurred speech", "severe bleeding", "allergic reaction",
    "swelling of the face", "swelling of the throat", "poison", "suicid", "kill myself", "want to die",
]


def looks_like_emergency(text):
    """True if the message contains an urgent phrase. Medji then shows the emergency numbers instead of an AI answer."""
    t = text.lower()
    return any(w in t for w in EMERGENCY_WORDS)


def emergency_reply(country):
    general, ambulance = EMERGENCY_NUMBERS.get(country, EMERGENCY_NUMBERS["India"])
    extra = " If you are thinking of harming yourself, please tell someone near you now. In India you can also call Tele-MANAS on 14416." if country == "India" else ""
    return (f"**This sounds urgent. Please call {general} now, or {ambulance} for an ambulance.** "
            f"Do not wait for an app to answer. If someone is with you, ask them to stay beside you and help.{extra}")


def get_api_key(typed=""):
    """Order: Streamlit secrets, environment variable, then the key typed in this session."""
    def usable(value):  # ignore empty values and the template placeholder
        return bool(value) and "PASTE_YOUR_KEY" not in str(value)

    try:
        import streamlit as st
        if usable(st.secrets.get("NVIDIA_API_KEY")):
            return st.secrets["NVIDIA_API_KEY"], "secrets"
    except Exception:
        pass
    if usable(os.environ.get("NVIDIA_API_KEY")):
        return os.environ["NVIDIA_API_KEY"], "environment"
    return (typed.strip(), "typed") if typed.strip() else ("", "")


def get_model():
    """Model name: optional NVIDIA_MODEL secret or environment variable, otherwise the default."""
    try:
        import streamlit as st
        if st.secrets.get("NVIDIA_MODEL"):
            return str(st.secrets["NVIDIA_MODEL"])
    except Exception:
        pass
    return os.environ.get("NVIDIA_MODEL") or DEFAULT_MODEL


def ask_medji(api_key, model, messages, extra_context=""):
    """Send the chat to NVIDIA's OpenAI-compatible endpoint. Returns (ok, text)."""
    # 1. The system prompt tells the model how to behave (general information only, no doses, call a doctor if unsure)
    system = SYSTEM_PROMPT + (f" The user's current medicine list: {extra_context}." if extra_context else "")
    # 2. Send the chat to NVIDIA's OpenAI-compatible endpoint; the key goes in the Authorization header
    try:
        r = requests.post(
            NVIDIA_URL,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            json={"model": model, "messages": [{"role": "system", "content": system}] + messages,
                  "temperature": 0.6, "top_p": 0.95, "max_tokens": 2000, "stream": False},
            timeout=90,
        )
    except requests.Timeout:
        return False, "Medji took too long to answer. Please try again."
    except requests.RequestException:
        return False, "Medji could not reach the internet. Check your connection and try again."
    # 3. Turn each kind of failure into a short, friendly message instead of a crash
    if r.status_code in (401, 403):
        return False, "The NVIDIA API key was not accepted. Please check it and try again."
    if r.status_code == 404:
        return False, "That model name was not found. Check the model name in Medji settings."
    if r.status_code == 429:
        return False, "Too many requests right now. Please wait a minute and try again."
    if not r.ok:
        return False, f"Medji ran into a problem (code {r.status_code}). Please try again later."
    try:
        text = r.json()["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, ValueError, AttributeError):
        return False, "Medji sent back an answer in a format the app did not understand."
    return clean_answer(text)


def clean_answer(text):
    """Reasoning models may include their thinking. Show only the final answer."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "</think>" in text:
        text = text.split("</think>")[-1]
    text = text.strip()
    if not text:
        return False, "Medji did not finish an answer this time. Please try asking again."
    return True, text


def maps_search_url(place):
    return "https://www.google.com/maps/search/?api=1&query=" + quote(f"pharmacy near {place}")


def osm_search_url(place):
    return "https://www.openstreetmap.org/search?query=" + quote(f"pharmacy near {place}")


def maps_embed_url(place):
    return "https://www.google.com/maps?q=" + quote(f"pharmacy near {place}") + "&output=embed"


def _km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p) / 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2)
    return 12742 * math.asin(math.sqrt(a))


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def _nominatim(q):
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": q, "format": "json", "limit": 1}, headers=UA, timeout=15)
    r.raise_for_status()
    hits = r.json()
    return (float(hits[0]["lat"]), float(hits[0]["lon"])) if hits else None


def _photon(q):
    r = requests.get("https://photon.komoot.io/api/", params={"q": q, "limit": 1}, headers=UA, timeout=15)
    r.raise_for_status()
    feats = r.json().get("features") or []
    if not feats:
        return None
    lon, lat = feats[0]["geometry"]["coordinates"]
    return float(lat), float(lon)


def _open_meteo(q):
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": q, "count": 1},
                     headers=UA, timeout=15)
    r.raise_for_status()
    res = r.json().get("results") or []
    return (float(res[0]["latitude"]), float(res[0]["longitude"])) if res else None


_COORDS = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def geocode(place, region=""):
    """Turn a place into (lat, lon). Tries several free geocoders and, if needed, broader versions of the
    place ('Navrangpura, Ahmedabad' then 'Ahmedabad'). Returns (point, matched_text, error_name)."""
    m = _COORDS.match(place)
    if m:
        return (float(m.group(1)), float(m.group(2))), place, ""
    parts = [p.strip() for p in place.split(",") if p.strip()]
    queries = [", ".join(parts[i:]) for i in range(len(parts))] or [place]
    if region and region.lower() not in place.lower():
        queries.insert(1, f"{place}, {region}")
        queries.append(f"{parts[-1]}, {region}")
    error = ""
    for q in queries:
        for lookup in (_nominatim, _photon, _open_meteo):
            try:
                point = lookup(q)
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
                error = error or type(e).__name__
                continue
            if point:
                return point, q, ""
    return None, "", error


def find_pharmacies(place, radius_m=2000, region=""):
    """List pharmacies and chemists near `place`. Returns (ok, message_or_results)."""
    # Step 1: turn the typed place into coordinates (several free geocoders, broader place if needed)
    point, matched, error = geocode(place, region)
    if not point:
        if error:
            return False, f"The place search did not answer ({error}). Please try again, or use the map buttons."
        return False, "I could not find that place. Try an area and city, like 'Navrangpura, Ahmedabad'."
    lat, lon = point
    # Step 2: ask OpenStreetMap (Overpass) for pharmacies and chemists within the chosen radius
    around = f"(around:{radius_m},{lat},{lon})"
    query = (f'[out:json][timeout:25];(nwr["amenity"="pharmacy"]{around};nwr["shop"="chemist"]{around};'
             f'nwr["healthcare"="pharmacy"]{around};);out center 60;')
    elements, last = None, ""
    for url in OVERPASS_URLS:  # several public servers, in case one is busy
        try:
            o = requests.post(url, data={"data": query}, headers=UA, timeout=35)
            if o.status_code == 200:
                elements = o.json().get("elements", [])
                break
            last = f"HTTP {o.status_code}"
        except (requests.RequestException, ValueError) as e:
            last = type(e).__name__
    if elements is None:
        return False, f"The pharmacy map service is busy or unreachable ({last}). Try again in a minute, or use the map buttons."
    # Step 3: tidy the results (remove duplicates, add distance) and sort nearest first
    rows, seen = [], set()
    for e in elements:
        plat = e.get("lat") or e.get("center", {}).get("lat")
        plon = e.get("lon") or e.get("center", {}).get("lon")
        if plat is None or plon is None:
            continue
        tags = e.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or "Medical store (name not listed)"
        if (name, round(plat, 5), round(plon, 5)) in seen:
            continue
        seen.add((name, round(plat, 5), round(plon, 5)))
        rows.append({"name": name, "km": round(_km(lat, lon, plat, plon), 2),
                     "hours": tags.get("opening_hours", "Not listed"),
                     "phone": tags.get("phone") or tags.get("contact:phone") or "Not listed",
                     "lat": plat, "lon": plon})
    rows.sort(key=lambda r: r["km"])
    return True, {"centre": (lat, lon), "rows": rows[:20], "matched": matched}
