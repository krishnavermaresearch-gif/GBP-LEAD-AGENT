import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

agent_1_dir = os.path.join(os.path.dirname(__file__), "..", "GBP lead agent")
sys.path.append(agent_1_dir)

import sheets_manager
import config as agent2_config

def get_cloud_analysis(website_text, business_name, category, rating, reviews):
    trimmed_text = website_text[:2000] if website_text else "[NO WEBSITE EXISTS - Recommend building a website online presence!]"
    
    prompt = f"""You are an elite Business Analyst and AI Automation Expert.
Analyze the following business lead using both their Google Business Profile stats AND their website text.

Business Name: {business_name}
Category: {category}
Google Reviews: {reviews} reviews (Average {rating} stars)

1. Provide a short, 1-sentence analysis of their current digital state based on their GBP reviews and Website text.
2. Suggest the BEST package from the list below and pitch it in 1 sentence.

Official Packages:
- Basic Presence (Setup: 3,999): 1-page website, GBP setup, Map visibility. Best for getting started.
- Growth System (Setup: 8,999 | Monthly: 3,499): Website, Lead capture, WhatsApp integration, auto-replies. Best for more leads.
- Pro Conversion System (Setup: 12,999 | Monthly: 4,999): Booking system, Advanced follow-ups, Lead filtering. Best for automated bookings.
- Advanced Automation (Setup: 20,000+ | Monthly: 8,000+): Full automation system, CRM setup, Review automation, Custom workflows. Best for high-growth.

3. Output EXACTLY ONE "Opportunity Type" from this strict list: [Basic Presence, Growth System, Pro Conversion System, Advanced Automation]
4. Determine the exact "Opportunity Strength": If website outdated -> HIGH. If no clear CTA/Booking -> HIGH. If just basic SEO issues -> MEDIUM.

Format strictly as:
Analysis: [Your analysis]
Pitch: [Your pitch]
Type: [Opportunity Type]
Strength: [HIGH or MEDIUM]

Website Text Snippet (If any):
{trimmed_text}
"""
    
    headers = {
        "Authorization": f"Bearer {agent2_config.CLOUD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": agent2_config.CLOUD_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(agent2_config.CLOUD_API_URL, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
            analysis = "Website analysis completed."
            pitch = "Consider an AI Voice Agent for improved leads."
            opp_type = "Advanced Automation"
            strength = "HIGH"
            
            for line in result.split('\n'):
                if line.startswith("Analysis:"): analysis = line.replace("Analysis:", "").strip()
                if line.startswith("Pitch:"): pitch = line.replace("Pitch:", "").strip()
                if line.startswith("Type:"): opp_type = line.replace("Type:", "").strip()
                if line.startswith("Strength:"): strength = line.replace("Strength:", "").strip()
                    
            return analysis, pitch, opp_type, strength
        else:
            print(f"  ⚠️  Cloud HTTP {response.status_code}: {response.text}")
            return f"API HTTP {response.status_code}", "Cannot generate pitch", "Advanced Automation", "MEDIUM"
    except Exception as e:
        print(f"  ⚠️  Cloud API error: {e}")
        return "Analysis skipped", "Standard Web/Growth package.", "Growth System", "MEDIUM"

def get_deal_value(offer):
    if "Basic Presence" in offer: return "₹3,999"
    if "Growth System" in offer: return "₹8,999 - ₹12,498"
    if "Pro Conversion System" in offer: return "₹12,999 - ₹17,998"
    if "Advanced Automation" in offer: return "₹20,000+"
    return "Unknown"

def get_next_action(priority, has_web):
    if priority == "HIGH 🔥": return "Send Message"
    if priority == "MEDIUM": return "Follow-up"
    return "Book Call"

def scrape_website(url):
    if not url or url.lower() == "no website":
        return ""
        
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
            
            print(f"  🕸️  [Chrome] Loading {url}...")
            page.goto(url, timeout=15000)
            
            html_content = page.content()
            import bs4
            soup = bs4.BeautifulSoup(html_content, "html.parser")
            
            for el in soup(["script", "style", "nav", "footer", "svg", "button", "iframe", "noscript"]):
                el.extract()
                
            important_tags = soup.find_all(['h1', 'h2', 'h3', 'p', 'li'])
            clean_text = "\n".join([tag.get_text(separator=' ', strip=True) for tag in important_tags if tag.get_text(strip=True)])
            
            browser.close()
            return clean_text
    except Exception as e:
        print(f"  🕸️  [Chrome] Could not load {url}: {e}")
        return ""

def process_agent_2():
    print("🚀 Starting Agent 2: Deep Analysis & Segmentation Mode")
    
    service = sheets_manager._get_service()
    sheet = service.spreadsheets()
    
    print(f"📊 Reading raw data from '{agent2_config.SHEET_INPUT_TAB}'...")
    try:
        result = sheet.values().get(
            spreadsheetId=agent2_config.GOOGLE_SHEET_ID,
            range=f"{agent2_config.SHEET_INPUT_TAB}!A:Z"
        ).execute()
    except Exception as e:
        print(f"❌ Failed to reach Agent 1 Data. Does '{agent2_config.SHEET_INPUT_TAB}' exist? ({e})")
        return
        
    rows = result.get("values", [])
    if not rows or len(rows) < 2:
        print("⚠️ No actual leads to process found in Agent 1 output.")
        return
        
    headers = rows[0]
    
    def get_idx(name):
        try:
            return headers.index(name)
        except ValueError:
            return -1
            
    idx_id = get_idx("Lead ID")
    idx_name = get_idx("Business Name")
    idx_cat = get_idx("Category")
    idx_rating = get_idx("Rating")
    idx_rev = get_idx("Reviews Count")
    idx_loc = get_idx("Location")
    idx_web = get_idx("Website")
    idx_phone = get_idx("Phone")
    idx_hasweb = get_idx("Has Website (Yes/No)")
    idx_gbplink = get_idx("GBP Profile Link")
    idx_contacted = get_idx("Contacted (Yes/No)")
    idx_status = get_idx("Status")
    
    core_leads = []
    advanced_leads = []
    processed_rows = []
    
    total_core_saved = 0
    total_advanced_saved = 0
    
    def flush_batches():
        nonlocal core_leads, advanced_leads, processed_rows, total_core_saved, total_advanced_saved
        if not processed_rows: return
        
        print(f"\n💾 [Auto-Save] Flushing chunk of {len(processed_rows)} leads securely to Google Sheets...")
        
        if core_leads:
            body1 = {"values": core_leads}
            try:
                sheet.values().append(
                    spreadsheetId=agent2_config.GOOGLE_SHEET_ID,
                    range=f"'{agent2_config.SHEET_OUTPUT_CORE}'!A:Z",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body=body1
                ).execute()
            except Exception as e:
                if "unable to parse range" in str(e).lower():
                    sheet.batchUpdate(spreadsheetId=agent2_config.GOOGLE_SHEET_ID, body={'requests': [{'addSheet': {'properties': {'title': agent2_config.SHEET_OUTPUT_CORE}}}]}).execute()
                    sheet.values().update(spreadsheetId=agent2_config.GOOGLE_SHEET_ID, range=f"'{agent2_config.SHEET_OUTPUT_CORE}'!A1:Z1", valueInputOption="RAW", body={"values": [agent2_config.CORE_HEADERS]}).execute()
                    sheet.values().append(spreadsheetId=agent2_config.GOOGLE_SHEET_ID, range=f"'{agent2_config.SHEET_OUTPUT_CORE}'!A:Z", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body=body1).execute()
                else:
                    print(f"❌ Error writing Core Leads: {e}")
                    
        if advanced_leads:
            body2 = {"values": advanced_leads}
            try:
                sheet.values().append(
                    spreadsheetId=agent2_config.GOOGLE_SHEET_ID,
                    range=f"'{agent2_config.SHEET_OUTPUT_ADVANCED}'!A:Z",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body=body2
                ).execute()
            except Exception as e:
                if "unable to parse range" in str(e).lower():
                    sheet.batchUpdate(spreadsheetId=agent2_config.GOOGLE_SHEET_ID, body={'requests': [{'addSheet': {'properties': {'title': agent2_config.SHEET_OUTPUT_ADVANCED}}}]}).execute()
                    sheet.values().update(spreadsheetId=agent2_config.GOOGLE_SHEET_ID, range=f"'{agent2_config.SHEET_OUTPUT_ADVANCED}'!A1:Z1", valueInputOption="RAW", body={"values": [agent2_config.ADVANCED_HEADERS]}).execute()
                    sheet.values().append(spreadsheetId=agent2_config.GOOGLE_SHEET_ID, range=f"'{agent2_config.SHEET_OUTPUT_ADVANCED}'!A:Z", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body=body2).execute()
                else:
                    print(f"❌ Error writing Advanced Leads: {e}")
                    
        status_col_letter = chr(ord('A') + idx_status) if idx_status < 26 else 'N'
        id_col_letter = chr(ord('A') + idx_id) if idx_id < 26 else 'O'
        
        data_updates = []
        for p_row in processed_rows:
            r_idx = p_row['ridx']
            lead_id_value = p_row['lead_id']
            
            data_updates.append({
                "range": f"'{agent2_config.SHEET_INPUT_TAB}'!{status_col_letter}{r_idx}",
                "values": [["Processed"]]
            })
            if idx_id != -1:
                data_updates.append({
                    "range": f"'{agent2_config.SHEET_INPUT_TAB}'!{id_col_letter}{r_idx}",
                    "values": [[lead_id_value]]
                })
            
        try:
            sheet.values().batchUpdate(
                spreadsheetId=agent2_config.GOOGLE_SHEET_ID,
                body={
                    "valueInputOption": "RAW",
                    "data": data_updates
                }
            ).execute()
            print(f"  👉 Synced {len(processed_rows)} Lead IDs back to Results and Ticked as Processed.")
        except Exception as e:
             print(f"❌ Could not sync old leads back to Results: {e}")
             
        total_core_saved += len(core_leads)
        total_advanced_saved += len(advanced_leads)
        
        core_leads.clear()
        advanced_leads.clear()
        processed_rows.clear()
    
    print(f"🧹 Commencing split-filter on {len(rows)-1} leads...\n")
    
    for ridx, row in enumerate(rows[1:], start=2):
        def val(idx):
            return row[idx] if idx != -1 and idx < len(row) else ""
            
        lead_id = val(idx_id)
        name = val(idx_name)
        cat = val(idx_cat)
        rating_str = val(idx_rating)
        rev_str = val(idx_rev)
        loc = val(idx_loc)
        phone = val(idx_phone)
        
        if not lead_id: 
            import hashlib
            raw_id_string = f"{name}-{phone}-{loc}"
            lead_id = hashlib.md5(raw_id_string.encode('utf-8')).hexdigest()[:10].upper()
        web = val(idx_web)
        gbp_link = val(idx_gbplink)
        has_web = val(idx_hasweb)
        contacted = val(idx_contacted)
        status = val(idx_status)
        
        if status != "New Lead":
            continue
        
        is_big_brand = any(b.lower() in name.lower() for b in agent2_config.BIG_BRANDS)
        if is_big_brand:
            processed_rows.append({"ridx": ridx, "lead_id": lead_id})
            continue
            
        try: rating = float(rating_str)
        except ValueError: rating = 0.0
            
        try: reviews = int(rev_str)
        except ValueError: reviews = 0
        
        if reviews > 1000:
            processed_rows.append({"ridx": ridx, "lead_id": lead_id})
            continue
            
        if has_web.lower() == "yes":
            print(f"  🧠 [AI Evaluation] Assessing GBP Profile & Website >> {name} ({reviews} reviews at {rating}⭐)")
            
            website_text = scrape_website(web)
            analysis, pitch, opp_type, strength = get_cloud_analysis(website_text, name, cat, rating, reviews)
            deal_val = get_deal_value(opp_type)
            
            if opp_type in ["Basic Presence", "Growth System"]:
                score = 6 if strength == "HIGH" else 3
                priority = "HIGH 🔥" if strength == "HIGH" else "MEDIUM"
                contact_ready = "YES" if strength == "HIGH" else "NO"
                next_action = get_next_action(priority, web)
                core_leads.append([lead_id, name, phone, gbp_link, contacted, loc, analysis, opp_type, score, priority, contact_ready, deal_val, next_action])
            else:
                next_action = "Book Call" if strength == "HIGH" else "Follow-up"
                advanced_leads.append([lead_id, name, phone, web, gbp_link, contacted, analysis, pitch, opp_type, strength, deal_val, next_action])
        else:
            score = 3
            problem_parts = ["No presence"]
            if rating < 4.0: score += 2; problem_parts.append("Low trust")
            if reviews < 100: score += 2; problem_parts.append("Low visibility")
            
            problemStr = " + ".join(problem_parts)
            offer = "Basic Presence"
            priority = "LOW"
            if score >= 6: priority = "HIGH 🔥"
            elif score >= 3: priority = "MEDIUM"
            
            contact_ready = "YES" if priority == "HIGH 🔥" else "NO"
            deal_val = get_deal_value(offer)
            next_action = get_next_action(priority, web)
            core_leads.append([lead_id, name, phone, gbp_link, contacted, loc, problemStr, offer, score, priority, contact_ready, deal_val, next_action])
            
        processed_rows.append({"ridx": ridx, "lead_id": lead_id})
        
        if len(processed_rows) >= 15:
            flush_batches()

    if processed_rows:
        flush_batches()

    if total_core_saved == 0 and total_advanced_saved == 0:
        print("✅ No 'New Lead' rows found. Everything is fully updated!")
    else:
        print(f"\n✅ SUCCESS! Segmented raw data into:")
        print(f"   - {total_core_saved} Tier 1 (Core Optimization) targeted leads.")
        print(f"   - {total_advanced_saved} Tier 2 (High-Ticket AI Automation) targeted leads.")

if __name__ == "__main__":
    process_agent_2()
