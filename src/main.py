# main.py

import os
import json
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from timeular.client import TimeularClient
from freshbooks.client import FreshbooksClient
from freshbooks.authentication import get_freshbooks_session
from timeular.csv_handler import load_time_entries_from_excel

def main():
    # Load environment variables
    load_dotenv()
    
    # Get API credentials from environment
    timeular_api_key = os.getenv("TIMEULAR_API_KEY")
    timeular_api_secret = os.getenv("TIMEULAR_API_SECRET")
    freshbooks_client_id = os.getenv("FRESHBOOKS_CLIENT_ID")
    freshbooks_client_secret = os.getenv("FRESHBOOKS_CLIENT_SECRET")
    freshbooks_business_id = os.getenv("FRESHBOOKS_BUSINESS_ID")
    
    # Check if credentials are available
    if not all([timeular_api_key, timeular_api_secret, freshbooks_client_id, freshbooks_client_secret, freshbooks_business_id]):
        print("Missing required environment variables. Please check your .env file.")
        return
    
    # Step 1: Authenticate with Freshbooks (this will open a browser for OAuth flow if needed)
    print("Authenticating with Freshbooks...")
    freshbooks_session = get_freshbooks_session(freshbooks_client_id, freshbooks_client_secret)
    
    if not freshbooks_session:
        print("Failed to authenticate with Freshbooks")
        return
    
    print("Freshbooks authentication successful!")
    
    # Step 2: Initialize Freshbooks client with the authenticated session
    freshbooks_client = FreshbooksClient(
        api_token=freshbooks_session.token['access_token'],
        business_id=freshbooks_business_id
    )
    
    # Step 3: Get clients from Freshbooks (needed for mapping Timeular activities to clients)
    print("Fetching clients from Freshbooks...")
    freshbooks_client.get_clients()
    
    # Step 4: Authenticate with Timeular
    print("Authenticating with Timeular...")
    timeular_client = TimeularClient(timeular_api_key, timeular_api_secret)
    try:
        timeular_client.authenticate()
        print("Timeular authentication successful!")
    except Exception as e:
        print(f"Failed to authenticate with Timeular: {e}")
        return
    
    # Step 5: Choose data source - Timeular API or CSV/Excel file
    use_file = input("Do you want to import time entries from a file? (y/n): ").lower() == 'y'
    
    if use_file:
        # Option A: Load time entries from Excel/CSV
        file_path = input("Enter the path to your Excel/CSV file: ")
        try:
            time_entries = load_time_entries_from_excel(file_path)
            print(f"Loaded {len(time_entries)} time entries from file")
        except Exception as e:
            print(f"Failed to load time entries from file: {e}")
            return
    else:
        # Option B: Get time entries from Timeular API
        days_back = int(input("How many days back do you want to fetch? (default: 30): ") or 30)
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=days_back)
        
        print(f"Fetching time entries from {start_date.date()} to {end_date.date()}...")
        
        try:
            raw_entries = timeular_client.get_time_entries(start_date, end_date)
            time_entries = timeular_client.format_entries(raw_entries)
            print(f"Retrieved {len(time_entries)} time entries from Timeular")
            
            # Save a summary report for reference
            summary = timeular_client.generate_summary_report(start_date, end_date)
            with open("timeular_summary.json", "w") as f:
                json.dump(summary, f, indent=2, default=str)
            print("Saved summary report to timeular_summary.json")
            
        except Exception as e:
            print(f"Failed to get time entries from Timeular: {e}")
            return
    
    # Step 6: Process entries for Freshbooks format
    print("Processing entries for Freshbooks...")
    freshbooks_entries = []
    
    for entry in time_entries:
        # Map Timeular entry fields to Freshbooks fields
        freshbooks_entry = {
            "duration": entry.get("duration_hours", 0),
            "startdate": entry.get("start_time", datetime.now()),
            "note": entry.get("note", ""),
            "billable": True,  # Set default billable status
            "activity": entry.get("activity_name", "")
        }
        
        # Add additional fields if available
        if "folder" in entry and entry["folder"]:
            freshbooks_entry["folderid"] = entry["folder"].get("id")
        
        freshbooks_entries.append(freshbooks_entry)
    
    # Step 7: Submit time entries to Freshbooks
    print(f"Submitting {len(freshbooks_entries)} time entries to Freshbooks...")
    
    results = freshbooks_client.create_time_entries_batch(freshbooks_entries)
    
    # Step 8: Output results
    print(f"\nSummary: {results['stats']['success']} entries created, {results['stats']['failure']} failed")
    
    if results['stats']['failure'] > 0:
        print("\nFailed entries:")
        for entry in results['failed']:
            print(f"- {entry.get('activity', 'Unknown')} ({entry.get('duration', 0)} hours): {entry.get('note', '')}")
    
    print("\nTime entries have been uploaded to Freshbooks!")

if __name__ == "__main__":
    main()