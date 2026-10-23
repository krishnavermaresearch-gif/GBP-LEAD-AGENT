import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_credentials():
    """Authenticate via OAuth 2.0 (opens browser on first run, then reuses token)."""
    creds = None

    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CREDENTIALS_FILE, SCOPES,
            )
            creds = flow.run_local_server(port=8080, prompt="consent")

        with open(config.TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def _get_service():
    """Build Google Sheets API service."""
    creds = _get_credentials()
    return build("sheets", "v4", credentials=creds)


def read_inputs():
    """
    Read input rows from the Inputs tab.
    Returns list of dicts:
      {"state": "...", "city": "...", "subcity": "...", "categories": ["...", ...]}
    """
    service = _get_service()
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{config.SHEET_INPUT_TAB}!A:Z"
    ).execute()

    rows = result.get("values", [])

    if not rows:
        print("⚠️  No data found in Inputs tab.")
        return []

    inputs = []
    for i, row in enumerate(rows[1:], start=2):
        # Pad row with empty strings up to at least 8 columns to avoid IndexErrors
        row = row + [""] * max(0, 8 - len(row))

        country = row[0].strip() if len(row) > 0 else ""
        state = row[1].strip() if len(row) > 1 else ""
        district = row[2].strip() if len(row) > 2 else ""
        city = row[3].strip() if len(row) > 3 else ""
        sub_city = row[4].strip() if len(row) > 4 else ""
        locality = row[5].strip() if len(row) > 5 else ""
        micro_location = row[6].strip() if len(row) > 6 else ""

        categories = []
        for c in row[7:]:
            c_clean = c.strip()
            if c_clean and not c_clean.startswith("✅"):
                categories.append(c_clean)

        if len(categories) == 1 and categories[0].upper() == "ALL":
            print(f"  ⚡ 'ALL' Keyword Detected! Expanding to entire {len(config.MASTER_CATEGORIES)}-category master list.")
            categories = config.MASTER_CATEGORIES

        if not categories:
            print(f"⚠️  Row {i}: Skipping (At least 1 Category required, or already processed)")
            continue

        inputs.append({
            "country": country,
            "state": state,
            "district": district,
            "city": city,
            "sub_city": sub_city,
            "locality": locality,
            "micro_location": micro_location,
            "categories": categories,
            "row_number": i
        })

    print(f"✅ Read {len(inputs)} input rows from '{config.SHEET_INPUT_TAB}'")
    return inputs


def write_results(results):
    """
    Write result rows to the Results tab.
    Each result is a list: [State, City, Subcity, Category, Name, Phone, Address, Website, Summary, Status]
    """
    if not results:
        print("⚠️  No results to write.")
        return

    service = _get_service()
    sheet = service.spreadsheets()

    try:
        existing = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range=f"{config.SHEET_OUTPUT_TAB}!A1:Z1"
        ).execute()
    except Exception as e:
        if "Unable to parse range" in str(e):
            print(f"  ⚠️  Tab '{config.SHEET_OUTPUT_TAB}' not found. Re-creating it automatically...")
            sheet.batchUpdate(
                spreadsheetId=config.GOOGLE_SHEET_ID,
                body={'requests': [{'addSheet': {'properties': {'title': config.SHEET_OUTPUT_TAB}}}]}
            ).execute()
            existing = {}
        else:
            raise e

    sheet.values().update(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{config.SHEET_OUTPUT_TAB}!A1:Z1",
        valueInputOption="RAW",
        body={"values": [config.OUTPUT_HEADERS]}
    ).execute()

    sheet.values().append(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{config.SHEET_OUTPUT_TAB}!A:Z",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": results}
    ).execute()

    print(f"✅ Wrote {len(results)} rows to '{config.SHEET_OUTPUT_TAB}'")


def update_input_status(row_number, status="✅ Processed"):
    """Mark an input row as processed by writing status to the last used column."""
    service = _get_service()
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{config.SHEET_INPUT_TAB}!A{row_number}:Z{row_number}"
    ).execute()

    row = result.get("values", [[]])[0]
    next_col = chr(ord("A") + len(row))

    sheet.values().update(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{config.SHEET_INPUT_TAB}!{next_col}{row_number}",
        valueInputOption="RAW",
        body={"values": [[status]]}
    ).execute()


def get_completed_categories():
    """
    Reads the 'Results' tab and extracts a memory-cache of all uniquely 
    completed (Location, Category) combinations for 'Deep Resume' logic.
    """
    service = _get_service()
    sheet = service.spreadsheets()
    try:
        result = sheet.values().get(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range=f"{config.SHEET_OUTPUT_TAB}!B:E"
        ).execute()
        
        rows = result.get("values", [])
        completed_cache = set()
        
        for row in rows[1:]:
            if len(row) >= 4:
                cat = row[0].strip()
                loc = row[3].strip()
                completed_cache.add((loc, cat))
                
        return completed_cache
    except Exception as e:
        print(f"  ⚠️ Could not build Deep Resume cache (first run?): {e}")
        return set()
