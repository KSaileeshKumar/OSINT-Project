#!/usr/bin/env python3
"""
OSINT Footprint Minimizer - Web Version
Flask-based web application for browser deployment
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import time
import re

app = Flask(__name__)

# --- CONFIGURATION ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

# --- SERVICES DATA STRUCTURE ---
SERVICES = {
    "GitHub": {
        "id": 1,
        "url": "https://github.com/{}",
        "type": "status", 
        "risk": "Medium",
        "advice": "Check public activity and committed email addresses."
    },
    "Reddit": {
        "id": 2,
        "url": "https://www.reddit.com/user/{}/about.json", 
        "display_url": "https://www.reddit.com/user/{}",
        "type": "json", 
        "risk": "Medium",
        "advice": "Scrub comments for location/personal info."
    },
    "Facebook": {
        "id": 3,
        "url": "https://www.facebook.com/{}",
        "type": "redirect_check", 
        "risk": "High",
        "advice": "Set 'Search Engine Indexing' to OFF."
    },
    "Instagram": {
        "id": 4,
        "url": "https://www.instagram.com/{}/",
        "type": "text_search",
        "error_text": "page not found",
        "risk": "Medium",
        "advice": "Set account to Private."
    },
    "Twitter (X)": {
        "id": 5,
        "url": "https://nitter.net/{}", 
        "display_url": "https://x.com/{}",
        "type": "status", 
        "risk": "Medium",
        "advice": "Enable 2FA and remove location tagging."
    },
    "Pinterest": {
        "id": 6,
        "url": "https://www.pinterest.com/{}",
        "type": "text_search",
        "error_text": "user not found",
        "risk": "Low",
        "advice": "Use a pseudonym."
    }
}

# --- CORE LOGIC FUNCTIONS ---

def check_service(username, service_name, service_data, session):
    """Checks a specific service using logic tailored to that platform."""
    target_url = service_data["url"].format(username)
    display_url = service_data.get("display_url", target_url).format(username)
    check_type = service_data["type"]
    
    try:
        response = session.get(target_url, headers=HEADERS, timeout=10, allow_redirects=True)
        
        if check_type == "json":
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "error" in data or ("data" not in data and "kind" not in data):
                        return False, display_url
                    return True, display_url
                except:
                    return False, display_url
            return False, display_url

        elif check_type == "redirect_check":
            current_url = response.url.lower()
            if any(x in current_url for x in ["login", "home.php", "auth", "signup", "unavailable", "404"]):
                return False, display_url
            if response.status_code == 200:
                return True, display_url
            return False, display_url

        elif check_type == "text_search":
            error_msg = service_data.get("error_text", "not found").lower()
            if response.status_code == 200:
                if error_msg in response.text.lower():
                    return False, display_url
                return True, display_url
            return False, display_url

        else:
            if response.status_code == 200:
                return True, display_url
            return False, display_url

    except Exception as e:
        return False, display_url

# --- FLASK ROUTES ---

@app.route('/')
def index():
    """Main page with scan form."""
    return render_template('index.html', services=SERVICES)

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    """Scan results page."""
    if request.method == 'GET':
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    platforms = request.form.getlist('platforms')
    
    if not username:
        return redirect(url_for('index'))
    
    if not platforms:
        return redirect(url_for('index'))
    
    session = requests.Session()
    results = []
    found_count = 0

    for platform_name in platforms:
        service_data = SERVICES[platform_name]
        time.sleep(0.5)
        
        result, url = check_service(username, platform_name, service_data, session)
        
        status = "NOT_FOUND"
        status_class = "not-found"
        
        if result == True:
            found_count += 1
            status = "FOUND"
            status_class = "found"
        
        results.append({
            "service": platform_name,
            "status": status,
            "status_class": status_class,
            "risk": service_data["risk"],
            "url": url,
            "advice": service_data["advice"]
        })
    
    return render_template('results.html', 
                         username=username,
                         results=results,
                         found_count=found_count,
                         total_scanned=len(platforms))

@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')

@app.errorhandler(404)
def page_not_found(e):
    """404 error handler."""
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)