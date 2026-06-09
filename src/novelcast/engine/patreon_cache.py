# novelcast/engine/patreon_cache.py
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PatreonCache:
    """Cache Patreon posts and chapters"""
    
    def __init__(self, cache_dir: str = ".cache/patreon"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_campaign_file(self, campaign_id: str) -> str:
        """Get path to campaign cache file"""
        return os.path.join(self.cache_dir, f"campaign_{campaign_id}.json")
    
    def _get_metadata_file(self, campaign_id: str) -> str:
        """Get path to campaign metadata file"""
        return os.path.join(self.cache_dir, f"metadata_{campaign_id}.json")
    
    # -------------------------
    # POSTS CACHE
    # -------------------------
    def get_cached_posts(self, campaign_id: str) -> Optional[List[Dict]]:
        """Get cached posts for campaign"""
        cache_file = self._get_campaign_file(campaign_id)
        
        if not os.path.exists(cache_file):
            logger.debug("No cached posts for campaign %s", campaign_id)
            return None
        
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            logger.info("Loaded %d cached posts for campaign %s", len(data.get("posts", [])), campaign_id)
            return data.get("posts", [])
        
        except Exception as e:
            logger.warning("Failed to load post cache: %s", e)
            return None
    
    def save_posts(self, campaign_id: str, posts: List[Dict], creator_name: str = ""):
        """Save posts to cache"""
        cache_file = self._get_campaign_file(campaign_id)
        
        try:
            data = {
                "campaign_id": campaign_id,
                "creator_name": creator_name,
                "posts": posts,
                "cached_at": datetime.utcnow().isoformat(),
                "post_count": len(posts),
            }
            
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info("Cached %d posts for campaign %s", len(posts), campaign_id)
        
        except Exception as e:
            logger.error("Failed to cache posts: %s", e)
    
    # -------------------------
    # CHAPTERS CACHE
    # -------------------------
    def get_cached_chapters(self, campaign_id: str) -> Optional[List[Dict]]:
        """Get cached chapters for campaign"""
        metadata_file = self._get_metadata_file(campaign_id)
        
        if not os.path.exists(metadata_file):
            return None
        
        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
            
            logger.info("Loaded %d cached chapters for campaign %s", len(data.get("chapters", [])), campaign_id)
            return data.get("chapters", [])
        
        except Exception as e:
            logger.warning("Failed to load chapter cache: %s", e)
            return None
    
    def save_chapters(
        self,
        campaign_id: str,
        creator_name: str,
        chapters: List[Dict],
        url: str = ""
    ):
        """Save parsed chapters to cache"""
        metadata_file = self._get_metadata_file(campaign_id)
        
        try:
            data = {
                "campaign_id": campaign_id,
                "creator_name": creator_name,
                "url": url,
                "chapters": chapters,
                "cached_at": datetime.utcnow().isoformat(),
                "chapter_count": len(chapters),
            }
            
            with open(metadata_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info("Cached %d chapters for campaign %s", len(chapters), campaign_id)
        
        except Exception as e:
            logger.error("Failed to cache chapters: %s", e)
    
    # -------------------------
    # CACHE MANAGEMENT
    # -------------------------
    def get_last_fetch_time(self, campaign_id: str) -> Optional[datetime]:
        """Get when posts were last cached"""
        cache_file = self._get_campaign_file(campaign_id)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            cached_at = data.get("cached_at")
            if cached_at:
                return datetime.fromisoformat(cached_at)
        
        except Exception as e:
            logger.warning("Failed to get cache time: %s", e)
        
        return None
    
    def is_cache_fresh(self, campaign_id: str, max_age_hours: int = 24) -> bool:
        """Check if cache is fresh (within max_age_hours)"""
        last_fetch = self.get_last_fetch_time(campaign_id)
        
        if not last_fetch:
            return False
        
        age = datetime.utcnow() - last_fetch
        return age < timedelta(hours=max_age_hours)
    
    def clear_campaign_cache(self, campaign_id: str):
        """Clear cache for a specific campaign"""
        cache_file = self._get_campaign_file(campaign_id)
        metadata_file = self._get_metadata_file(campaign_id)
        
        try:
            if os.path.exists(cache_file):
                os.remove(cache_file)
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            
            logger.info("Cleared cache for campaign %s", campaign_id)
        except Exception as e:
            logger.error("Failed to clear cache: %s", e)
    
    def clear_all_cache(self):
        """Clear all Patreon cache"""
        try:
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info("Cleared all Patreon cache")
        except Exception as e:
            logger.error("Failed to clear all cache: %s", e)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {
            "cache_dir": self.cache_dir,
            "campaigns": 0,
            "total_posts": 0,
            "total_chapters": 0,
            "cache_size_mb": 0,
        }
        
        try:
            # Count cached campaigns
            for file in os.listdir(self.cache_dir):
                if file.startswith("campaign_"):
                    stats["campaigns"] += 1
            
            # Get cache size
            total_size = 0
            for file in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, file)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
            
            stats["cache_size_mb"] = total_size / (1024 * 1024)
        
        except Exception as e:
            logger.warning("Failed to get cache stats: %s", e)
        
        return stats