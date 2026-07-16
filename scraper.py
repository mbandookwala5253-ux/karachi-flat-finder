import os
import re
import json
import time
import logging
import requests
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load local environment variables if available
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

DATA_FILE = "flats.json"
CONFIG_FILE = "config.json"

# Email Configuration
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def get_max_budget():
    """Loads the max budget from config.json, defaulting to 50000 if missing."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("max_budget", 50000))
        except Exception:
            pass
    return 50000

def send_email_alert(flat):
    """Sends a beautifully styled HTML email notification when a new flat is found."""
    if not EMAIL_USER or not EMAIL_PASS:
        logging.warning("Email credentials not fully set in .env. Skipping email alert.")
        return False
        
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🏠 [New Flat Found] {flat['area']} - {flat['price_str']}"
        msg['From'] = f"Karachi Flat Finder <{EMAIL_USER}>"
        msg['To'] = EMAIL_USER
        
        # HTML body matching dashboard theme
        html_body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Plus Jakarta Sans', Arial, sans-serif;
                    background-color: #090a0f;
                    color: #f3f4f6;
                    padding: 20px;
                    margin: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #161926;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                }}
                .header {{
                    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                    padding: 24px;
                    text-align: center;
                }}
                .header h1 {{
                    color: #ffffff;
                    margin: 0;
                    font-size: 24px;
                    font-weight: 700;
                }}
                .content {{
                    padding: 24px;
                }}
                .price-tag {{
                    font-size: 32px;
                    font-weight: 800;
                    color: #4ade80;
                    margin-bottom: 16px;
                }}
                .details-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 24px;
                }}
                .details-table td {{
                    padding: 10px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                }}
                .label {{
                    color: #9ca3af;
                    font-weight: bold;
                    width: 35%;
                }}
                .value {{
                    color: #ffffff;
                }}
                .btn-link {{
                    display: block;
                    text-align: center;
                    background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
                    color: #ffffff !important;
                    text-decoration: none;
                    font-weight: bold;
                    padding: 12px;
                    border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏢 New Property Alert!</h1>
                </div>
                <div class="content">
                    <div class="price-tag">{flat['price_str']}</div>
                    <h2 style="color: #ffffff; margin-top: 0; margin-bottom: 20px; font-size: 18px;">{flat['title']}</h2>
                    
                    <table class="details-table">
                        <tr>
                            <td class="label">📍 Area Category</td>
                            <td class="value">{flat['area']}</td>
                        </tr>
                        <tr>
                            <td class="label">🛏️ Rooms</td>
                            <td class="value">{flat['rooms']} Rooms</td>
                        </tr>
                        <tr>
                            <td class="label">📍 Location</td>
                            <td class="value">{flat['location']}</td>
                        </tr>
                        <tr>
                            <td class="label">👤 Seller Name</td>
                            <td class="value">{flat.get('contact_name', 'Not Available')}</td>
                        </tr>
                        <tr>
                            <td class="label">📞 Contact Phone</td>
                            <td class="value">{flat.get('contact_phone', 'Not Available')}</td>
                        </tr>
                        <tr>
                            <td class="label">🏷️ Source</td>
                            <td class="value">{flat['source']}</td>
                        </tr>
                    </table>
                    
                    <a href="{flat['link']}" target="_blank" class="btn-link">View Original Advertisement</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Connect to Gmail SMTP (SSL)
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        server.close()
        
        logging.info(f"Email alert successfully sent to {EMAIL_USER}!")
        return True
    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")
        return False

def fetch_contact_details(link, source):
    """Navigates to the listing detail page headlessly to extract advertiser names and phone numbers."""
    details = {"name": "Not Available", "phone": "Not Available"}
    
    with sync_playwright() as p:
        try:
            logging.info(f"Fetching detail page to extract contacts: {link}")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(link, timeout=20000)
            page.wait_for_timeout(2000)
            
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # 1. Try parsing JSON-LD Schema.org metadata
            schemas = soup.find_all("script", type="application/ld+json")
            for schema in schemas:
                try:
                    data = json.loads(schema.string)
                    data_list = data if isinstance(data, list) else [data]
                    for item in data_list:
                        if isinstance(item, dict):
                            if "seller" in item and isinstance(item["seller"], dict):
                                details["name"] = item["seller"].get("name", details["name"])
                                details["phone"] = item["seller"].get("telephone", details["phone"])
                            elif "contactPoint" in item:
                                cp = item["contactPoint"]
                                if isinstance(cp, dict):
                                    details["phone"] = cp.get("telephone", details["phone"])
                                    details["name"] = cp.get("name", details["name"])
                except Exception:
                    pass
            
            # 2. Platform-specific DOM parsing fallbacks
            if "zameen" in link.lower():
                agent_name_el = soup.find(class_=re.compile(r"agentName|agent-name|AgentName")) or soup.find("div", class_="_54a20b08")
                if agent_name_el:
                    details["name"] = agent_name_el.text.strip()
                    
            elif "olx" in link.lower():
                seller_name_el = soup.find(class_=re.compile(r"sellerName|seller-name|SellerProfile")) or soup.find(attrs={"data-aut-id": "profileCard"})
                if seller_name_el:
                    details["name"] = seller_name_el.text.split("\n")[0].strip()
                
                initial_state_match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", html)
                if initial_state_match:
                    try:
                        state_data = json.loads(initial_state_match.group(1))
                        user_info = state_data.get("user", {}).get("profile", {})
                        if user_info:
                            details["name"] = user_info.get("name", details["name"])
                            details["phone"] = user_info.get("phone", details["phone"])
                    except Exception:
                        pass
            
            # 3. Regex matching as a final fallback for telephone numbers in Pakistan format
            if details["phone"] == "Not Available":
                phone_match = re.search(r"\b(\+92[- ]??3[0-9]{2}[- ]??[0-9]{7}|03[0-9]{2}[- ]??[0-9]{7})\b", html)
                if phone_match:
                    details["phone"] = phone_match.group(1)
                    
            browser.close()
        except Exception as e:
            logging.error(f"Error fetching detail contact for {link}: {e}")
            
    return details

def clean_price(price_str):
    """Converts price strings like 'Rs 45,000', '45 Thousand', '3.5 Lakh' to integer."""
    if not price_str:
        return 0
    price_str = price_str.lower().replace(",", "").replace("rs", "").replace("pkr", "").strip()
    
    # Check for lakh
    if "lakh" in price_str or "lacs" in price_str or "lac" in price_str:
        try:
            val = float(re.findall(r"[\d\.]+", price_str)[0])
            return int(val * 100000)
        except Exception:
            pass
            
    # Check for crore
    if "crore" in price_str or "cr" in price_str:
        try:
            val = float(re.findall(r"[\d\.]+", price_str)[0])
            return int(val * 10000000)
        except Exception:
            pass

    # Check for thousand
    if "thousand" in price_str or "k" in price_str:
        try:
            val = float(re.findall(r"[\d\.]+", price_str)[0])
            return int(val * 1000)
        except Exception:
            pass

    # Extract all digits
    digits = re.findall(r"\d+", price_str)
    if digits:
        return int("".join(digits))
    return 0

def clean_rooms(title, description):
    """Infers bedroom count from title or description."""
    text = f"{title} {description}".lower()
    match = re.search(r"(\d)\s*(?:bed|br|room|bhk|bedroom)", text)
    if match:
        return int(match.group(1))
    return 0

def get_commute_area(title, location_text, default_area="Midway / PECHS"):
    """Infers whether an area is closer to Clifton commute, Pakistan Chowk commute, or midway."""
    combined = f"{title} {location_text}".lower()
    
    clifton_keywords = ["clifton", "bath island", "gizri", "dha", "defence", "civil lines", "cantt"]
    chowk_keywords = ["pakistan chowk", "saddar", "burns road", "aram bagh", "garden east", "garden west", "kharadar", "mithadar"]
    midway_keywords = ["pechs", "shabbirabad", "bahadurabad", "karsaz", "dhoraji"]
    
    # Check Clifton
    for k in clifton_keywords:
        if k in combined:
            return "Clifton Area"
            
    # Check Pakistan Chowk
    for k in chowk_keywords:
        if k in combined:
            return "Pakistan Chowk Area"
            
    # Check PECHS/Midway
    for k in midway_keywords:
        if k in combined:
            return "PECHS / Shabbirabad"
            
    return default_area

def scrape_zameen(max_budget):
    """Scrapes Zameen.com listings for Clifton, Saddar, PECHS, Bath Island, and Garden East."""
    listings = []
    
    # Corrected category mappings and location IDs for Zameen
    queries = [
        {"id": 5, "name": "Clifton", "default": "Clifton Area"},
        {"id": 304, "name": "Saddar", "default": "Pakistan Chowk Area"},
        {"id": 184, "name": "PECHS", "default": "PECHS / Shabbirabad"},
        {"id": 198, "name": "Bath_Island", "default": "Clifton Area"},
        {"id": 6922, "name": "Jamshed_Town_Garden_East", "default": "Pakistan Chowk Area"}
    ]
    
    with sync_playwright() as p:
        logging.info("Starting Playwright for Zameen scraping...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # Zameen search limit
        search_limit = max_budget + 5000
        
        for q_item in queries:
            loc_id = q_item["id"]
            loc_name = q_item["name"]
            default_commute = q_item["default"]
            
            logging.info(f"Scraping Zameen for {loc_name} (ID: {loc_id})")
            url = f"https://www.zameen.com/Rentals_Flats_Apartments/Karachi_{loc_name}-{loc_id}-1.html?price_max={search_limit}"
            try:
                page.goto(url, timeout=30000)
                page.wait_for_timeout(3000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                page.wait_for_timeout(2000)
                
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                property_links = soup.find_all("a", href=re.compile(r"/Property/|/Property-"))
                logging.info(f"Found {len(property_links)} property links on Zameen for {loc_name}")
                
                seen_links = set()
                for link_el in property_links:
                    try:
                        href = link_el["href"]
                        full_link = "https://www.zameen.com" + href if href.startswith("/") else href
                        if full_link in seen_links:
                            continue
                        seen_links.add(full_link)
                        
                        card = link_el.find_parent("li") or link_el.find_parent("div", role="article") or link_el.find_parent("article")
                        if not card:
                            continue
                            
                        title_el = card.find("h2") or card.find("div", aria_label="Title") or card.find("span", aria_label="Title")
                        title = title_el.text.strip() if title_el else "Apartment for rent"
                        
                        # Bulletproof Zameen Price Extraction
                        price_el = card.find("span", attrs={"aria-label": "Price"})
                        price_str = "0"
                        if price_el:
                            price_str = price_el.text.strip()
                        else:
                            # Sibling based price parsing fallback
                            currency_span = card.find("span", string=re.compile(r"PKR|Rs", re.I)) or card.find(string=re.compile(r"PKR|Rs", re.I))
                            if currency_span:
                                parent_span = currency_span.parent if currency_span.name != "span" else currency_span
                                for sib in parent_span.next_siblings:
                                    if sib.name == "span" and sib.text.strip():
                                        price_str = sib.text.strip()
                                        break
                                        
                        price = clean_price(price_str)
                        
                        loc_el = card.find("div", aria_label="Location") or card.find(class_=re.compile(r"location|Location"))
                        location_text = loc_el.text.strip() if loc_el else loc_name
                        
                        rooms_el = card.find("span", aria_label="Beds") or card.find(class_=re.compile(r"beds|Beds|bedroom|bed"))
                        rooms = 0
                        if rooms_el:
                            rooms_digits = re.findall(r"\d+", rooms_el.text)
                            if rooms_digits:
                                rooms = int(rooms_digits[0])
                        if rooms == 0:
                            rooms = clean_rooms(title, "")
                            if rooms == 0:
                                rooms = 2
                                
                        img_el = card.find("img")
                        img_url = ""
                        if img_el:
                            img_url = img_el.get("src") or img_el.get("data-src") or ""
                            
                        if price > max_budget or price < 10000:
                            continue
                            
                        matched_area = get_commute_area(title, location_text, default_commute)
                        
                        listings.append({
                            "title": title,
                            "price": price,
                            "price_str": f"PKR {price:,}",
                            "location": location_text,
                            "area": matched_area,
                            "rooms": rooms,
                            "link": full_link,
                            "image": img_url or "https://via.placeholder.com/300x200?text=No+Image",
                            "source": "Zameen",
                            "date": time.strftime("%Y-%m-%d")
                        })
                    except Exception as e:
                        logging.error(f"Error parsing Zameen item: {e}")
            except Exception as e:
                logging.error(f"Error loading Zameen URL for {loc_name}: {e}")
                
        browser.close()
    return listings

def scrape_web_listings(max_budget):
    """Queries DuckDuckGo HTML search results for broader coverage including Facebook, Instagram, OLX, and Graana."""
    listings = []
    
    # Query matching multiple commute zones and budget limit
    query = f'flat for rent ("clifton" OR "pakistan chowk" OR "saddar" OR "pechs" OR "shabbirabad" OR "gizri" OR "bath island") karachi rent'
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    logging.info(f"Querying DuckDuckGo HTML search for multi-platform listings...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logging.warning(f"DuckDuckGo search request failed with status: {response.status_code}")
            return listings
            
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all(class_="result")
        logging.info(f"Found {len(results)} potential search results on DuckDuckGo")
        
        for res in results:
            try:
                a = res.find("a", class_="result__a")
                snippet_el = res.find(class_="result__snippet")
                if not a or not snippet_el:
                    continue
                    
                title = a.text.strip()
                link_raw = a["href"]
                
                # Decode DuckDuckGo redirect link
                parsed_url = urllib.parse.urlparse(link_raw)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                link = query_params.get("uddg", [link_raw])[0]
                
                if not link.startswith("http") or "google.com" in link or "duckduckgo.com" in link:
                    continue
                    
                snippet = snippet_el.text.strip()
                
                domain_match = re.search(r"https?://(?:www\.)?([^/]+)", link)
                source = "Web Search"
                if domain_match:
                    dom = domain_match.group(1).lower()
                    if "facebook.com" in dom:
                        source = "Facebook Marketplace"
                    elif "instagram.com" in dom:
                        source = "Instagram"
                    elif "graana.com" in dom:
                        source = "Graana"
                    elif "bolee.com" in dom:
                        source = "Bolee"
                    elif "olx.com.pk" in dom:
                        source = "OLX"
                    elif "realproperty.pk" in dom:
                        source = "RealProperty"
                    elif "ilaan.com" in dom:
                        source = "Ilaan"
                    elif "mitula" in dom:
                        source = "Mitula"
                    elif "lamudi" in dom:
                        source = "Lamudi"
                    else:
                        source = dom.split(".")[0].capitalize()
                        
                combined_text = f"{title} {snippet}".lower()
                matched_area = get_commute_area(title, snippet, "PECHS / Shabbirabad")
                
                price = 45000
                price_match = re.search(r"\b(1[5-9]|[2-9][0-9]|100),?000\b", combined_text)
                if price_match:
                    try:
                        price = int(price_match.group(1).replace(",", "")) * 1000
                    except Exception:
                        pass
                else:
                    k_match = re.search(r"\b(1[5-9]|[2-9][0-9]|100)\s*k\b", combined_text)
                    if k_match:
                        try:
                            price = int(k_match.group(1)) * 1000
                        except Exception:
                            pass
                            
                if price > max_budget:
                    continue
                    
                rooms = 2
                rooms_match = re.search(r"(\d)\s*(?:bed|room|bedroom)", combined_text)
                if rooms_match:
                    rooms = int(rooms_match.group(1))
                    
                listings.append({
                    "title": title,
                    "price": price,
                    "price_str": f"PKR {price:,}",
                    "location": snippet[:60] + "..." if len(snippet) > 60 else (snippet or matched_area),
                    "area": matched_area,
                    "rooms": rooms,
                    "link": link,
                    "image": "https://via.placeholder.com/300x200?text=Social/Web+Ad",
                    "source": source,
                    "date": time.strftime("%Y-%m-%d")
                })
            except Exception as e:
                logging.error(f"Error parsing DuckDuckGo search result: {e}")
    except Exception as e:
        logging.error(f"DuckDuckGo search scraper failed: {e}")
        
    return listings

def run_scraper(progress_callback=None):
    """Runs scrapers for all portals, dedups, fetches contact details for new ads, and emails."""
    logging.info("Starting complete Karachi Flat Finder Scraper...")
    
    # Load dynamic config budget
    max_budget = get_max_budget()
    logging.info(f"Loaded Max Budget limit: PKR {max_budget:,}")

    if progress_callback:
        progress_callback("checking_db", "Loading local seen properties database...")
        
    # 1. Load existing listings to detect new ones
    existing_links = set()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for item in old_data:
                    normalized_link = item["link"].split("?")[0]
                    existing_links.add(normalized_link)
            logging.info(f"Loaded {len(existing_links)} existing listing links from {DATA_FILE}")
        except Exception as e:
            logging.error(f"Failed to read existing DATA_FILE: {e}")

    # 2. Scrape Zameen and Web Search
    zameen_results = []
    web_results = []
    
    if progress_callback:
        progress_callback("olx", "OLX direct scraper bypassed (relying on search fallbacks)...")
        time.sleep(1)
        
    try:
        if progress_callback:
            progress_callback("zameen", f"Scanning Zameen.com (Limit: PKR {max_budget:,})...")
        zameen_results = scrape_zameen(max_budget)
        logging.info(f"Zameen search complete. Found {len(zameen_results)} listings.")
    except Exception as e:
        logging.error(f"Zameen scraper failed globally: {e}")

    try:
        if progress_callback:
            progress_callback("google", f"Searching Web & Social portals (Max: PKR {max_budget:,})...")
        web_results = scrape_web_listings(max_budget)
        logging.info(f"DuckDuckGo Web/Social search complete. Found {len(web_results)} listings.")
    except Exception as e:
        logging.error(f"DuckDuckGo Search scraper failed globally: {e}")
        
    all_results = zameen_results + web_results
    
    # 3. Deduplicate listings
    unique_scraped = {}
    for item in all_results:
        normalized_link = item["link"].split("?")[0]
        if normalized_link not in unique_scraped:
            unique_scraped[normalized_link] = item
            
    current_listings = list(unique_scraped.values())
    
    # 4. Compare and identify brand-new listings
    new_listings_found = 0
    total_new = sum(1 for flat in current_listings if flat["link"].split("?")[0] not in existing_links)
    
    for idx, flat in enumerate(current_listings):
        normalized_link = flat["link"].split("?")[0]
        if normalized_link not in existing_links:
            new_listings_found += 1
            if progress_callback:
                progress_callback("contacts", f"Extracting contacts ({new_listings_found}/{total_new}): {flat['title'][:30]}...")
            
            logging.info(f"✨ Brand-new flat listing detected: {flat['title']} ({flat['price_str']})")
            
            # Fetch contact details for the new listing in real-time
            contact = fetch_contact_details(flat["link"], flat["source"])
            flat["contact_name"] = contact["name"]
            flat["contact_phone"] = contact["phone"]
            
            # Send Email Alert (Using credentials from Maimoon Dental Care)
            send_email_alert(flat)
            
            # Add to seen list to prevent duplicate alert on current run
            existing_links.add(normalized_link)
            
    logging.info(f"Scan complete. Discovered {new_listings_found} new flat listings.")

    if progress_callback:
        progress_callback("saving", "Sorting and writing updated results to database...")

    # 5. Sort combined list by price ascending
    current_listings.sort(key=lambda x: x["price"])
    
    # 6. Save back to flats.json
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(current_listings, f, indent=4, ensure_ascii=False)
        logging.info(f"Successfully updated property database with {len(current_listings)} listings in {DATA_FILE}")
    except Exception as e:
        logging.error(f"Failed to save listings to JSON file: {e}")
        
    return current_listings

if __name__ == "__main__":
    run_scraper()
