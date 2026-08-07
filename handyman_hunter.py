import os
import json
import requests
from datetime import datetime

# --- CONFIGURATION ENGINE ---
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
HISTORY_FILE = "dual_leads_history.json"
HTML_OUTPUT_FILE = "leads_dashboard.html"

# 🎯 YOUR PIPE KEYWORD LIST - Modify these between quotes to change your targets!
KEYWORD_PIPE_LIST = "handyman|repair|fence|drywall|sheetrock|carpenter|plumbing|fixture|deck|door|flooring|painting|fan"

# Expanded target list for high-traffic local neighborhood and marketplace groups
FACEBOOK_GROUP_URLS = [
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
    """Feeds text matching your pipe terms to OpenRouter to qualify buyers."""
    if not OPENROUTER_API_KEY:
        return True # Fallback if key missing
        
    url = "https://openrouter.ai"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Converts pipes to a readable list for the AI agent
    clean_services = ", ".join(KEYWORD_PIPE_LIST.split("|"))
    
    prompt = (
        f"Analyze this neighborhood community group post. Is this individual looking to find or hire "
        f"someone to perform any of these maintenance tasks or trades: {clean_services}? "
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
        print(f"OpenRouter screening instance error: {e}")
    return True

def scrape_facebook_via_apify():
    """Runs the Apify actor system to scrape target local Facebook groups."""
    if not APIFY_TOKEN:
        print("Scraping execution skipped. Apify Token environment variable missing.")
        return []
    
    run_url = f"https://apify.com{APIFY_TOKEN}"
    payload = {
        "startUrls": [{"url": link} for link in FACEBOOK_GROUP_URLS],
        "resultsLimit": 20,
        "viewOption": "CHRONOLOGICAL"
    }
    
    fb_leads = []
    try:
        print("Connecting to Apify Actor core...")
        run_res = requests.post(run_url, json=payload, timeout=30)
        if run_res.status_code == 201:
            dataset_id = run_res.json()["data"]["defaultDatasetId"]
            
            import time
            print("Allowing background extraction thread to fetch posts...")
            time.sleep(25) # Brief hold while data gathers
            
            items_url = f"https://apify.com{dataset_id}/items?token={APIFY_TOKEN}"
            items_res = requests.get(items_url, timeout=20)
            if items_res.status_code == 200:
                for post in items_res.json():
                    text = post.get("text", "")
                    post_id = post.get("id", "") or post.get("url", "")
                    if text and post_id:
                        fb_leads.append({"id": post_id, "text": text, "link": post.get("url", "#")})
    except Exception as e:
        print(f"Apify connector failed: {e}")
    return fb_leads

def build_dashboard(leads):
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    html_content = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Handyman Job Console</title>
<style>
    body {{ font-family: -apple-system, sans-serif; background-color: #f4f6f9; margin: 0; padding: 15px; }}
    .header {{ background-color: #0056b3; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .header p {{ margin: 5px 0 0 0; font-size: 13px; opacity: 0.9; }}
    .card {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #007bff; }}
    .badge {{ display: inline-block; padding: 3px 8px; font-size: 11px; font-weight: bold; border-radius: 4px; color: white; background-color: #007bff; margin-bottom: 8px; }}
    .title {{ font-size: 16px; font-weight: bold; margin-bottom: 6px; color: #111; }}
    .desc {{ font-size: 14px; color: #555; line-height: 1.4; margin-bottom: 12px; }}
    .btn {{ display: inline-block; background-color: #28a745; color: white; text-decoration: none; padding: 8px 14px; font-size: 14px; border-radius: 5px; font-weight: bold; }}
    .no-leads {{ text-align: center; color: #777; font-style: italic; padding: 10px 0; }}
</style></head>
<body>
    <div class="header"><h1>🛠️ Lexington Area Handyman Job Console</h1><p>Last Operational Update: {timestamp}</p></div>"""

    if not leads:
        html_content += '<div class="card"><p class="no-leads">No active matching jobs found within your targeted group networks right now.</p></div>'
    else:
        for lead in leads:
            html_content += f"""
    <div class="card">
        <span class="badge">FACEBOOK GROUP</span>
        <div class="title">{lead["title"]}</div>
        <div class="desc">{lead["description"]}</div>
        <a href="{lead["link"]}" target="_blank" class="btn">Open Post To Bid ↗</a>
    </div>"""
            
    html_content += "</body></html>"
    with open(HTML_OUTPUT_FILE, "w", encoding="utf-8") as f: f.write(html_content)
    print("Dashboard web interface rebuilt.")

def main():
    print("Initiating community group scanning engine...")
    history = load_history()
    collected_leads = []
    
    # Breaks up the pipes into a string array for fast filtering loops
    target_keywords = KEYWORD_PIPE_LIST.lower().split("|")

    fb_posts = scrape_facebook_via_apify()
    print(f"Retrieved {len(fb_posts)} raw posts. Commencing pipeline validation process...")
    
    for post in fb_posts:
        if post["id"] in history: 
            continue
            
        post_text_lower = post["text"].lower()
        
        # Level 1 Match: Checks if any of your pipe keywords are in the text
        if any(keyword in post_text_lower for keyword in target_keywords):
            print(f"Keyword matched. Passing to OpenRouter AI helper...")
            
            # Level 2 Match: AI screens out sales, tool reviews, and spam posts
            if check_with_openrouter(post["text"]):
                print("🎯 Match confirmed by AI context checker!")
                collected_leads.append({
                    "source": "Facebook",
                    "title": "Local Service Request Found",
                    "description": post["text"][:220] + "..." if len(post["text"]) > 220 else post["text"],
                    "link": post["link"]
                })
                history.append(post["id"])

    save_history(history)
    build_dashboard(collected_leads)
    print(f"Cycle completed. Added {len(collected_leads)} unique client entries.")

if __name__ == "__main__":
    main()
