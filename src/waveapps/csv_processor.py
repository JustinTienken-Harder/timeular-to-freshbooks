"""
CSV Processor for Timeular timesheets

Handles parsing, grouping, and aggregation of Timeular CSV data for WaveApp invoice generation.
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)


class TimeularCSVProcessor:
    """Process Timeular CSV exports for WaveApp invoice generation"""
    
    def __init__(self, file_path: str):
        """
        Initialize processor with a CSV file
        
        Args:
            file_path: Path to Timeular CSV export file
        """
        self.file_path = file_path
        self.df: pd.DataFrame = None
        self.processed_data: Dict[str, Any] = {}
        
    def load_csv(self) -> pd.DataFrame:
        """
        Load and parse the CSV file
        
        Returns:
            Parsed DataFrame
        """
        try:
            # Load CSV
            self.df = pd.read_csv(self.file_path)
            
            # Validate required columns
            required_columns = ['Activity', 'Duration', 'Billable', 'Tags', 'Note']
            missing_columns = [col for col in required_columns if col not in self.df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            logger.info(f"Loaded {len(self.df)} entries from CSV")
            return self.df
            
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            raise
    
    def parse_duration(self, duration_str: str) -> float:
        """
        Parse duration string (HH:MM:SS) to hours
        
        Args:
            duration_str: Duration in HH:MM:SS format
            
        Returns:
            Duration in hours (float)
        """
        try:
            # Parse HH:MM:SS format
            parts = duration_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours + (minutes / 60) + (seconds / 3600)
            else:
                logger.warning(f"Unexpected duration format: {duration_str}")
                return 0.0
        except Exception as e:
            logger.error(f"Failed to parse duration '{duration_str}': {e}")
            return 0.0
    
    def filter_billable(self) -> 'TimeularCSVProcessor':
        """
        Filter to keep only billable entries
        
        Returns:
            Self for method chaining
        """
        if self.df is None:
            raise ValueError("CSV not loaded. Call load_csv() first.")
        
        # Convert Billable column to boolean
        self.df['IsBillable'] = self.df['Billable'].str.lower().isin(['yes', 'true', 'y', '1'])
        
        original_count = len(self.df)
        self.df = self.df[self.df['IsBillable']].copy()
        filtered_count = len(self.df)
        
        logger.info(f"Filtered to {filtered_count} billable entries (removed {original_count - filtered_count})")
        return self
    
    def parse_durations(self) -> 'TimeularCSVProcessor':
        """
        Parse all duration strings to hours
        
        Returns:
            Self for method chaining
        """
        if self.df is None:
            raise ValueError("CSV not loaded. Call load_csv() first.")
        
        self.df['Hours'] = self.df['Duration'].apply(self.parse_duration)
        logger.info(f"Parsed durations, total hours: {self.df['Hours'].sum():.2f}")
        return self
    
    def aggregate_data(self) -> Dict[str, Any]:
        """
        Group and aggregate data by Activity (client) and Tags (service)
        Aggregates:
        - Sum hours per service within each client
        - Concatenate all notes for each service
        
        Returns:
            Dictionary structure:
            {
                "Activity Name": {
                    "total_hours": float,
                    "entries_by_tag": {
                        "tag_name": {
                            "hours": float,
                            "notes": str (concatenated)
                        }
                    }
                }
            }
        """
        if self.df is None or 'Hours' not in self.df.columns:
            raise ValueError("CSV not processed. Call load_csv(), filter_billable(), and parse_durations() first.")
        
        # Handle missing Tags - replace NaN with empty string
        self.df['Tags'] = self.df['Tags'].fillna('')
        self.df['Note'] = self.df['Note'].fillna('')
        
        # Ensure StartDate is available for formatting notes
        if 'StartDate' not in self.df.columns:
            logger.warning("StartDate column not found, notes will not include dates")
        
        result = {}
        
        # Group by Activity (client)
        for activity, activity_group in self.df.groupby('Activity'):
            activity_data = {
                'total_hours': 0.0,
                'entries_by_tag': {}
            }
            
            # Group by Tags within each Activity
            for tag, tag_group in activity_group.groupby('Tags'):
                # Sum hours
                total_hours = tag_group['Hours'].sum()
                
                # Aggregate notes with dates (filter out empty strings)
                notes_list = []
                for _, row in tag_group.iterrows():
                    note = str(row['Note']).strip()
                    if note:
                        # Format: Date: Note
                        if 'StartDate' in row and pd.notna(row['StartDate']):
                            date_str = pd.to_datetime(row['StartDate']).strftime('%Y-%m-%d')
                            formatted_note = f"{date_str}: {note}"
                        else:
                            formatted_note = note
                        notes_list.append(formatted_note)
                
                aggregated_notes = '\n'.join(notes_list) if notes_list else ''
                
                activity_data['entries_by_tag'][tag] = {
                    'hours': round(total_hours, 2),
                    'notes': aggregated_notes
                }
                
                activity_data['total_hours'] += total_hours
            
            activity_data['total_hours'] = round(activity_data['total_hours'], 2)
            result[activity] = activity_data
        
        self.processed_data = result
        logger.info(f"Aggregated data for {len(result)} activities")
        
        return result
    
    def get_unique_activities(self) -> List[str]:
        """
        Get list of unique activities (clients) from processed data
        
        Returns:
            List of activity names
        """
        if not self.processed_data:
            raise ValueError("Data not processed. Call aggregate_data() first.")
        
        return list(self.processed_data.keys())
    
    def get_unique_tags(self) -> List[str]:
        """
        Get list of unique tags (services) across all activities
        
        Returns:
            List of unique tag names
        """
        if not self.processed_data:
            raise ValueError("Data not processed. Call aggregate_data() first.")
        
        tags = set()
        for activity_data in self.processed_data.values():
            tags.update(activity_data['entries_by_tag'].keys())
        
        return sorted(list(tags))
    
    def process(self) -> Dict[str, Any]:
        """
        Execute full processing pipeline
        
        Returns:
            Processed and aggregated data
        """
        self.load_csv()
        self.filter_billable()
        self.parse_durations()
        return self.aggregate_data()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of processed data
        
        Returns:
            Summary statistics
        """
        if not self.processed_data:
            return {}
        
        total_hours = sum(data['total_hours'] for data in self.processed_data.values())
        total_activities = len(self.processed_data)
        total_tags = len(self.get_unique_tags())
        
        return {
            'total_activities': total_activities,
            'total_tags': total_tags,
            'total_hours': round(total_hours, 2),
            'activities': list(self.processed_data.keys())
        }
