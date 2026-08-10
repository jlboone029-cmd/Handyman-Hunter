import os
import json
import requests
import time
from datetime import datetime

# --- CONFIGURATION ENGINE ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
HISTORY_FILE = "dual_leads_history.json"
HTML_OUTPUT_FILE = "index.html"

# 🎯 YOUR MASTER 80+ PIPE KEYWORD LIST
KEYWORD_PIPE_LIST = (
    "handyman|repair|fence|drywall|sheetrock|carpenter|plumbing|fixture|deck|door|flooring|painting|fan|"
    "electrical|plumber|electrician|tile|cabinets|sink|troubleshooting|outlet|switch|breaker|panel|wire|"
    "wiring|lighting|light|chandelier|faucet|toilet|shower|tub|drain|leak|clog|pipe|valves|sump|waterheater|"
    "vanity|countertop|backsplash|grout|laminate|hardwood|vinyl|carpet|baseboard|trim|molding|crown|ceiling|"
    "roof|shingle|gutter|downspout|siding|soffit|fascia|window|screen|lock|deadbolt|knob|hinge|closet|shelf|"
    "shelving|framing|stud|dryrot|rot|decking|railing|porch|patio|steps|stairs|masonry|brick|concrete|paver|"
    "caulk|sealing|pressurewashing|washing|haul|demolition|appliance|mounting|tvmount|hanging|blinds"
)

# 🗺️ 17 HIGH-TRAFFIC SC REGIONAL TARGET GROUPS
FACEBOOK_GROUP_URLS = [
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

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f: json.dump(history, f, indent=4)

def check_with_openrouter(post_text):
    if not OPENROUTER_API_KEY:
        print("OpenRouter Key missing. Skipping AI filtering step.")
        return True
    url = "https://openrouter.ai"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Analyze this local Facebook group community post. Is this individual explicitly looking to find, hire, "
        f"or get recommendations for a contractor, handyman, or repair service technician to perform "
        f"a physical manual labor fix, installation, or remodel maintenance task?\n"
        f"The job location should be within these SC service networks: Gaston, South Congaree, Swansea, "
        f"Three Fountains, West Columbia, Downtown Columbia, Olympia, Irmo, Forest Acres, Wagener, "
        f"Lake Murray, or Lexington.\n"
        f"Answer strictly with a single word response: YES or NO.\n\n"
        f"Post Text: {post_text}"
    )
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            verdict = res.json()['choices']['message']['content'].strip().upper()
            return "YES" in verdict
    except Exception as e:
        print(f"OpenRouter error: {e}")
    return True

def scrape_facebook_via_apify():
    if not APIFY_TOKEN:
        print("Apify Token environment variable missing.")
        return []
    
    run_url = f"https://apify.com{APIFY_TOKEN}"
    payload = {
        "startUrls": [{"url": link} for link in FACEBOOK_GROUP_URLS],
        "resultsLimit": 70,
        "viewOption": "CHRONOLOGICAL"
    }
    
    fb_leads = []
    try:
        print("Connecting to Apify Actor core...")
        run_res = requests.post(run_url, json=payload, timeout=30)
        if run_res.status_code == 201:
            dataset_id = run_res.json()["data"]["defaultDatasetId"]
            print(f"Scraper job initialized. Waiting 45s for dataset {dataset_id}...")
            time.sleep(45)
            
            items_url = f"https://apify.com{dataset_id}/items?token={APIFY_TOKEN}"
            items_res = requests.get(items_url, timeout=20)
            if items_res.status_code == 200:
                for post in items_res.json():
                    text = post.get("text", "")
                    post_id = post.get("id", "")
                    
                    post_link = (
                        post.get("url") or 
                        post.get("facebookUrl") or 
                        post.get("postUrl") or 
                        (f"https://facebook.com{post_id}" if post_id else "#")
                    )
                    
                    if text and post_link:
                        fb_leads.append({
                            "id": post_id or post_link, 
                            "description": text, 
                            "link": post_link
                        })
    except Exception as e:
        print(f"Apify connector failed: {e}")
    return fb_leads

def build_dashboard(leads, checked_count):
    timestamp = datetime.now().strftime("%I:%M %p | %b %d")
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Handyman Control Console</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0d1117; margin: 0; padding: 12px; color: #c9d1d9; }}
        .console-header {{ background: linear-gradient(135deg, #1f2937, #111827); border: 1px solid #30363d; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
        .console-header h1 {{ margin: 0; font-size: 20px; color: #58a6ff; font-weight: 800; display: flex; align-items: center; gap: 8px; }}
        .status-bar {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }}
        .metric-box {{ background: #161b22; border: 1px solid #21262d; padding: 10px; border-radius: 8px; text-align: center; }}
        .metric-label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-value {{ font-size: 18px; font-weight: bold; margin-top: 4px; color: #3ff23f; }}
        .metric-value.sync {{ color: #ffbc00; }}
        .lead-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); border-left: 6px solid #238636; }}
        .badge-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .source-badge {{ background-color: #238636; color: white; padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 6px; text-transform: uppercase; }}
        .time-badge {{ font-size: 12px; color: #8b949e; }}
        .lead-desc {{ font-size: 14px; color: #e6edf3; line-height: 1.5; margin-bottom: 16px; white-space: pre-wrap; }}
        .bid-btn {{ display: block; text-align: center; background: #238636; color: white; text-decoration: none; padding: 12px; font-size: 15px; border-radius: 8px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: background 0.2s; }}
        .bid-btn:active {{ background: #2ea043; }}
        .empty-state {{ text-align: center; padding: 40px 20px; color: #8b949e; font-style: italic; }}
    </style>
</head>
<body>
    <div class="console-header">
        <h1>🛠️ Handyman Lead Matrix</h1>
        <div class="status-bar">
            <div class="metric-box">
                <div class="metric-label">Live Channels</div>
                <div class="metric-value">{len(FACEBOOK_GROUP_URLS)} Active</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Last Cloud Sync</div>
                <div class="metric-value sync">{timestamp}</div>
            </div>
        </div>
    </div>
"""

    if not leads:
        html_content += '<div class="empty-state">📡 Scanning frequencies active... No fresh targeted leads found in this sync block.</div>'
    else:
        for lead in leads:
            html_content += f"""
    <div class="lead-card">
        <div class="badge-row">
            <span class="source-badge">VERIFIED BUYER</span>
            <span class="time-badge">Live Target</span>
        </div>
        <div class="lead-desc">{lead.get("description", "No description text provided.")}</div>
        <a href="{lead.get("link", "#")}" target="_blank" class="bid-btn">LAUNCH LINK TO BID ↗</a>
    </div>"""
            
    html_content += "\n</body>\n</html>"
    with open(HTML_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

# --- MASTER ORCHESTRATION APPLICATION LOOP ---
if __name__ == "__main__":
    print("🤖 Launching Handyman Hunter Automation Engine...")
    
    raw_posts = scrape_facebook_via_apify()
    print(f"Scrape completed. Retrieved {len(raw_posts)} total posts to analyze.")
    
    verified_leads = []
    
    import re
    keyword_regex = re.compile(KEYWORD_PIPE_LIST, re.IGNORECASE)
    
    for idx, post in enumerate(raw_posts):
        text_content = post.get("description", "")
        if keyword_regex.search(text_content):
            print(f"[{idx+1}/{len(raw_posts)}] Match found! Validating SC regions via OpenRouter AI...")
            if check_with_openrouter(text_content):
                print(" -> AI Verdict: VALID target service territory. Adding to dashboard.")
                verified_leads.append(post)
            else:
                print(" -> AI Verdict: INVALID location/intent parameters.")

    build_dashboard(verified_leads, len(raw_posts))
    print(f"🚀 Sync sequence fully complete. {len(verified_leads)} live leads updated inside {HTML_OUTPUT_FILE}.")

