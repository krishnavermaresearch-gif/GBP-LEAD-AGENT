"""
╔═══════════════════════════════════════════════════════╗
║         🤖 Kimi-Scout Pro — Lead Generation Agent     ║
║  Google Sheets → JustDial → Kimi K2 → Google Sheets   ║
╚═══════════════════════════════════════════════════════╝

Usage:
    python main.py                          # Run with config defaults
    python main.py --sheet-id YOUR_ID       # Override Sheet ID
    python main.py --limit 10               # Max businesses per search
    python main.py --dry-run                # Test connections only
"""

import argparse
import time
import sys
import hashlib

import config
import sheets_manager
import google_maps_scraper


def print_banner():
    print("\n" + "="*55)
    print("║" + " "*53 + "║")
    print("║" + "         🚀  GBP LEAD AGENT v1.0              ".center(53) + "║")
    print("║" + "         Google Business Profile Scraper      ".center(53) + "║")
    print("║" + " "*53 + "║")
    print("="*55 + "\n")
    print()


def run_dry_run():
    print("🧪 DRY RUN MODE — Testing connections...\n")

    print("─── Google Sheets ───")
    try:
        inputs = sheets_manager.read_inputs()
        if inputs:
            print(f"   Sample row: {inputs[0]}")
        print()
    except Exception as e:
        print(f"   ❌ Sheets error: {e}\n")

    print("─── Google Maps URL Format ───")
    sample_url = "https://www.google.com/maps/search/Tile+Manufacturers+in+Bandra+Mumbai"
    print(f"   Sample URL: {sample_url}")
    print(f"   (No actual request made in dry-run)")
    print()

    print("✅ Dry run complete.")


def process_row(input_row, limit, row_index, total_rows, finished_cache):
    """
    Process one input row: for each category, scrape → check website → summarize → collect results.
    """
    country = input_row.get("country", "")
    state = input_row.get("state", "")
    district = input_row.get("district", "")
    city = input_row.get("city", "")
    sub_city = input_row.get("sub_city", "")
    locality = input_row.get("locality", "")
    micro_location = input_row.get("micro_location", "")
    categories = input_row.get("categories", [])
    row_number = input_row.get("row_number", 0)

    loc_parts = [micro_location, locality, sub_city, city, district, state, country]
    valid_locs = [p.strip() for p in loc_parts if p.strip()]
    location_str = ", ".join(valid_locs)

    print(f"\n{'='*60}")
    print(f"📍 [{row_index}/{total_rows}] Processing: {location_str}")
    print(f"   Categories: {', '.join(categories)}")
    print(f"{'='*60}")

    all_results = []
    total_scraped = 0

    for cat_i, category in enumerate(categories, start=1):
        if (location_str, category) in finished_cache:
            print(f"\n  ⏭️  [SKIPPED] Category '{category}' already securely saved in Google Sheets for this location.")
            continue
            
        print(f"\n  📂 [{cat_i}/{len(categories)}] Category: {category}")
        print(f"  {'─'*40}")

        businesses = google_maps_scraper.scrape_google_maps(
            location=location_str,
            category=category,
            limit=limit
        )

        if not businesses:
            print(f"  ⚠️  No businesses found for '{category}' in {location_str}")
            continue

        for biz_i, biz in enumerate(businesses, start=1):
            name = biz.get("name", "Unknown")
            phone = biz.get("phone", "")
            address = biz.get("address", "")
            website = biz.get("website", "")
            gbp_link = biz.get("gbp_link", "")
            
            rating_str = biz.get("rating", "0")
            reviews_str = biz.get("reviews_count", "0")
            
            try:
                rating = float(rating_str)
            except ValueError:
                rating = 0.0
                
            try:
                reviews = int(reviews_str)
            except ValueError:
                reviews = 0

            has_website = "Yes" if website and website != "No Website" else "No"
            
            phone_digits = ''.join(filter(str.isdigit, phone))
            has_whatsapp = True
            if not phone_digits or len(phone_digits) < 10:
                has_whatsapp = False
            elif phone_digits.startswith('0') or phone_digits.startswith('1') or phone_digits.startswith('2'):
                has_whatsapp = False

            score = 0
            if has_website == "No":
                score += 3
            if rating < 4.0: # Includes 0.0 (no ratings)
                score += 2
            if reviews < 100: # Includes 0 (no reviews)
                score += 1
            if not has_whatsapp:
                score += 2
                
            main_problem = "Not Need"
            offer = "Advanced tech support"
            
            if has_website == "No":
                main_problem = "No website"
                offer = "Website build"
            elif not has_whatsapp:
                main_problem = "Slow response"
                offer = "WhatsApp system"
            elif rating < 4.0:
                main_problem = "Low conversion"
                offer = "Follow-up automation"
            elif reviews < 100:
                main_problem = "Low visibility"
                offer = "GBP optimization"

            print(f"    {biz_i}. Score: {score} | {name[:30]:<30} | {main_problem}")

            raw_id_string = f"{name}-{phone}-{location_str}"
            lead_id = hashlib.md5(raw_id_string.encode('utf-8')).hexdigest()[:10].upper()
            
            result_row = [
                name, category, str(rating), str(reviews),
                location_str, website, phone, has_website,
                main_problem, offer, str(score),
                gbp_link, "No", "New Lead", lead_id
            ]
            all_results.append(result_row)
            total_scraped += 1
            
            if len(all_results) >= config.BATCH_SAVE_SIZE:
                try:
                    sheets_manager.write_results(all_results)
                    print(f"  💾 Auto-saved chunk: {len(all_results)} leads secured safely.")
                    all_results = []
                except Exception as e:
                    print(f"  ❌ Auto-save failed: {e}")
                    _save_backup(all_results, row_number)
                    all_results = []
                    
    if all_results:
        try:
            sheets_manager.write_results(all_results)
        except Exception as e:
            print(f"  ❌ Failed to write results to sheet: {e}")
            _save_backup(all_results, row_number)

    try:
        sheets_manager.update_input_status(row_number)
    except Exception as e:
        print(f"  ⚠️  Could not mark row {row_number} as processed: {e}")

    return total_scraped


def _save_backup(results, row_number):
    import csv
    filename = f"backup_row_{row_number}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(config.OUTPUT_HEADERS)
        writer.writerows(results)
    print(f"  💾 Backup saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Kimi-Scout Pro — Lead Generation Agent")
    parser.add_argument("--sheet-id", help="Google Sheet ID (overrides config)")
    parser.add_argument("--limit", type=int, default=config.DEFAULT_LIMIT,
                        help=f"Max businesses per search (default: {config.DEFAULT_LIMIT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Test connections without scraping")
    args = parser.parse_args()

    print_banner()

    if args.sheet_id:
        config.GOOGLE_SHEET_ID = args.sheet_id

    if not config.GOOGLE_SHEET_ID:
        print("❌ No Google Sheet ID configured!")
        print("   Set it in config.py or pass --sheet-id YOUR_ID")
        sys.exit(1)

    if args.dry_run:
        run_dry_run()
        return

    print("🔄 Pre-flight checks...")
    print()

    print("📊 Reading inputs from Google Sheets...")
    try:
        inputs = sheets_manager.read_inputs()
    except Exception as e:
        print(f"❌ Failed to read Google Sheets: {e}")
        sys.exit(1)

    if not inputs:
        print("⚠️  No input rows to process. Add data to the Inputs tab.")
        sys.exit(0)

    print("\n🧠 Building Smart Deep Resume Cache from 'Results' tab...")
    finished_cache = sheets_manager.get_completed_categories()
    print(f"   (Detected {len(finished_cache)} successfully scraped category locations to safely skip.)")

    print(f"\n🚀 Starting processing: {len(inputs)} rows, limit={args.limit} per search\n")

    total_leads = 0
    start_time = time.time()

    for i, input_row in enumerate(inputs, start=1):
        try:
            leads = process_row(input_row, args.limit, i, len(inputs), finished_cache)
            total_leads += leads
        except KeyboardInterrupt:
            print("\n\n⏸️  Interrupted by user. Partial results have been saved.")
            break
        except Exception as e:
            print(f"\n❌ Error processing row {i}: {e}")
            continue

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"🏁 COMPLETE!")
    print(f"   Rows processed: {len(inputs)}")
    print(f"   Total leads found: {total_leads}")
    print(f"   Time taken: {elapsed:.1f}s")
    print(f"   Results saved to: Google Sheet → '{config.SHEET_OUTPUT_TAB}' tab")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
