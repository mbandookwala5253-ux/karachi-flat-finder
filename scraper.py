import os
import re
import json
import time
import logging
import requests
import smtplib
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
    if "lakh" in price_str:
        try:
            val = float(re.findall(r"[\d\.]+", price_str)[0])
            return int(val * 100000)
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

def scrape_olx(max_budget):
    """Scrapes OLX Pakistan listings for multiple target areas close to the commutes."""
    listings = []
    
    queries = [
        {"q": "clifton", "default": "Clifton Area"},
        {"q": "pakistan-chowk", "default": "Pakistan Chowk Area"},
        {"q": "saddar", "default": "Pakistan Chowk Area"},
        {"q": "burns-road", "default": "Pakistan Chowk Area"},
        {"q": "bath-island", "default": "Clifton Area"},
        {"q": "gizri", "default": "Clifton Area"},
        {"q": "pechs", "default": "PECHS / Shabbirabad"},
        {"q": "shabbirabad", "default": "PECHS / Shabbirabad"},
        {"q": "garden-east", "default": "Pakistan Chowk Area"}
    ]
    
    with sync_playwright() as p:
        logging.info("Starting Playwright for OLX scraping...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # OLX search limit
        search_limit = max_budget + 5000
        
        for q_item in queries:
            query = q_item["q"]
            default_commute = q_item["default"]
            logging.info(f"Scraping OLX query '{query}'")
            
            url = f"https://www.olx.com.pk/karachi_g4060695/apartments-flats_c367/q-{query}?filter=price_to_{search_limit}"
            try:
                page.goto(url, timeout=30000)
                page.wait_for_timeout(3000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                page.wait_for_timeout(2000)
                
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                items = soup.find_all(attrs={"data-aut-id": "itemBox"})
                
                if not items:
                    links = soup.find_all("a", href=re.compile(r"/item/"))
                    items = []
                    seen_parents = set()
                    for link in links:
                        parent = link.find_parent("li") or link.find_parent("div", class_=re.compile(r"card|item|listing|product"))
                        if parent and parent not in seen_parents:
                            items.append(parent)
                            seen_parents.add(parent)
                
                for item in items:
                    try:
                        link_el = item.find("a", href=re.compile(r"/item/"))
                        if not link_el:
                            continue
                        link = "https://www.olx.com.pk" + link_el["href"] if link_el["href"].startswith("/") else link_el["href"]
                        
                        title_el = item.find(attrs={"data-aut-id": "itemTitle"}) or item.find("h2") or item.find("span", class_=re.compile(r"title"))
                        title = title_el.text.strip() if title_el else "Flat for rent"
                        
                        price_el = item.find(attrs={"data-aut-id": "itemPrice"}) or item.find("span", class_=re.compile(r"price|Price"))
                        price_str = price_el.text.strip() if price_el else "0"
                        price = clean_price(price_str)
                        
                        loc_el = item.find(attrs={"data-aut-id": "itemDetails"}) or item.find("span", class_=re.compile(r"location|Location"))
                        location_text = loc_el.text.strip() if loc_el else ""
                        
                        img_el = item.find("img")
                        img_url = ""
                        if img_el:
                            img_url = img_el.get("data-src") or img_el.get("src") or ""
                        
                        if price > max_budget or price < 10000:
                            continue
                            
                        # Work out commute region
                        matched_area = get_commute_area(title, location_text, default_commute)
                        
                        rooms = clean_rooms(title, "")
                        if rooms == 0:
                            rooms = 2
                            
                        listings.append({
                            "title": title,
                            "price": price,
                            "price_str": f"PKR {price:,}",
                            "location": location_text or query.capitalize(),
                            "area": matched_area,
                            "rooms": rooms,
                            "link": link,
                            "image": img_url or "https://via.placeholder.com/300x200?text=No+Image",
                            "source": "OLX",
                            "date": time.strftime("%Y-%m-%d")
                        })
                    except Exception as e:
                        logging.error(f"Error parsing OLX item: {e}")
            except Exception as e:
                logging.error(f"Error loading OLX URL for {query}: {e}")
                
        browser.close()
    return listings

def scrape_zameen(max_budget):
    """Scrapes Zameen.com listings for Clifton, Saddar, DHA, PECHS, and Bath Island."""
    listings = []
    
    # Location IDs: Clifton (118), Saddar/Pakistan Chowk (201), PECHS (184), Bath Island (116), Garden East (186)
    queries = [
        {"id": 118, "name": "Clifton", "default": "Clifton Area"},
        {"id": 201, "name": "Saddar", "default": "Pakistan Chowk Area"},
        {"id": 184, "name": "PECHS", "default": "PECHS / Shabbirabad"},
        {"id": 116, "name": "Bath_Island", "default": "Clifton Area"},
        {"id": 186, "name": "Garden_East", "default": "Pakistan Chowk Area"}
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
            url = f"https://www.zameen.com/Rent_Flats/Karachi_{loc_name}-{loc_id}-1.html?price_max={search_limit}"
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
                        
                        price_el = card.find("span", aria_label="Price") or card.find(class_=re.compile(r"price|Price"))
                        price_str = price_el.text.strip() if price_el else "0"
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

def scrape_google_listings(max_budget):
    """Queries Google search results for broader coverage including Facebook, Instagram, and Graana."""
    listings = []
    
    # Query matching multiple commute zones and budget
    query = f'flat for rent ("clifton" OR "pakistan chowk" OR "saddar" OR "pechs" OR "shabbirabad" OR "gizri" OR "bath island") karachi 20000..{max_budget} -site:zameen.com -site:olx.com.pk'
    url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
    
    with sync_playwright() as p:
        logging.info("Starting Playwright for Google search scraping...")
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            results = soup.find_all(class_="g")
            logging.info(f"Found {len(results)} potential Google search results")
            
            for res in results:
                try:
                    h3 = res.find("h3")
                    a_tag = res.find("a")
                    if not h3 or not a_tag:
                        continue
                        
                    link = a_tag["href"]
                    if not link.startswith("http") or "google.com" in link:
                        continue
                        
                    title = h3.text.strip()
                    
                    snippet_el = res.find(class_=re.compile(r"VwiC3b|yDAB2d|MUb15c"))
                    snippet = snippet_el.text.strip() if snippet_el else ""
                    
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
                        elif "ilaan.com" in dom:
                            source = "Ilaan"
                        elif "mitula" in dom:
                            source = "Mitula"
                        elif "lamudi" in dom:
                            source = "Lamudi"
                        else:
                            source = dom.split(".")[0].capitalize()
                            
                    combined_text = f"{title} {snippet}".lower()
                    
                    # Deduce commute zone
                    matched_area = get_commute_area(title, snippet, "PECHS / Shabbirabad")
                        
                    price = 45000
                    price_match = re.search(r"\b(1[5-9]|[2-4][0-9]|50),?000\b", combined_text)
                    if price_match:
                        try:
                            price = int(price_match.group(1).replace(",", "")) * 1000
                        except Exception:
                            pass
                    else:
                        k_match = re.search(r"\b(1[5-9]|[2-4][0-9]|50)\s*k\b", combined_text)
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
                    logging.error(f"Error parsing Google result details: {e}")
            browser.close()
        except Exception as e:
            logging.error(f"Google dorking scraper execution failed: {e}")
            
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

    # 2. Scrape OLX, Zameen, and Google Dorks
    olx_results = []
    zameen_results = []
    web_results = []
    
    try:
        if progress_callback:
            progress_callback("olx", f"Scanning OLX (Limit: PKR {max_budget:,})...")
        olx_results = scrape_olx(max_budget)
        logging.info(f"OLX search complete. Found {len(olx_results)} listings.")
    except Exception as e:
        logging.error(f"OLX scraper failed globally: {e}")
        
    try:
        if progress_callback:
            progress_callback("zameen", f"Scanning Zameen (Limit: PKR {max_budget:,})...")
        zameen_results = scrape_zameen(max_budget)
        logging.info(f"Zameen search complete. Found {len(zameen_results)} listings.")
    except Exception as e:
        logging.error(f"Zameen scraper failed globally: {e}")

    try:
        if progress_callback:
            progress_callback("google", f"Searching Google (Max: PKR {max_budget:,})...")
        web_results = scrape_google_listings(max_budget)
        logging.info(f"Google Web/Social search complete. Found {len(web_results)} listings.")
    except Exception as e:
        logging.error(f"Google Search scraper failed globally: {e}")
        
    all_results = olx_results + zameen_results + web_results
    
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
