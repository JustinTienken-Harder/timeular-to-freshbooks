import requests
import json
from datetime import datetime, timedelta
import pytz

class TimeularClient:
    BASE_URL = "https://api.timeular.com/api/v4"
    
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.token = None
        
    def authenticate(self):
        """Authenticate with the Timeular API and get an access token."""
        auth_url = f"{self.BASE_URL}/developer/sign-in"
        headers = {"Content-Type": "application/json"}
        payload = {
            "apiKey": self.api_key,
            "apiSecret": self.secret_key
        }
        
        response = requests.post(auth_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            self.token = response.json()["token"]
            return True
        else:
            raise Exception(f"Authentication failed to Timeular: {response.status_code} - {response.text}")
    
    def get_headers(self):
        """Get headers with authentication token."""
        if not self.token:
            self.authenticate()
        
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_activities(self):
        """Get all activities from Timeular."""
        url = f"{self.BASE_URL}/activities"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            return response.json()["activities"]
        else:
            raise Exception(f"Failed to get activities: {response.status_code} - {response.text}")
    
    def get_time_entries(self, start_date=None, end_date=None):
        """
        Get time entries from Timeular for a date range.
        
        Args:
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to today)
            
        Returns:
            List of time entries
        """
        # Default to last week if no dates provided
        if not start_date:
            start_date = datetime.now(pytz.UTC) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(pytz.UTC)
            
        # Format dates for Timeular API (ISO 8601 format with timezone)
        # Using the exact format Timeular expects: YYYY-MM-DDThh:mm:ss.SSS
        start_iso = start_date.strftime("%Y-%m-%dT%H:%M:%S.987")
        end_iso = end_date.strftime("%Y-%m-%dT%H:%M:%S.987")
        
        print(f"Fetching entries from {start_iso} to {end_iso}")
        
        url = f"{self.BASE_URL}/time-entries/{start_iso}/{end_iso}"
        
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            return response.json()["timeEntries"]
        else:
            error_message = f"Failed to get time entries: {response.status_code} - {response.text}"
            print(f"URL attempted: {url}")
            raise Exception(error_message)
    
    def get_last_week_entries(self):
        """
        Get time entries from the last week.
        
        Returns:
            List of time entries formatted for easy use
        """
        # Calculate last week's date range
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=7)
        
        # Get raw entries
        entries = self.get_time_entries(start_date, end_date)
        return self.format_entries(entries)
    
    def format_entries(self, entries):        
        # Format entries for easier use
        formatted_entries = []
        
        for entry in entries:
            # Get activity details directly from the entry structure
            activity = entry.get('activity', {})
            activity_id = activity.get('id')
            activity_name = activity.get('name', 'Unknown Activity')
            
            # Get duration information
            duration = entry.get('duration', {})
            start_time_str = duration.get('startedAt')
            end_time_str = duration.get('stoppedAt')
            
            # Parse timestamps to datetime objects
            if start_time_str:
                # Remove milliseconds if present and handle timezone
                start_time_str = start_time_str.split('.')[0] + 'Z'
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            else:
                start_time = None
                
            if end_time_str:
                # Remove milliseconds if present and handle timezone
                end_time_str = end_time_str.split('.')[0] + 'Z'
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            else:
                end_time = None
            
            # Calculate duration in hours
            if start_time and end_time:
                duration_hours = (end_time - start_time).total_seconds() / 3600
            else:
                duration_hours = 0
                
            # Get note text
            note_obj = entry.get('note', {})
            note_text = note_obj.get('text', '')
            
            # Get tags if present
            tags = note_obj.get('tags', [])
            def rounding(duration_hours):
                """Rounds up to the nearest half hour. 
                If the duration is less than 15 minutes, it rounds up to 15 minutes"""
                if duration_hours < 0.25:
                    return 0.25
                elif duration_hours < 0.5:
                    return 0.5
                else:
                    return round(duration_hours * 2) / 2
            # Format the entry
            formatted_entry = {
                "id": entry.get('id'),
                "activity_id": activity_id,
                "activity_name": activity_name,
                "start_time": start_time,
                "end_time": end_time,
                "duration_hours": rounding(duration_hours),
                "note": note_text,
                "tags": tags,
                "is_ongoing": end_time is None
            }
            
            formatted_entries.append(formatted_entry)
        
        return formatted_entries

    def generate_report(self, start_date=None, end_date=None, format_type="json"):
        """
        Generate a report from Timeular for a date range.
        
        Args:
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to today)
            format_type: Output format ("json", "pdf", "csv", or "xlsx")
            
        Returns:
            Report data in the requested format
        """
        # Default to last week if no dates provided
        if not start_date:
            start_date = datetime.now(pytz.UTC) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(pytz.UTC)
            
        # Format dates as simple ISO dates for the reports endpoint
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        print(f"Generating report from {start_date_str} to {end_date_str}")
        
        url = f"{self.BASE_URL}/report"
        
        # Set up request parameters based on format type
        if format_type.lower() == "json":
            url = f"{self.BASE_URL}/report"
            payload = {
                "date": {
                    "start": start_date_str,
                    "end": end_date_str
                },
                'fileType': "json",
                "timezone": "UTC",
                "userIds": [],  # Empty for current user
                "showBillableTime": True,
                "showTrackedTime": True
            }
            
            response = requests.post(url, json=payload, headers=self.get_headers())
            
            if response.status_code == 200:
                return response.json()
            else:
                error_message = f"Failed to generate report: {response.status_code} - {response.text}"
                print(f"URL attempted: {url}")
                raise Exception(error_message)
                
        else:
            # For PDF, CSV, XLSX formats
            format_type = format_type.lower()
            if format_type not in ["pdf", "csv", "xlsx"]:
                raise ValueError(f"Unsupported format: {format_type}. Use 'pdf', 'csv', 'xlsx', or 'json'")
            
            url = f"{self.BASE_URL}/report"
            payload = {
                "date": {
                    "start": start_date_str,
                    "end": end_date_str
                },
                'fileType': f"{format_type}",
                "timezone": "UTC",
                "userIds": [],
                "showTrackedTime": True,
                "showBillableTime": True
            }
            
            response = requests.post(url, json=payload, headers=self.get_headers())
            
            if response.status_code == 200:
                # For file downloads, return the binary content
                return response.content
            else:
                error_message = f"Failed to generate {format_type} report: {response.status_code} - {response.text}"
                print(f"URL attempted: {url}")
                raise Exception(error_message)

    def generate_and_save_report(self, start_date=None, end_date=None, format_type="pdf", output_path=None):
        """
        Generate a report and save it to a file.
        
        Args:
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to today)
            format_type: Output format ("pdf", "csv", or "xlsx")
            output_path: Path to save the file (defaults to report.<format> in current directory)
            
        Returns:
            Path to the saved file
        """
        # Generate the report
        report_data = self.generate_report(start_date, end_date, format_type)
        
        # Default output path if not provided
        if not output_path:
            if format_type.lower() == "json":
                output_path = f"timeular_report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.json"
            else:
                output_path = f"timeular_report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.{format_type.lower()}"
        
        # Save the report
        if format_type.lower() == "json":
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2)
        else:
            # For binary files (PDF, CSV, XLSX)
            with open(output_path, 'wb') as f:
                f.write(report_data)
        
        print(f"Report saved to: {output_path}")
        return output_path

    def generate_summary_report(self, start_date=None, end_date=None):
        """
        Generate a summary report of time entries grouped by activity.
        
        Args:
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to today)
            
        Returns:
            Dictionary with summary information
        """
        # Get formatted time entries for the period
        if not start_date:
            start_date = datetime.now(pytz.UTC) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(pytz.UTC)
            
        entries = self.get_time_entries(start_date, end_date)
        formatted_entries = self.format_entries(entries)
        
        # Group by activity
        activity_totals = {}
        daily_totals = {}
        
        for entry in formatted_entries:
            activity = entry["activity_name"]
            date_str = entry["start_time"].strftime("%Y-%m-%d") if entry["start_time"] else "No date"
            
            # Add to activity totals
            if activity not in activity_totals:
                activity_totals[activity] = {
                    "total_hours": 0,
                    "entry_count": 0,
                    "entries": []
                }
            
            activity_totals[activity]["total_hours"] += entry["duration_hours"]
            activity_totals[activity]["entry_count"] += 1
            activity_totals[activity]["entries"].append(entry)
            
            # Add to daily totals
            if date_str not in daily_totals:
                daily_totals[date_str] = 0
            daily_totals[date_str] += entry["duration_hours"]
        
        # Calculate grand total
        grand_total = sum(activity["total_hours"] for activity in activity_totals.values())
        
        # Format the summary report
        summary = {
            "period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            "activity_totals": activity_totals,
            "daily_totals": daily_totals,
            "grand_total": grand_total
        }
        
        return summary


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)



if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("TIMEULAR_API_KEY")
    api_secret = os.getenv("TIMEULAR_API_SECRET")
    
    if not api_key or not api_secret:
        print("Please set TIMEULAR_API_KEY and TIMEULAR_API_SECRET environment variables")
        exit(1)
    
    client = TimeularClient(api_key, api_secret)
    try:
        client.authenticate()
        print("Authentication successful!")
        #get a report of last week:
        report = client.generate_report(datetime.now(pytz.UTC) - timedelta(days=30), format_type='csv')
        print(report)
        # pretty_json = json.dumps(report, indent=4, cls=DateTimeEncoder)
        # print(pretty_json)
        # json.dump(report, open("timeular_report.json", "w"), indent=4, cls = DateTimeEncoder)
    except Exception as e:
        print(f"Error: {str(e)}")
    # try:
    #     # Authenticate with Timeular
    #     client.authenticate()
    #     print("Authentication successful!")
        
    #     # Get entries from last week
    #     print("\nFetching time entries from the last week...")
    #     # entries = client.get_last_week_entries()
    #     entries = client.get_time_entries(datetime.now(pytz.UTC) - timedelta(days=30), datetime.now(pytz.UTC))
    #     entries = client.format_entries(entries)
    #     # Display entries
    #     print(f"\nFound {len(entries)} time entries:")
    #     for i, entry in enumerate(entries):
    #         date = entry["start_time"].strftime("%Y-%m-%d")
    #         print(f"{i+1}. {date}: {entry['activity_name']} - {entry['duration_hours']} hours")
    #         if entry["note"]:
    #             print(f"   Note: {entry['note']}")
            
    #     # Calculate total time per activity
    #     activity_totals = {}
    #     for entry in entries:
    #         activity = entry["activity_name"]
    #         if activity not in activity_totals:
    #             activity_totals[activity] = 0
    #         activity_totals[activity] += entry["duration_hours"]
        
    #     # Print summary
    #     print("\nSummary by activity:")
    #     for activity, hours in activity_totals.items():
    #         print(f"- {activity}: {hours:.2f} hours")
        
    #     print(f"\nTotal hours tracked: {sum(activity_totals.values()):.2f}")
    #     for entry in entries:
    #         if entry['activity_name'] == "Studio Waltz":
    #             print(entry)
    #         else:
    #             pass
    # except Exception as e:
    #     print(f"Error: {str(e)}")