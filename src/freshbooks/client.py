import json
import requests
from datetime import datetime, timezone
import logging

from freshbooks.services import ServicesMixin
from freshbooks.clients import ClientsMixin
from freshbooks.utils import FuzzyMatchingMixin

class FreshbooksClient(ServicesMixin, ClientsMixin, FuzzyMatchingMixin):
    def __init__(self, api_token, business_id=None):
        """
        Initialize FreshbooksClient with API token and optional business ID.
        If business_id is not provided, it will be loaded from the /users/me endpoint.
        
        Args:
            api_token: FreshBooks API token
            business_id: Optional FreshBooks business ID
        """
        self.api_key = api_token
        self.business_id = business_id
        self.base_url = "https://api.freshbooks.com"
        self.dont_send = True 
    
        # If business_id not provided, load it
        if not self.business_id:
            business_info = self.get_business_info()
            if not business_info:
                logging.warning("Could not automatically determine business ID. Some functionality may not work.")
        
        # Initialize data we need
        self.get_clients()
        self.get_services()
        
    def create_invoice(self, invoice_data):
        # Logic to create an invoice in Freshbooks
        pass

    def create_time_entry(self, time_entry):
        """
        Create a time entry in Freshbooks based on data from CSV/Excel.
        
        Args:
            time_entry: Dict with the following expected fields (all lowercase):
                - duration: duration in hours (will be converted to seconds)
                - startdate: start date/time
                - note: description of the work
                - billable: whether the entry is billable
                - tags/service: Optional service identifier or tags
                - folderid: Can be used to map to project_id
                - activity: Activity name which can be used to find client
                
        Returns:
            Response from Freshbooks API or None if the request failed
        """
        endpoint = f"{self.base_url}/timetracking/business/{self.business_id}/time_entries"
        
        # Extract required fields from time_entry
        # In the FreshbooksClient.create_time_entry method, update this part:
        try:
            # Convert duration from hours to seconds
            if isinstance(time_entry['duration'], str) and ':' in time_entry['duration']:
                # Parse duration in format 'HH:MM:SS'
                hours_parts = time_entry['duration'].split(':')
                hours = int(hours_parts[0])  
                minutes = int(hours_parts[1]) if len(hours_parts) > 1 else 0
                seconds = int(hours_parts[2]) if len(hours_parts) > 2 else 0
                
                # Calculate total seconds
                seconds = (hours * 3600) + (minutes * 60) + seconds
            else:
                # Try direct conversion from numeric hours
                hours = float(time_entry['duration'])
                seconds = int(hours * 3600)  # Convert hours to seconds
            
            # Create the request payload
            if 'startdate' in time_entry:
                started_at = time_entry['startdate']
                
                # If we have separate date and time fields, combine them
                if 'starttime' in time_entry and time_entry['starttime']:
                    # Make sure it's properly formatted for ISO 8601
                    if isinstance(started_at, str) and isinstance(time_entry['starttime'], str):
                        started_at = f"{started_at.rstrip('Z')}T{time_entry['starttime']}Z"
                
                # Ensure we have the 'Z' UTC timezone indicator if it's just a date
                elif isinstance(started_at, str) and 'T' not in started_at and 'Z' not in started_at:
                    started_at = f"{started_at}T00:00:00Z"
                    
                # If it already has a T but no Z, add Z
                elif isinstance(started_at, str) and 'T' in started_at and 'Z' not in started_at:
                    started_at = f"{started_at}Z"
                    
            else:
                # Use current time in UTC
                started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            # Better handling of billable flag
            billable = False  # Default to False
            if 'billable' in time_entry:
                if isinstance(time_entry['billable'], str):
                    # Only these specific string values should be considered True
                    billable = time_entry['billable'].lower().strip() in ('yes', 'true', '1', 'y')
                else:
                    # For non-string values, use Python's boolean conversion
                    billable = bool(time_entry['billable'])

            # Then update your time entry creation dictionary
            freshbooks_entry = {
                "time_entry": {
                    "is_logged": True,
                    "duration": seconds,
                    "note": time_entry.get('note', ''),
                    "started_at": started_at,
                    "billable": billable  # Use the properly calculated billable value
                }
            }
                            
            # Add client_id by looking up the client name from activityName or activity
            client_name = None
            if 'activityname' in time_entry and time_entry['activityname']:
                client_name = time_entry['activityname']
            elif 'activity' in time_entry and time_entry['activity']:
                client_name = time_entry['activity']
                
            if client_name:
                client_id = self.get_client_id_from_name(client_name)
                if client_id:
                    freshbooks_entry["time_entry"]["client_id"] = str(client_id)
                    logging.info(f"Matched client name '{client_name}' to client ID: {client_id}")
            
            # Add optional fields if they exist in the input
            # Map client ID if explicitly provided
            if 'client_id' in time_entry:
                freshbooks_entry["time_entry"]["client_id"] = str(time_entry['client_id'])
            # Try to match service from tags if available
            service_id = self.extract_service_from_time_entry(time_entry)
            if service_id:
                freshbooks_entry["time_entry"]["service_id"] = str(service_id)
                logging.info(f"Matched service tag to service ID: {service_id}")
            # Map service ID if explicitly provided as 'service'
            elif 'service' in time_entry and time_entry['service']:
                # Check if it's a direct ID or needs to be looked up
                if isinstance(time_entry['service'], (int, str)) and str(time_entry['service']).isdigit():
                    # It's already an ID
                    freshbooks_entry["time_entry"]["service_id"] = str(time_entry['service'])
                else:
                    # Try to look it up by name
                    service_id = self.get_service_id_from_tag(time_entry['service'])
                    if service_id:
                        freshbooks_entry["time_entry"]["service_id"] = str(service_id)
                        logging.info(f"Matched service name '{time_entry['service']}' to service ID: {service_id}")
            
            # Ensure we have the identity ID (user ID)
            if not hasattr(self, 'identity_id'):
                self.get_identity_id()
            
            # Add identity_id to the request
            if hasattr(self, 'identity_id') and self.identity_id:
                freshbooks_entry["time_entry"]["identity_id"] = str(self.identity_id)
            elif 'identity_id' in time_entry:  # Fallback to provided identity_id if available
                freshbooks_entry["time_entry"]["identity_id"] = str(time_entry['identity_id'])
            
            # Set headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Api-Version": "alpha"
            }

            # Send the request
            if self.dont_send:
                logging.info("Would have sent the following time entry data:")
                logging.info(json.dumps(freshbooks_entry, indent=2))
                # Return a mock response with the same structure as a real one
                return {
                    "time_entry": {
                        "id": "mock-id",
                        "client_id": freshbooks_entry["time_entry"].get("client_id", ""),
                        "note": freshbooks_entry["time_entry"].get("note", "")
                    },
                    "fuzzy_matches": []  # Empty array to maintain structure
                }
            else:
                response = requests.post(endpoint, json=freshbooks_entry, headers=headers)
                        
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            else:
                logging.error(f"Failed to create time entry. Status code: {response.status_code}")
                logging.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error creating time entry: {str(e)}")
            logging.error(f"Time entry data: {time_entry}")
            return None
            
    def create_time_entries_batch(self, time_entries):
        """
        Create multiple time entries from a list.
        
        Args:
            time_entries: List of time entry dictionaries
            
        Returns:
            Dict containing successful entries, failed entries, and fuzzy match information
        """
        successful = []
        failed = []
        fuzzy_matches = {
            "clients": [],
            "services": []
        }
        
        # Make sure we have services loaded
        if not hasattr(self, 'services'):
            self.get_services()
        
        # Process each entry
        for entry in time_entries:
            # Track fuzzy matches for this entry
            fuzzy_info = {
                "client": None,
                "service": None
            }
            
            # Check for client fuzzy match
            client_name = None
            if 'activityname' in entry and entry['activityname']:
                client_name = entry['activityname']
            elif 'activity' in entry and entry['activity']:
                client_name = entry['activity']
                
            if client_name:
                client = self.find_client_by_name(client_name)
                
                if client:
                    # Determine if it was an exact or fuzzy match
                    name_lower = client_name.lower()
                    if name_lower in self.clients["by_name"]:
                        match_type = "exact"
                        score = 1.0
                    else:
                        match_type = "fuzzy"
                        score = self._calculate_fuzzy_match_score(client_name, client)
                        
                        # Add to fuzzy matches collection if not an exact match
                        if match_type == "fuzzy" and score < 1.0:
                            fuzzy_matches["clients"].append({
                                "input": client_name,
                                "matched_to": f"{client.get('fname', '')} {client.get('lname', '')}" if client else "No match",
                                "organization": client.get('organization', ''),
                                "client_id": client.get('id', ''),
                                "score": score
                            })
                            
                            # Store match info for this entry
                            fuzzy_info["client"] = {
                                "input": client_name,
                                "matched_to": f"{client.get('fname', '')} {client.get('lname', '')}" if client else "No match",
                                "client_id": client.get('id', ''),
                                "score": score
                            }
            
            # Check for service fuzzy match
            service_info = self._extract_service_info(entry)
            if service_info and service_info.get("match_type") == "fuzzy":
                fuzzy_matches["services"].append(service_info)
                fuzzy_info["service"] = service_info
            
            # Create the time entry
            result = self.create_time_entry(entry)
            
            if result:
                successful.append({
                    "original": entry,
                    "response": result,
                    "fuzzy_matches": fuzzy_info  # Include fuzzy match info in the successful entry
                })
            else:
                failed.append({
                    "entry": entry,
                    "fuzzy_matches": fuzzy_info  # Include fuzzy match info in the failed entry too
                })
        
        # Deduplicate fuzzy matches
        fuzzy_matches["clients"] = self._deduplicate_fuzzy_matches(fuzzy_matches["clients"], "input")
        fuzzy_matches["services"] = self._deduplicate_fuzzy_matches(fuzzy_matches["services"], "input")
        
        # Sort fuzzy matches by score (descending)
        fuzzy_matches["clients"].sort(key=lambda x: x["score"], reverse=True)
        fuzzy_matches["services"].sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "successful": successful,
            "failed": failed,
            "stats": {
                "total": len(time_entries),
                "success": len(successful),
                "failure": len(failed)
            },
            "fuzzy_matches": fuzzy_matches
        }

    def get_identity_id(self):
        """
        Retrieve the identity ID (user ID) from Freshbooks API and store it in self.identity_id.
        This method uses the /users/me endpoint to find the current user's ID.
        
        Returns:
            Identity ID if successful, None otherwise
        """
        endpoint = f"{self.base_url}/auth/api/v1/users/me"
        
        try:
            # Set headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Api-Version": "alpha"
            }
            
            response = requests.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got user data in expected format
                if 'response' in data and 'id' in data['response']:
                    self.identity_id = data['response']['id']
                    logging.info(f"Found user identity ID: {self.identity_id}")
                    
                    # Store additional user info if needed
                    self.user_info = {
                        'id': self.identity_id,
                        'name': f"{data['response'].get('first_name', '')} {data['response'].get('last_name', '')}",
                        'email': data['response'].get('email', '')
                    }
                    
                    # Also store business information for reference
                    if 'business_memberships' in data['response'] and data['response']['business_memberships']:
                        # Find the membership that matches our business ID
                        for membership in data['response']['business_memberships']:
                            if membership['business']['id'] == int(self.business_id):
                                self.business_info = membership['business']
                                break
                    
                    return self.identity_id
                else:
                    logging.error(f"Unexpected response format from /users/me: {data}")
                    # If we couldn't get the ID from /users/me, try the alternative methods
                    return self._get_identity_from_staff() or self._get_identity_from_team_members()
            else:
                logging.error(f"Failed to retrieve user data. Status code: {response.status_code}")
                logging.error(f"Response: {response.text}")
                
                # Try alternate endpoints if the first failed
                return self._get_identity_from_staff() or self._get_identity_from_team_members()
        
        except Exception as e:
            logging.error(f"Error retrieving identity ID: {str(e)}")
            return self._get_identity_from_staff() or self._get_identity_from_team_members()

    def get_business_info(self, refresh=False):
        """
        Retrieve business information including business ID and account ID.
        If already loaded, returns cached information unless refresh=True.
        
        Args:
            refresh: If True, force a refresh of the business information
        
        Returns:
            Dict containing business information if successful, None otherwise
        """
        if hasattr(self, 'business_info') and not refresh:
            return self.business_info
        
        endpoint = f"{self.base_url}/auth/api/v1/users/me"
        
        try:
            # Set headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Api-Version": "alpha"
            }
            
            response = requests.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got user data in expected format
                if ('response' in data and 'business_memberships' in data['response'] and 
                    len(data['response']['business_memberships']) > 0):
                    
                    # Initialize info container
                    self.business_info = {}
                    
                    # Find the membership that matches our business ID if specified
                    business_membership = None
                    
                    if self.business_id:
                        # Try to find the membership with the matching business ID
                        for membership in data['response']['business_memberships']:
                            if ('business' in membership and 
                                'id' in membership['business'] and 
                                membership['business']['id'] == int(self.business_id)):
                                business_membership = membership
                                break
                    
                    # If no matching membership found or no business ID specified, use the first one
                    if not business_membership and data['response']['business_memberships']:
                        business_membership = data['response']['business_memberships'][0]
                    
                    # Extract and store business information
                    if business_membership and 'business' in business_membership:
                        business = business_membership['business']
                        
                        # Update business_id if not set or if refreshing
                        if not self.business_id or refresh:
                            self.business_id = business.get('id')
                        
                        # Store all business info
                        self.business_info = {
                            'id': business.get('id'),
                            'account_id': business.get('account_id'),
                            'name': business.get('name'),
                            'business_uuid': business.get('business_uuid', ''),
                            'date_format': business.get('date_format', ''),
                            'role': business_membership.get('role', '')
                        }
                        self.account_id = self.business_info['account_id']
                        # Also store user identity ID if available
                        if 'id' in data['response']:
                            self.identity_id = data['response']['id']
                            self.business_info['identity_id'] = self.identity_id
                        
                        logging.info(f"Found business info: ID={self.business_info['id']}, Account ID={self.business_info['account_id']}")
                        return self.business_info
                    else:
                        logging.error("No valid business information found in response")
                else:
                    logging.error("No business memberships found in response")
                
                return None
            else:
                logging.error(f"Failed to retrieve business info. Status code: {response.status_code}")
                logging.error(f"Response: {response.text}")
                return None
        
        except Exception as e:
            logging.error(f"Error retrieving business information: {str(e)}")
            return None