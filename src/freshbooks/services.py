import requests
import logging

class ServicesMixin:
    """
    Mixin class for FreshbooksClient that handles service-related functionality.
    This separates the service-related code from the main client code.
    """
    
    def get_services(self):
        """
        Retrieve all services from Freshbooks API and store them in self.services.
        
        Returns:
            Dict containing all services if successful, None otherwise
        """
        endpoint = f"{self.base_url}/comments/business/{self.business_id}/services"
        
        try:
            # Set headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Api-Version": "alpha"
            }
            
            # Make the request
            response = requests.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got services data in expected format
                if 'services' in data:
                    services = data['services']
                    
                    # Create a service lookup by both ID and name
                    self.services = {
                        "by_id": {},
                        "by_name": {},
                        "all": services
                    }
                    
                    # Populate lookups
                    for service in services:
                        service_id = service.get('id')
                        service_name = service.get('name')
                        
                        if service_id:
                            self.services["by_id"][service_id] = service
                        
                        if service_name:
                            self.services["by_name"][service_name.lower()] = service
                    
                    logging.info(f"Retrieved {len(services)} services from Freshbooks")
                    return self.services
                else:
                    logging.error(f"Unexpected response format: {data}")
                    return None
            else:
                logging.error(f"Failed to retrieve services. Status code: {response.status_code}")
                logging.error(f"Response: {response.text}")
                return None
        
        except Exception as e:
            logging.error(f"Error retrieving services: {str(e)}")
            return None

    def find_service_by_tag(self, tag):
        """
        Find a service by tag name (fuzzy matching).
        
        Args:
            tag: String with tag name to search for
        
        Returns:
            Service dict if found, None otherwise
        """
        if not hasattr(self, 'services'):
            self.get_services()
        
        # Normalize tag
        tag_lower = tag.lower().strip()
        
        # Try exact match first
        if tag_lower in self.services["by_name"]:
            return self.services["by_name"][tag_lower]
        
        # Try fuzzy match if exact match fails
        service_match = self._partial_match_service(tag_lower)
        if service_match:
            return service_match
        
        return None

    def get_service_id_from_tag(self, tag):
        """
        Get service ID from a tag name.
        
        Args:
            tag: String with tag name to search for
        
        Returns:
            Service ID if found, None otherwise
        """
        service = self.find_service_by_tag(tag)
        if service:
            return service.get('id')
        return None
        
    def _partial_match_service(self, tag):
        """
        Find a service by partial name (fuzzy matching).
        
        Args:
            tag: String with partial service name to search for
        
        Returns:
            Service dict if found, None otherwise
        """
        # Define a function to extract comparison text from a service
        def get_service_comparison_text(service, key):
            # For services, the name is the primary field
            return f"{service.get('name', '')} {key}".strip()
        
        # Use the shared fuzzy matching function with service-specific settings
        service_stop_words = {'service', 'services', 'consulting', 'time', 'hours', 'work'}
        return self._fuzzy_match(
            tag, 
            self.services["by_name"],
            get_service_comparison_text,
            min_threshold=0.35,
            custom_stop_words=service_stop_words
        )
        
    def _calculate_service_match_score(self, tag, service):
        """
        Calculate the fuzzy match score between a tag and a service.
        
        Args:
            tag: String with tag to match
            service: Service dict to match against
            
        Returns:
            Fuzzy match score between 0 and 1
        """
        # Get service comparison text
        def get_service_comparison_text(service, key):
            # For services, the name is the primary field
            return f"{service.get('name', '')} {key}".strip()
        
        # Tokenize the input tag
        input_tokens = set(tag.lower().replace('-', ' ').replace('/', ' ').split())
        
        # Remove common words
        stop_words = {'and', 'the', 'of', 'in', 'for', 'to', 'with', 'by', 'at', 'from',
                      'service', 'services', 'consulting', 'time', 'hours', 'work'}
        input_tokens = {token for token in input_tokens if token not in stop_words and len(token) > 1}
        
        # Get comparison text
        comparison_text = get_service_comparison_text(service, service.get('name', ''))
        
        # Tokenize the comparison text
        target_tokens = set(comparison_text.lower().replace('-', ' ').replace('/', ' ').split())
        target_tokens = {token for token in target_tokens if token not in stop_words and len(token) > 1}
        
        # Skip if either token set is empty after filtering
        if not input_tokens or not target_tokens:
            return 0.0
        
        # Calculate scores
        # Overlap coefficient
        overlap = len(input_tokens.intersection(target_tokens))
        overlap_score = overlap / min(len(input_tokens), len(target_tokens))
        
        # Substring matches
        substring_score = 0
        for token in input_tokens:
            if token in comparison_text.lower():
                substring_score += 0.5
        
        substring_score = min(1.0, substring_score / len(input_tokens)) if input_tokens else 0
        
        # Containment check
        containment_score = 0
        if tag.lower() in comparison_text.lower() or comparison_text.lower() in tag.lower():
            containment_score = 0.8
        
        # Combined score with weights
        combined_score = (overlap_score * 0.6) + (substring_score * 0.3) + (containment_score * 0.1)
        
        return min(1.0, combined_score)  # Ensure score doesn't exceed 1.0
        
    def _extract_service_info(self, time_entry):
        """
        Extract service information from a time entry, including fuzzy match details.
        Used for building fuzzy match reports.
        
        Args:
            time_entry: Dict with time entry data
        
        Returns:
            Dict with service match information or None
        """
        # Check if this is Timeular API format
        if 'tags' in time_entry and isinstance(time_entry['tags'], list) and time_entry['tags'] and isinstance(time_entry['tags'][0], dict):
            # Process tags from Timeular API
            tag_labels = []
            for tag in time_entry['tags']:
                if 'label' in tag and tag['label']:
                    tag_labels.append(tag['label'])
                    
            # Try to match each tag
            for label in tag_labels:
                service = self.find_service_by_tag(label)
                if service:
                    # Check match type
                    if label.lower() in self.services["by_name"]:
                        match_type = "exact"
                        score = 1.0
                    else:
                        match_type = "fuzzy"
                        score = self._calculate_service_match_score(label, service)
                        
                        # Return fuzzy match details
                        if match_type == "fuzzy" and score < 1.0:
                            return {
                                "input": label,
                                "field": "tags[].label",
                                "matched_to": service.get('name', ''),
                                "service_id": service.get('id', ''),
                                "billable": service.get('billable', False),
                                "score": score,
                                "match_type": match_type
                            }
            return None
            
        # Process CSV format
        # Check different possible field names for tags
        tag_fields = ['tags', 'tag', 'servicetag', 'service_tag', 'service']
        
        # Try to find tags in any of the fields
        tags = None
        tag_field_used = None
        
        for field in tag_fields:
            if field in time_entry and time_entry[field]:
                tags = time_entry[field]
                tag_field_used = field
                break
        
        if not tags:
            return None
        
        # Process the tag(s)
        tag_list = []
        
        # If tags is a string, try to parse it as a list
        if isinstance(tags, str):
            # Common formats: comma-separated, semicolon-separated, or space-separated
            if ',' in tags:
                tag_list = [t.strip() for t in tags.split(',')]
            elif ';' in tags:
                tag_list = [t.strip() for t in tags.split(';')]
            else:
                # Assume space-separated or single tag
                tag_list = [tags.strip()]
        else:
            # If it's already a list or other iterable
            try:
                tag_list = list(tags)
            except:
                tag_list = [str(tags)]
        
        # Try to match each tag to a service
        for tag in tag_list:
            service = self.find_service_by_tag(tag)
            
            if service:
                # Determine if it was an exact or fuzzy match
                tag_lower = tag.lower()
                if tag_lower in self.services["by_name"]:
                    match_type = "exact"
                    score = 1.0
                else:
                    match_type = "fuzzy"
                    score = self._calculate_service_match_score(tag, service)
                    
                    # Return fuzzy match information
                    if match_type == "fuzzy" and score < 1.0:
                        return {
                            "input": tag,
                            "field": tag_field_used,
                            "matched_to": service.get('name', ''),
                            "service_id": service.get('id', ''),
                            "billable": service.get('billable', False),
                            "score": score,
                            "match_type": match_type
                        }
        
        return None
    
    def extract_service_from_time_entry(self, time_entry):
        """
        Extract and match service ID from a time entry.
        This is a dispatcher that calls the appropriate method based on the data format.
        
        Args:
            time_entry: Dict with time entry data
    
        Returns:
            Service ID if found and matched, None otherwise
        """
        # Check if this is Timeular API format (has tags array of objects)
        if 'tags' in time_entry and isinstance(time_entry['tags'], list) and time_entry['tags'] and isinstance(time_entry['tags'][0], dict):
            return self.extract_service_from_timeular_api(time_entry)
    
        # Otherwise assume CSV/Excel format
        return self.extract_service_from_csv(time_entry)

    def extract_service_from_timeular_api(self, time_entry):
        """
        Extract service ID from a Timeular API time entry.
        Timeular API entries have tags as an array of objects.
    
        Args:
            time_entry: Dict with Timeular API time entry data
    
        Returns:
            Service ID if found, None otherwise
        """
        if 'tags' not in time_entry or not time_entry['tags']:
            return None
    
        # Collect all tag labels
        tag_labels = []
        for tag in time_entry['tags']:
            if 'label' in tag and tag['label']:
                tag_labels.append(tag['label'])
    
        # Try to match each tag to a service
        for label in tag_labels:
            service_id = self.get_service_id_from_tag(label)
            if service_id:
                logging.info(f"Matched Timeular tag '{label}' to service ID: {service_id}")
                return service_id
    
        return None

    def extract_service_from_csv(self, time_entry):
        """
        Extract service ID from a CSV/Excel time entry.
        CSV entries have tags as strings in various possible fields.
    
        Args:
            time_entry: Dict with CSV time entry data
    
        Returns:
            Service ID if found, None otherwise
        """
        # Check different possible field names for tags
        tag_fields = ['tags', 'tag', 'servicetag', 'service_tag', 'service']
    
        # Try to find tags in any of the fields
        tags = None
        for field in tag_fields:
            if field in time_entry and time_entry[field]:
                tags = time_entry[field]
                break
    
        if not tags:
            return None
    
        # If tags is a string, try to parse it as a list
        if isinstance(tags, str):
            # Common formats: comma-separated, semicolon-separated, or space-separated
            if ',' in tags:
                tags_list = [t.strip() for t in tags.split(',')]
            elif ';' in tags:
                tags_list = [t.strip() for t in tags.split(';')]
            else:
                # Assume space-separated or single tag
                tags_list = [tags.strip()]
        else:
            # If it's already a list or other iterable
            try:
                tags_list = list(tags)
            except:
                tags_list = [str(tags)]
    
        # Try to match each tag to a service
        for tag in tags_list:
            service_id = self.get_service_id_from_tag(tag)
            if service_id:
                logging.info(f"Matched CSV tag '{tag}' to service ID: {service_id}")
                return service_id
    
        return None

    def export_service_mappings(self, tags, filename="service_mappings.csv"):
        """
        Export a CSV file showing the mappings between tags and Freshbooks services.
        
        Args:
            tags: List of tag strings
            filename: Name of the CSV file to export (default: service_mappings.csv)
            
        Returns:
            Path to the exported CSV file and mappings data
        """
        import csv
        import os
        from datetime import datetime
        
        # Make sure we have services loaded
        if not hasattr(self, 'services'):
            self.get_services()
        
        # Prepare the data for CSV
        mappings = []
        for tag in tags:
            # Skip empty tags
            if not tag:
                continue
                
            # Try to find a matching service
            service = self.find_service_by_tag(tag)
            
            # Determine match type
            if service:
                tag_lower = tag.lower()
                if tag_lower in self.services["by_name"]:
                    match_type = "Exact match"
                    score = "1.0"
                else:
                    match_type = "Fuzzy match"
                    fuzzy_score = self._calculate_service_match_score(tag, service)
                    score = f"{fuzzy_score:.2f}"
            else:
                match_type = "No match"
                score = "0.0"
            
            mappings.append({
                'timeular_tag': tag,
                'freshbooks_service_name': service.get('name', '') if service else "No match",
                'freshbooks_service_id': service.get('id', '') if service else "N/A",
                'billable': service.get('billable', False) if service else "N/A",
                'match_type': match_type,
                'score': score
            })
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = f"{os.path.splitext(filename)[0]}_{timestamp}{os.path.splitext(filename)[1]}"
        
        # Write to CSV
        try:
            with open(filename_with_timestamp, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timeular_tag', 'freshbooks_service_name', 'freshbooks_service_id', 
                             'billable', 'match_type', 'score']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for mapping in mappings:
                    writer.writerow(mapping)
            
            logging.info(f"Successfully exported service mappings to {filename_with_timestamp}")
            return filename_with_timestamp, mappings
        
        except Exception as e:
            logging.error(f"Error exporting service mappings: {str(e)}")
            return None, mappings