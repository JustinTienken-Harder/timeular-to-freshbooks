import pandas as pd
from datetime import datetime, timedelta
import json

def load_time_entries_from_excel(file_path):
    """
    Load time entries from an Excel/CSV file with specific fields:
    - TimeEntryID
    - StartDate
    - Duration
    - Billable
    - ActivityID
    - Activity
    - FolderId
    - Folder
    - service
    - Note
    """
    # Detect file type and load
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported file format. Please use .xlsx, .xls, or .csv")
    
    # Transform data to match Timeular format
    time_entries = []
    
    for _, row in df.iterrows():
        # Parse start date
        start_date = pd.to_datetime(row['StartDate'])
        
        # Parse duration (assuming it's in seconds)
        duration_seconds = float(row['Duration'])
        
        # Calculate end time
        end_date = start_date + timedelta(seconds=duration_seconds)
        
        # Parse billable status
        billable = False
        billable_val = row['Billable']
        if isinstance(billable_val, bool):
            billable = billable_val
        elif isinstance(billable_val, str):
            billable = billable_val.lower() in ['yes', 'true', 'y', '1', 'billable']
        elif isinstance(billable_val, (int, float)):
            billable = bool(billable_val)
        
        # Create entry object
        entry = {
            'id': str(row['TimeEntryID']),
            'activityId': str(row['ActivityID']),
            'activityName': row['Activity'],
            'startedAt': start_date.isoformat(),
            'stoppedAt': end_date.isoformat(),
            'duration': duration_seconds,  # Duration in seconds
            'billable': billable,
            'note': str(row['Note']) if not pd.isna(row['Note']) else "",
            'folder': {
                'id': str(row['FolderId']),
                'name': row['Folder']
            },
            'service': row['service'] if not pd.isna(row['service']) else ""
        }
        
        time_entries.append(entry)
    
    return time_entries

# Example usage
if __name__ == "__main__":
    file_path = "test.xlsx"  # or "time_tracking.csv"
    time_entries = load_time_entries_from_excel(file_path)
    
    
    # Print pretty JSON
    print(json.dumps(time_entries, indent=4, default=str))