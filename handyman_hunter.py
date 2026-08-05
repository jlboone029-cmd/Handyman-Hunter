import os
import json
import re
import feedparser
import requests
from functools import lru_cache
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime

# ========================================== #
# SECURE CONFIGURATION VIA ENVIRONMENT       #
# ========================================== #
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")

# Official maintained endpoint identifier for Apify
APIFY_ACTOR_ID = "apify/facebook-groups-scraper"

HISTORY_FILE = "dual_leads_history.json"
DASHBOARD_FILE = "leads_dashboard.html"

# BOUNDARY CONFIGURATION
CENTER_CITY = "Lexington, South Carolina"
MAX_RADIUS_MILES = 25.0

FACEBOOK_GROUPS = [
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com",
    "https://facebook.com"
]

CRAIGSLIST_RSS_FEEDS = [
    "https://craigslist.org"
]

# ------------------------- #
# Helpers                   #
# ------------------------- #

def _load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-200:], f)

@lru_cache(maxsize=1)
def _get_geolocator():
    return Nominatim(user_agent="handyman_hunter_zo", timeout=10)

@lru_cache(maxsize=1)
def _center_coords():
    geolocator = _get_geolocator()
    center = geolocator.geocode(CENTER_CITY)
    if not center:
        raise RuntimeError(f"Could not geocode CENTER_CITY: {CENTER_CITY}")
    return (center.latitude, center.longitude)

def _normalize_town_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^['\"\s]+|['\"\s]+$", "", s)
    s = re.sub(r"\s+", " ", s)
    if s.lower().strip(".").strip() == "none":
        return "None"
    return s

def _town_from_text_openrouter(text: str) -> str:
    if not OPENROUTER_API_KEY:
        return "None"

    url = "https://openrouter.ai"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt = (
        "Extract ONLY the South Carolina town/city name mentioned in the text. "
        "Return exactly one town name (e.g., 'Lexington') or 'None' if no SC town is present.\n\n"
        f"TEXT:\n{text}"
    )

    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            data = r.json()
            content = data["choices"]["message"]["content"]
            return _normalize_town_name(content)
    except Exception:
        pass
    return "None"

def extract_and_verify_location(text: str) -> bool:
    if not OPENROUTER_API_KEY:
        return False

    try:
        detected_town = _town_from_text_openrouter(text)
        if detected_town == "None" or len(detected_town) > 40:
            return False

        geolocator = _get_geolocator()
        center_latlon = _center_coords()

        lead = geolocator.geocode(f"{detected_town}, South Carolina")
        if not lead:
            return False

        lead_latlon = (lead.latitude, lead.longitude)
        miles_apart = geodesic(center_latlon, lead_latlon).miles
        return miles_apart <= MAX_RADIUS_MILES
    except Exception:
        return False

# ------------------------- #
# Visual Console HTML Generator
# ------------------------- #
def generate_html_dashboard(leads):
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Handyman Hunter Console</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ color: #1e3a8a; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; }}
        .badge-fb {{ background: #1877f2; }}
        .badge-cl {{ background: #ff6600; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f8fafc; color: #475569; }}
        tr:hover {{ background: #f1f5f9; }}
        a {{ color: #2563eb; text-decoration: none; font-weight: bold; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛠️ Lexington Handyman Job Console</h1>
        <p>Last Operational Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <table>
            <thead>
                <tr>
                    <th>Source</th>
                    <th>Lead Details</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
    """
    if not leads:
        html_content += "<tr><td colspan='3' style='text-align:center; color:#64748b;'>No live matching jobs within your 25-mile radius right now. Checking again soon!</td></tr>"
    else:
        for lead in leads:
            badge_class = "badge-fb" if lead['source'] == "Facebook" else "badge-cl"
            html_content += f"""
                <tr>
                    <td><span class="badge {badge_class}">{lead['source']}</span></td>
                    <td>{lead['title']}</td>
                    <td><a href="{lead['link']}" target="_blank">Open Job ↗</a></td>
                </tr>
            """
    
    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
    """
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

# ------------------------- #
# Scrapers                  #
# ------------------------- #

def scrape_facebook_via_apify(history):
    new_leads = []
    if not APIFY_TOKEN:
        return new_leads, history

    run_url = f"https://apify.com{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}&waitForFinish=120"
    actor_input = {
        "startUrls": [{"url": link} for link in FACEBOOK_GROUPS],
        "resultsLimit": 5,
    }
    try:
        resp = requests.post(run_url, json=actor_input, timeout=150)
        if resp.status_code == 200 or resp.status_code == 201:
            run_data = resp.json().get("data", {}) or {}
            dataset_id = run_data.get("defaultDatasetId")
            if dataset_id:
                items_url = f"https://apify.com{dataset_id}/items?token={APIFY_TOKEN}"
                posts = requests.get(items_url, timeout=150).json()
                for post in posts:
                    post_id = post.get("id") or post.get("url")
                    if not post_id or post_id in history:
                        continue
                    post_text = post.get("text") or post.get("message") or ""
                    if post_text and extract_and_verify_location(post_text):
                        new_leads.append({
                            "id": post_id,
                            "title": (post_text[:60] + "...") if len(post_text) > 60 else post_text,
                            "link": post.get("url"),
                            "source": "Facebook",
                        })
                    history.append(post_id)
    except Exception:
        pass
    return new_leads, history

def scrape_craigslist(history):
    new_leads = []
    if not SCRAPERAPI_KEY:
        return new_leads, history

    try:
        for rss_url in CRAIGSLIST_RSS_FEEDS:
            proxy_endpoint = f"http://scraperapi.com?api_key={SCRAPERAPI_KEY}&url={rss_url}"
            rss_response = requests.get(proxy_endpoint, timeout=40)
            
            if rss_response.status_code == 200:
                feed = feedparser.parse(rss_response.content)
                for entry in feed.entries[:5]:
                    entry_id = getattr(entry, "id", None) or getattr(entry, "link", None)
                    if not entry_id or entry_id in history:
                        continue
                    title = getattr(entry, "title", "") or ""
                    desc = getattr(entry, "description", "") or ""
                    combined_text = f"{title} {desc}".strip()
