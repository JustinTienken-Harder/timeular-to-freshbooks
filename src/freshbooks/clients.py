import requests
import logging

class ClientsMixin:
    """
    Mixin class for FreshbooksClient that handles client-related functionality.
    This separates the client-related code from the main client code.
    """
    
    def get_clients(self):
        """
        Retrieve all clients from Freshbooks API and store them in self.clients.
        
        Returns:
            Dict containing all clients if successful, None otherwise
        """
        endpoint = f"{self.base_url}/accounting/account/{self.account_id}/users/clients"
        
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
            Client dict if found, None otherwise
        """
        # Define a function to extract comparison text from a client
        def get_client_comparison_text(client, key):
            full_name = f"{client.get('fname', '')} {client.get('lname', '')}".strip()
            organization = client.get('organization', '')
            # Return the combination of all text fields
            return f"{full_name} {organization} {key}".strip()
        
        # Use the shared fuzzy matching function with client-specific settings
        client_stop_words = {'llc', 'inc', 'ltd', 'corp', 'corporation', 'company', 'co'}
        return self._fuzzy_match(
            name, 
            self.clients["by_name"], 
            get_client_comparison_text,
            min_threshold=0.4,
            custom_stop_words=client_stop_words
        )

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
            return filename_with_timestamp, mappings
        
        except Exception as e:
            logging.error(f"Error exporting client mappings: {str(e)}")
            return None, mappings