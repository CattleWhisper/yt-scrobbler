import os
import re
import shutil
import tempfile
import yt_dlp

class YouTubeClient:
    """Client for interacting with YouTube using yt-dlp"""
    
    def __init__(self, cookies_file=None):
        self.original_cookies_file = cookies_file
        
        if not cookies_file or not os.path.exists(cookies_file):
            raise FileNotFoundError(
                f"Cookies file '{cookies_file}' not found. "
                "Please export your YouTube cookies using a browser extension."
            )
        
        # Create a writable copy of the cookies file in a temporary directory
        # This is necessary because yt-dlp may need to write to the cookies file,
        # and the original file might be on a readonly filesystem
        temp_dir = tempfile.gettempdir()
        cookies_filename = os.path.basename(cookies_file)
        self.cookies_file = os.path.join(temp_dir, f"yt_scrobbler_{cookies_filename}")
        
        try:
            shutil.copy2(cookies_file, self.cookies_file)
            print(f"Copied cookies from {cookies_file} to {self.cookies_file}")
        except Exception as e:
            print(f"Warning: Could not copy cookies file: {e}")
            print(f"Using original cookies file: {cookies_file}")
            self.cookies_file = cookies_file
    
    def extract_video_id(self, url_or_id):
        """Extract YouTube video ID from various formats"""
        if not url_or_id:
            return None
        
        # If it's already just an ID (11 characters, alphanumeric with - and _)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id
        
        # Extract from various YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        return None
    
    def mark_as_watched(self, video_id, debug=False):
        """
        Mark a video as watched using yt-dlp's built-in functionality.
        
        Args:
            video_id: YouTube video ID or URL
            debug: If True, print detailed debugging information
        """
        try:
            video_id = self.extract_video_id(video_id)
            if not video_id:
                print(f"Could not extract video ID from: {video_id}")
                return False
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Configure yt-dlp options
            ydl_opts = {
                'cookiefile': self.cookies_file,
                'mark_watched': True,  # Mark video as watched
                'skip_download': True,  # Don't download the video
                'quiet': not debug,  # Show output only in debug mode
                'no_warnings': not debug,
            }
            
            if debug:
                print(f"\n[DEBUG] Video ID: {video_id}")
                print(f"[DEBUG] Video URL: {video_url}")
                print(f"[DEBUG] Using yt-dlp to mark as watched...")
            
            # Use yt-dlp to mark the video as watched
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            print(f"Successfully marked video {video_id} as watched")
            return True
            
        except Exception as e:
            print(f"Error marking video as watched: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            return False
    
    def get_video_info(self, video_id):
        """Get information about a video using yt-dlp"""
        try:
            video_id = self.extract_video_id(video_id)
            if not video_id:
                return None
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            ydl_opts = {
                'cookiefile': self.cookies_file,
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'author': info.get('uploader'),
                    'duration': info.get('duration'),
                }
            
        except Exception as e:
            print(f"Error getting video info: {e}")
            return None
