import sys
import os
import sheets_manager
import config

print("🔧 Pushing perfectly aligned headers to Google Sheets...")
try:
    service = sheets_manager._get_service()
    sheet = service.spreadsheets()
    sheet.values().update(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{config.SHEET_OUTPUT_TAB}!A1:Z1",
        valueInputOption="RAW",
        body={"values": [config.OUTPUT_HEADERS]}
    ).execute()
    print("✅ Header re-alignment complete!")
except Exception as e:
    print(f"❌ Error: {e}")
