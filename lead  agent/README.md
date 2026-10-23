# GBP LEAD AGENT 🤖
**Google Maps Lead Generation & Smart Filtering Engine**

This is a local, lightweight Python agent designed to extract high-quality B2B and B2C leads directly from Google Maps. It automatically bypasses Google's dynamic rendering by using headless Chromium (Playwright) to physically click and load individual business profiles, ensuring it perfectly captures hidden phone numbers and website links.

## 🌟 Key Features
* **Deep-Click Extraction:** Physically clicks into every individual Google Maps profile behind-the-scenes to securely rip the contact information (handles standard and obfuscated DOM structures).
* **7-Tier Geographic Mapping:** Pass hyper-local coordinates dynamically from your Google Sheet (Country, State, District, City, Sub-City, Locality, Micro-Location).
* **Smart Logic Opportunity Scoring:** Instantly calculates an Opportunity Score (0 to 8) based on whether the lead has a website, weak ratings, low reviews, or runs a landline phone.
* **Intelligent Pitch Assignment:** Automatically assigns "Main Problem" and "Offer" tags (e.g., *Website Build*, *WhatsApp Automation*, or *Advanced Tech Support*) based on their calculated flaws.
* **Auto-ALL Mode:** Enter `ALL` in the category column to instantly run a heavy-duty scrape pulling from a master dictionary of 60+ prime local business categories.
* **Crash-Resilient Backup System:** If the Google Sheets API ever fails or restricts limits, the agent automatically drops all scraped leads into a local `.csv` file on your hard drive so you never lose data.

---

## 🛠️ Setup & Installation

**1. Install Python Dependencies:**
Open your terminal inside this directory and run:
`pip install -r requirements.txt`

**2. Install the Headless Browser Engine:**
This downloads the invisible Chromium browser used to simulate human clicks:
`playwright install chromium`

**3. Google Sheets Authentication:**
Ensure `credentials.json` (your Google Cloud Service Account key) and `token.json` (your active API session) are in this folder alongside the script.

---

## 🏃 Running the Agent

**1. Configure your Google Sheet Inputs:**
Open the `Inputs` tab of your Google Sheet. Your target location must be placed in the first 7 columns **(A through G)**. Your target categories must start from **Column H** onward.
*(Note: You can intentionally leave location columns blank! The agent will dynamically pad them and still extract the data successfully).*

**2. Start the Scraper:**
Run the master orchestrator from your terminal:
`python main.py`

**3. View your Results:**
The script will sequentially process every row, evaluate every lead in milliseconds, and inject the clean, categorized data into your `Results` tab spanning exactly 13 columns.

---

## 💡 Pro-Tips
- **AI Consulting:** Highly optimized businesses (Score: 0) are perfectly tagged for `Advanced tech support` pitching, as they already possess the foundational setup to purchase expensive AI automations.
- **Limit Constraints:** You can force the bot to run a short test limit anytime by typing: `python main.py --limit 5`
