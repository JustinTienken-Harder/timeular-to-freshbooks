import logging

class FuzzyMatchingMixin:
    """
    Mixin class with shared utility methods for fuzzy matching.
    """
    
    def _fuzzy_match(self, input_str, target_items, get_comparison_text_func, min_threshold=0.35, custom_stop_words=None):
        """
        General-purpose fuzzy matching function that can be used for both clients and services.
        
        Args:
            input_str: String to match
            target_items: Dictionary of items to match against (key->item)
            get_comparison_text_func: Function that extracts text to compare from each item
            min_threshold: Minimum score to consider a match (0-1)
            custom_stop_words: Additional stop words specific to this type of matching
            
        Returns:
            Best matching item if found, None otherwise
        """
        # Tokenize the input string
        input_tokens = set(input_str.lower().replace('-', ' ').replace('/', ' ').split())
        
        # Define common stop words
        stop_words = {'and', 'the', 'of', 'in', 'for', 'to', 'with', 'by', 'at', 'from'}
        
        # Add custom stop words if provided
        if custom_stop_words:
            stop_words.update(custom_stop_words)
        
        input_tokens = {token for token in input_tokens if token not in stop_words and len(token) > 1}
        
        best_match = None
        best_score = 0
        
        for key, item in target_items.items():
            # Get comparison text using the provided function
            comparison_text = get_comparison_text_func(item, key)
            
            # Tokenize the comparison text
            target_tokens = set(comparison_text.lower().replace('-', ' ').replace('/', ' ').split())
            target_tokens = {token for token in target_tokens if token not in stop_words and len(token) > 1}
            
            # Skip if either token set is empty after filtering
            if not input_tokens or not target_tokens:
                continue
            
            # Method 1: Overlap coefficient (works well for different length sets)
            overlap = len(input_tokens.intersection(target_tokens))
            overlap_score = overlap / min(len(input_tokens), len(target_tokens))
            
            # Method 2: Check for substring matches
            substring_score = 0
            for token in input_tokens:
                if token in comparison_text.lower():
                    substring_score += 0.5
                    
            # Normalize substring score to be between 0 and 1
            substring_score = min(1.0, substring_score / len(input_tokens)) if input_tokens else 0
            
            # Method 3: Check for complete containment
            containment_score = 0
            if input_str.lower() in comparison_text.lower() or comparison_text.lower() in input_str.lower():
                containment_score = 0.8
            
            # Calculate combined score with weights
            combined_score = (overlap_score * 0.6) + (substring_score * 0.3) + (containment_score * 0.1)
            
            # Keep track of the best match
            if combined_score > best_score:
                best_score = combined_score
                best_match = item
        
        # Return the match only if it's above the threshold
        if best_score >= min_threshold:
            entity_type = "service" if "service" in str(target_items).lower() else "client"
            logging.info(f"Found fuzzy {entity_type} match for '{input_str}' with score {best_score:.2f}")
            return best_match
        
        logging.debug(f"No fuzzy match found for: {input_str}")
        return None
        
    def _deduplicate_fuzzy_matches(self, matches, key_field):
        """
        Remove duplicate fuzzy matches based on input value.
        Keeps the match with the highest score when duplicates exist.
        
        Args:
            matches: List of match dictionaries
            key_field: Field to use as the deduplication key
            
        Returns:
            Deduplicated list of matches
        """
        if not matches:
            return []
            
        # Group by input value
        grouped = {}
        for match in matches:
            key = match.get(key_field, '')
            if key not in grouped or grouped[key]["score"] < match["score"]:
                grouped[key] = match
        
        # Return deduplicated list
        return list(grouped.values())