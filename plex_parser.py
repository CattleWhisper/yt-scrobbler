import json
import re
from urllib.parse import parse_qs, urlparse

class PlexWebhookParser:
    """Parser for Plex webhook payloads"""
    
    @staticmethod
    def parse_payload(form_data):
        """Parse the multipart form data from Plex webhook"""
        try:
            # Plex sends the payload as form data with a 'payload' field
            payload_json = form_data.get('payload')
            if not payload_json:
                print("No payload found in request")
                return None
            
            payload = json.loads(payload_json)
            return payload
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON payload: {e}")
            return None
        except Exception as e:
            print(f"Error parsing payload: {e}")
            return None
    
    @staticmethod
    def is_video_watched(payload, min_percentage=90):
        """
        Determine if the video was watched based on the event type
        and watch progress
        """
        event = payload.get('event')
        
        # We're interested in 'media.scrobble' events
        # Plex sends this when a video is considered "watched"
        if event == 'media.scrobble':
            return True
        
        # Alternatively, check 'media.stop' with high completion
        if event == 'media.stop':
            metadata = payload.get('Metadata', {})
            view_offset = metadata.get('viewOffset', 0)
            duration = metadata.get('duration', 0)
            
            if duration > 0:
                percentage = (view_offset / duration) * 100
                return percentage >= min_percentage
        
        return False
    
    @staticmethod
    def extract_youtube_id(payload):
        """
        Extract YouTube video ID from Plex metadata
        Tries multiple methods to find the YouTube video ID
        """
        metadata = payload.get('Metadata', {})
        
        # Method 1: Extract from file path (PRIMARY METHOD)
        # File pattern: '%(channel)s - %(title)s [%(id)s].%(ext)s'
        # The video ID is always in brackets before the file extension
        media = metadata.get('Media', [])
        if media and isinstance(media, list):
            for media_item in media:
                parts = media_item.get('Part', [])
                if parts and isinstance(parts, list):
                    for part in parts:
                        file_path = part.get('file', '')
                        if file_path:
                            # Extract video ID from pattern [VIDEO_ID].ext
                            match = re.search(r'\[([a-zA-Z0-9_-]{11})\]\.\w+$', file_path)
                            if match:
                                return match.group(1)
        
        # Method 2: Check title - might have the pattern in the title too
        title = metadata.get('title', '')
        match = re.search(r'\[([a-zA-Z0-9_-]{11})\]', title)
        if match:
            return match.group(1)
        
        # Method 3: Check original title for video ID pattern
        original_title = metadata.get('originalTitle', '')
        match = re.search(r'\[([a-zA-Z0-9_-]{11})\]', original_title)
        if match:
            return match.group(1)
        
        return None
    
    @staticmethod
    def _extract_id_from_string(text):
        """Extract YouTube video ID from a string"""
        if not text:
            return None
        
        # Direct YouTube ID pattern (11 chars)
        id_match = re.search(r'[a-zA-Z0-9_-]{11}', text)
        if id_match:
            potential_id = id_match.group(0)
            # Validate it looks like a real YouTube ID
            if re.match(r'^[a-zA-Z0-9_-]{11}$', potential_id):
                return potential_id
        
        # YouTube URL patterns
        youtube_patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def get_video_info(payload):
        """Extract useful video information from payload"""
        metadata = payload.get('Metadata', {})
        account = payload.get('Account', {})
        
        return {
            'title': metadata.get('title', 'Unknown'),
            'type': metadata.get('type', 'Unknown'),
            'library_section_title': metadata.get('librarySectionTitle', 'Unknown'),
            'duration': metadata.get('duration', 0),
            'view_offset': metadata.get('viewOffset', 0),
            'user': account.get('title', 'Unknown'),
            'event': payload.get('event', 'Unknown')
        }
