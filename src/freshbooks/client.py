import json
import requests
from datetime import datetime
import logging

class FreshbooksClient:
    def __init__(self, api_token, business_id):
        self.api_key = api_token
        self.business_id = business_id
        self.base_url = "https://api.freshbooks.com"

    def create_invoice(self, invoice_data):
        # Logic to create an invoice in Freshbooks
        pass

    def get_client_id_from_name(self, name):
        """
        Get client ID from a name.
        
        Args:
            name: String with client name to search for
            
        Returns:
            Client ID if found, None otherwise
        """
        client = self.find_client_by_name(name)
        if client:
            return client.get('id')
        return None

    def create_time_entry(self, time_entry):
        """
        Create a time entry in Freshbooks based on data from CSV/Excel.
        
        Args:
            time_entry: Dict with the following expected fields (all lowercase):
                - duration: duration in hours (will be converted to seconds)
                - startdate: start date/time
                - note: description of the work
                - billable: whether the entry is billable
                - service: Optional service identifier
                - folderid: Can be used to map to project_id
                - activity: Activity name which can be used to find client
                
        Returns:
            Response from Freshbooks API or None if the request failed
        """
        endpoint = f"{self.base_url}/timetracking/business/{self.business_id}/time_entries"
        
        # Extract required fields from time_entry
        try:
            # Parse the start date from string to datetime if needed
            if isinstance(time_entry['startdate'], str):
                start_date = datetime.fromisoformat(time_entry['startdate'].replace('Z', '+00:00'))
            else:
                start_date = time_entry['startdate']
            
            # Format start date in ISO format for Freshbooks
            started_at = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            # Convert duration from hours to seconds
            hours = float(time_entry['duration'])
            seconds = int(hours * 3600)  # Convert hours to seconds
            
            # Create the request payload
            freshbooks_entry = {
                "time_entry": {
                    "is_logged": True,
                    "duration": seconds,
                    "note": time_entry.get('note', ''),
                    "started_at": started_at,
                    "billable": bool(time_entry.get('billable', False))
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
                
            # Map project ID from folderid if available
            if 'folderid' in time_entry:
                freshbooks_entry["time_entry"]["project_id"] = str(time_entry['folderid'])
                
            # Map service ID if available
            if 'service' in time_entry and time_entry['service']:
                freshbooks_entry["time_entry"]["service_id"] = str(time_entry['service'])
            
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
            List of successful entries and failed entries
        """
        successful = []
        failed = []
        
        for entry in time_entries:
            result = self.create_time_entry(entry)
            if result:
                successful.append({
                    "original": entry,
                    "response": result
                })
            else:
                failed.append(entry)
                
        return {
            "successful": successful,
            "failed": failed,
            "stats": {
                "total": len(time_entries),
                "success": len(successful),
                "failure": len(failed)
            }
        }

    def get_clients(self):
        """
        Retrieve all clients from Freshbooks API and store them in self.clients.
        
        Returns:
            Dict containing all clients if successful, None otherwise
        """
        endpoint = f"{self.base_url}/accounting/account/{self.business_id}/users/clients"
        
        try:
            clients = []
            page = 1
            more_pages = True
            
            # Set headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Api-Version": "alpha"
            }
            
            # Paginate through all clients
            while more_pages:
                params = {
                    "page": page,
                    "per_page": 100  # Maximum allowed by API
                }
                
                response = requests.get(endpoint, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Add clients from current page
                    if 'response' in data and 'result' in data['response'] and 'clients' in data['response']['result']:
                        page_clients = data['response']['result']['clients']
                        clients.extend(page_clients)
                        
                        # Check if there are more pages
                        current_page = data['response']['result']['page']
                        total_pages = data['response']['result']['pages']
                        
                        if current_page >= total_pages:
                            more_pages = False
                        else:
                            page += 1
                    else:
                        logging.error(f"Unexpected response format: {data}")
                        more_pages = False
                else:
                    logging.error(f"Failed to retrieve clients. Status code: {response.status_code}")
                    logging.error(f"Response: {response.text}")
                    more_pages = False
            
            # Create a client lookup by both ID and name
            self.clients = {
                "by_id": {},
                "by_name": {},
                "all": clients
            }
            
            # Populate lookups
            for client in clients:
                client_id = client.get('id')
                if client_id:
                    self.clients["by_id"][client_id] = client
                
                # Create name lookup using full name and organization
                full_name = f"{client.get('fname', '')} {client.get('lname', '')}".strip()
                organization = client.get('organization', '')
                
                if full_name:
                    self.clients["by_name"][full_name.lower()] = client
                
                if organization:
                    self.clients["by_name"][organization.lower()] = client
                
                # Also add combined name and organization for more precise matching
                if full_name and organization:
                    combined = f"{full_name} - {organization}"
                    self.clients["by_name"][combined.lower()] = client
            
            return self.clients
        
        except Exception as e:
            logging.error(f"Error retrieving clients: {str(e)}")
            return None

    def find_client_by_name(self, name):
        """
        Find a client by name or organization.
        
        Args:
            name: String with client name or organization to search for
        
        Returns:
            Client dict if found, None otherwise
        """
        if not hasattr(self, 'clients'):
            self.get_clients()
        
        # Try exact match first
        name_lower = name.lower()
        if name_lower in self.clients["by_name"]:
            return self.clients["by_name"][name_lower]
        
        # Try partial match if exact match fails
        client_of_best_match = self.partial_match_client(name)
        if client_of_best_match is not None:
            return client_of_best_match
        
        return None

    def partial_match_client(self, name):
        """
        Find a client by partial name or organization.
        
        Args:
            name: String with partial client name or organization to search for
        
        Returns:
            List of matching clients
        """
         # If no exact match, try more advanced matching
    
        # 1. Tokenize the input name
        input_tokens = set(name.replace('-', ' ').replace('/', ' ').split())
        
        # Remove common words that don't help with matching
        stop_words = {'and', 'the', 'llc', 'inc', 'ltd', 'corp', 'corporation', 'company', 'co'}
        input_tokens = {token for token in input_tokens if token not in stop_words}
        
        best_match = None
        best_score = 0
        
        for key, client in self.clients["by_name"].items():
            # Tokenize the client name
            client_tokens = set(key.lower().replace('-', ' ').replace('/', ' ').split())
            client_tokens = {token for token in client_tokens if token not in stop_words}
            
            # Calculate match score using various methods
            
            # Method 1: Overlap coefficient (works well for different length sets)
            if len(input_tokens) == 0 or len(client_tokens) == 0:
                continue
                
            overlap = len(input_tokens.intersection(client_tokens))
            overlap_score = overlap / min(len(input_tokens), len(client_tokens))
            
            # Method 2: Check for substring matches in first/last name and organization
            substring_score = 0
            
            full_name = f"{client.get('fname', '').lower()} {client.get('lname', '').lower()}".strip()
            organization = client.get('organization', '').lower()
            
            # Check if any input token is in the name or organization
            for token in input_tokens:
                if token in full_name:
                    substring_score += 0.5
                if token in organization:
                    substring_score += 0.5
                    
            # Normalize substring score to be between 0 and 1
            substring_score = min(1.0, substring_score / len(input_tokens)) if input_tokens else 0
            
            # Method 3: Check for initial matches (e.g. "JD" matches "John Doe")
            initial_score = 0
            if client.get('fname') and client.get('lname'):
                initials = (client.get('fname', '')[0] + client.get('lname', '')[0]).lower()
                for token in input_tokens:
                    if len(token) == 2 and token.lower() == initials:
                        initial_score = 0.8
            
            # Calculate combined score with weights
            combined_score = (overlap_score * 0.6) + (substring_score * 0.3) + (initial_score * 0.1)
            
            # Special case: If one is completely contained in the other, boost the score
            if name in key.lower() or key.lower() in name:
                combined_score += 0.2
                
            # Keep track of the best match
            if combined_score > best_score:
                best_score = combined_score
                best_match = client
        
        # Return the match only if it's above a reasonable threshold
        if best_score >= 0.4:  # Threshold can be adjusted based on preference
            logging.info(f"Found fuzzy match for '{name}' with score {best_score:.2f}: {best_match.get('fname', '')} {best_match.get('lname', '')} - {best_match.get('organization', '')}")
            return best_match
        
        logging.warning(f"No match found for client name: {name}")
        return None

    def find_client_by_id(self, client_id):
        """
        Find a client by ID.
        
        Args:
            client_id: Client ID to search for
        
        Returns:
            Client dict if found, None otherwise
        """
        if not hasattr(self, 'clients'):
            self.get_clients()
        
        return self.clients["by_id"].get(client_id)

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
            
    def _get_identity_from_staff(self):
        """
        Alternative method to get identity ID from staff endpoint.
        
        Returns:
            Identity ID if successful, None otherwise
        """
        endpoint = f"{self.base_url}/accounting/account/{self.business_id}/users/staffs"
        
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
                
                # Check if we got staff data in expected format
                if ('response' in data and 'result' in data['response'] and 
                    'staff' in data['response']['result'] and 
                    len(data['response']['result']['staff']) > 0):
                    
                    # Assuming there's only one staff member or we want the first one
                    staff = data['response']['result']['staff'][0]
                    self.identity_id = staff.get('id')
                    
                    if self.identity_id:
                        logging.info(f"Found staff identity ID: {self.identity_id}")
                        return self.identity_id
                    else:
                        logging.error("Staff found but no ID available")
                else:
                    logging.error("Unexpected response format or no staff found")
                
                return None
            else:
                logging.error(f"Failed to retrieve staff data. Status code: {response.status_code}")
                return None
        
        except Exception as e:
            logging.error(f"Error retrieving staff identity ID: {str(e)}")
            return None

    def _get_identity_from_team_members(self):
        """
        Fallback method to get identity ID from team members endpoint.
        
        Returns:
            Identity ID if successful, None otherwise
        """
        endpoint = f"{self.base_url}/timetracking/business/{self.business_id}/team_members"
        
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
                
                # Assuming the first team member is the current user
                if 'team_members' in data and len(data['team_members']) > 0:
                    # Get the first team member's ID
                    self.identity_id = data['team_members'][0]['id']
                    logging.info(f"Found identity ID from team members: {self.identity_id}")
                    return self.identity_id
                else:
                    logging.error("No team members found in response")
                    return None
            else:
                logging.error(f"Failed to retrieve team members. Status code: {response.status_code}")
                logging.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error retrieving team members: {str(e)}")
            return None

    def export_client_mappings(self, timeular_activities, filename="client_mappings.csv"):
        """
        Export a CSV file showing the mappings between Timeular activities and Freshbooks clients.
        
        This is useful for showing how activity names from Timeular are matched to clients in Freshbooks,
        particularly when fuzzy matching is used.
        
        Args:
            timeular_activities: List of activity names from Timeular
            filename: Name of the CSV file to export (default: client_mappings.csv)
            
        Returns:
            Path to the exported CSV file
        """
        import csv
        import os
        from datetime import datetime
        
        # Make sure we have clients loaded
        if not hasattr(self, 'clients'):
            self.get_clients()
        
        # Prepare the data for CSV
        mappings = []
        for activity in timeular_activities:
            # Skip empty activity names
            if not activity:
                continue
                
            # Try to find a matching client
            client = self.find_client_by_name(activity)
            
            # Determine match type
            if client:
                name_lower = activity.lower()
                if name_lower in self.clients["by_name"]:
                    match_type = "Exact match"
                    score = "1.0"
                else:
                    match_type = "Fuzzy match"
                    # Try to recalculate the fuzzy match score
                    fuzzy_score = self._calculate_fuzzy_match_score(activity, client)
                    score = f"{fuzzy_score:.2f}"
            else:
                match_type = "No match"
                score = "0.0"
            
            mappings.append({
                'timeular_activity': activity,
                'freshbooks_client_name': f"{client.get('fname', '')} {client.get('lname', '')}" if client else "No match",
                'freshbooks_organization': client.get('organization', '') if client else "N/A",
                'freshbooks_client_id': client.get('id', '') if client else "N/A",
                'match_type': match_type,
                'score': score
            })
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = f"{os.path.splitext(filename)[0]}_{timestamp}{os.path.splitext(filename)[1]}"
        
        # Write to CSV
        try:
            with open(filename_with_timestamp, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timeular_activity', 'freshbooks_client_name', 'freshbooks_organization', 
                             'freshbooks_client_id', 'match_type', 'score']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for mapping in mappings:
                    writer.writerow(mapping)
            
            logging.info(f"Successfully exported client mappings to {filename_with_timestamp}")
            return filename_with_timestamp
        
        except Exception as e:
            logging.error(f"Error exporting client mappings: {str(e)}")
            return None

    def _calculate_fuzzy_match_score(self, name, client):
        """
        Calculate the fuzzy match score between a name and a client.
        This replicates the logic from partial_match_client for consistency.
        
        Args:
            name: String with client name to match
            client: Client dict to match against
            
        Returns:
            Fuzzy match score between 0 and 1
        """
        # Tokenize the input name
        input_tokens = set(name.lower().replace('-', ' ').replace('/', ' ').split())
        
        # Remove common words that don't help with matching
        stop_words = {'and', 'the', 'llc', 'inc', 'ltd', 'corp', 'corporation', 'company', 'co'}
        input_tokens = {token for token in input_tokens if token not in stop_words}
        
        # Generate the client name key like in partial_match_client
        full_name = f"{client.get('fname', '')} {client.get('lname', '')}".strip().lower()
        organization = client.get('organization', '').lower()
        
        # Tokenize the client name and organization
        client_tokens = set(full_name.replace('-', ' ').replace('/', ' ').split())
        if organization:
            client_tokens.update(organization.replace('-', ' ').replace('/', ' ').split())
        
        client_tokens = {token for token in client_tokens if token not in stop_words}
        
        # Calculate scores
        if len(input_tokens) == 0 or len(client_tokens) == 0:
            return 0.0
            
        # Overlap coefficient
        overlap = len(input_tokens.intersection(client_tokens))
        overlap_score = overlap / min(len(input_tokens), len(client_tokens))
        
        # Substring matches
        substring_score = 0
        for token in input_tokens:
            if token in full_name:
                substring_score += 0.5
            if token in organization:
                substring_score += 0.5
        
        substring_score = min(1.0, substring_score / len(input_tokens)) if input_tokens else 0
        
        # Initial matches
        initial_score = 0
        if client.get('fname') and client.get('lname'):
            initials = (client.get('fname', '')[0] + client.get('lname', '')[0]).lower()
            for token in input_tokens:
                if len(token) == 2 and token.lower() == initials:
                    initial_score = 0.8
        
        # Combined score
        combined_score = (overlap_score * 0.6) + (substring_score * 0.3) + (initial_score * 0.1)
        
        # Boost for complete containment
        if name.lower() in full_name or name.lower() in organization or full_name in name.lower() or organization in name.lower():
            combined_score += 0.2
        
        return min(1.0, combined_score)  # Ensure score doesn't exceed 1.0