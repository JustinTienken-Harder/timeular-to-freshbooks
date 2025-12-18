"""
Mapping Cache Manager

Stores and retrieves user's activity→customer and tag→service mappings
for faster workflow on subsequent runs.
"""

import json
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MappingCache:
    """Manages persistent storage of activity and tag mappings"""
    
    def __init__(self, cache_file: str = None):
        """
        Initialize cache manager
        
        Args:
            cache_file: Path to JSON cache file. Defaults to 'mapping_cache.json' in project root
        """
        if cache_file is None:
            # Default to project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            cache_file = os.path.join(project_root, 'mapping_cache.json')
        
        self.cache_file = cache_file
        self._ensure_cache_file()
    
    def _ensure_cache_file(self) -> None:
        """Create cache file if it doesn't exist"""
        if not os.path.exists(self.cache_file):
            self._write_cache({'activity_mappings': {}, 'tag_mappings': {}})
            logger.info(f"Created mapping cache file: {self.cache_file}")
    
    def _read_cache(self) -> Dict:
        """Read cache from file"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read cache: {e}")
            return {'activity_mappings': {}, 'tag_mappings': {}}
    
    def _write_cache(self, data: Dict) -> None:
        """Write cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved mapping cache to {self.cache_file}")
        except IOError as e:
            logger.error(f"Failed to write cache: {e}")
    
    def get_activity_mapping(self, activity: str) -> Optional[str]:
        """
        Get cached customer ID for an activity
        
        Args:
            activity: Activity name
            
        Returns:
            Customer ID or None if not cached
        """
        cache = self._read_cache()
        return cache.get('activity_mappings', {}).get(activity)
    
    def get_tag_mapping(self, tag: str) -> Optional[str]:
        """
        Get cached product ID for a tag
        
        Args:
            tag: Tag name
            
        Returns:
            Product ID or None if not cached
        """
        cache = self._read_cache()
        return cache.get('tag_mappings', {}).get(tag)
    
    def get_all_activity_mappings(self) -> Dict[str, str]:
        """Get all cached activity→customer mappings"""
        cache = self._read_cache()
        return cache.get('activity_mappings', {})
    
    def get_all_tag_mappings(self) -> Dict[str, str]:
        """Get all cached tag→service mappings"""
        cache = self._read_cache()
        return cache.get('tag_mappings', {})
    
    def save_mappings(self, activity_mappings: Dict[str, str], tag_mappings: Dict[str, str]) -> None:
        """
        Save activity and tag mappings to cache
        
        Args:
            activity_mappings: Dict of activity_name → customer_id
            tag_mappings: Dict of tag_name → product_id
        """
        cache = self._read_cache()
        
        # Merge new mappings with existing (new ones override)
        cache['activity_mappings'].update(activity_mappings)
        cache['tag_mappings'].update(tag_mappings)
        
        self._write_cache(cache)
        logger.info(f"Cached {len(activity_mappings)} activity mappings and {len(tag_mappings)} tag mappings")
    
    def clear_cache(self) -> None:
        """Clear all cached mappings"""
        self._write_cache({'activity_mappings': {}, 'tag_mappings': {}})
        logger.info("Cleared mapping cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cached mappings"""
        cache = self._read_cache()
        return {
            'total_activities': len(cache.get('activity_mappings', {})),
            'total_tags': len(cache.get('tag_mappings', {}))
        }
