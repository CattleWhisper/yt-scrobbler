import re
from plexapi.server import PlexServer


class PlexClient:
    """Client for connecting to Plex server and fetching media information"""
    
    def __init__(self, base_url, token):
        """
        Initialize Plex client
        
        Args:
            base_url: Base URL of your Plex server (e.g., 'http://localhost:32400')
            token: Plex authentication token
        """
        self.base_url = base_url
        self.token = token
        self.server = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Plex server"""
        try:
            self.server = PlexServer(self.base_url, self.token)
            print(f"Connected to Plex server: {self.server.friendlyName}")
        except Exception as e:
            print(f"Error connecting to Plex server: {e}")
            raise
    
    def get_media_metadata(self, rating_key):
        """
        Fetch complete media metadata from Plex server using rating key
        
        Args:
            rating_key: The unique rating key for the media item
            
        Returns:
            dict: Media metadata including file paths
        """
        try:
            # Fetch the media item
            media_item = self.server.fetchItem(rating_key)
            
            # Extract relevant information
            metadata = {
                'title': media_item.title,
                'type': media_item.type,
                'rating_key': rating_key,
                'duration': getattr(media_item, 'duration', 0),
                'view_offset': getattr(media_item, 'viewOffset', 0),
                'library_section_title': media_item.librarySectionTitle if hasattr(media_item, 'librarySectionTitle') else 'Unknown',
                'files': []
            }
            
            # Extract file paths from media parts
            if hasattr(media_item, 'media'):
                for media in media_item.media:
                    for part in media.parts:
                        metadata['files'].append(part.file)
            
            return metadata
            
        except Exception as e:
            print(f"Error fetching metadata for rating key {rating_key}: {e}")
            return None
    
    def extract_youtube_id_from_files(self, file_paths):
        """
        Extract YouTube video ID from file paths
        
        Args:
            file_paths: List of file paths
            
        Returns:
            str: YouTube video ID or None
        """
        for file_path in file_paths:
            # Extract video ID from pattern [VIDEO_ID].ext
            match = re.search(r'\[([a-zA-Z0-9_-]{11})\]\.\w+$', file_path)
            if match:
                return match.group(1)
        
        return None
    
    def get_youtube_id_from_rating_key(self, rating_key):
        """
        Get YouTube video ID by fetching media metadata from Plex server
        
        Args:
            rating_key: The unique rating key for the media item
            
        Returns:
            str: YouTube video ID or None
        """
        metadata = self.get_media_metadata(rating_key)
        if not metadata:
            return None
        
        # Extract YouTube ID from file paths
        if metadata['files']:
            youtube_id = self.extract_youtube_id_from_files(metadata['files'])
            if youtube_id:
                return youtube_id
        
        # Try extracting from title as fallback
        title = metadata.get('title', '')
        match = re.search(r'\[([a-zA-Z0-9_-]{11})\]', title)
        if match:
            return match.group(1)
        
        return None
