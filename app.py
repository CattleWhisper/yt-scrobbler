import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from youtube_client import YouTubeClient
from plex_parser import PlexWebhookParser

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5000))
MIN_WATCH_PERCENTAGE = int(os.getenv('MIN_WATCH_PERCENTAGE', 90))
YOUTUBE_COOKIES_FILE = os.getenv('YOUTUBE_COOKIES_FILE', 'cookies.txt')
PLEX_LIBRARY_FILTER = os.getenv('PLEX_LIBRARY_FILTER', '').split(',') if os.getenv('PLEX_LIBRARY_FILTER') else []

# Initialize YouTube client
youtube_client = None

def init_youtube_client():
    """Initialize YouTube client lazily using yt-dlp with cookies"""
    global youtube_client
    if youtube_client is None:
        try:
            youtube_client = YouTubeClient(cookies_file=YOUTUBE_COOKIES_FILE)
            print("YouTube client initialized with yt-dlp using cookies")
        except Exception as e:
            print(f"Error initializing YouTube client: {e}")
            print("Please ensure your YouTube cookies file is present and valid.")
            raise
    return youtube_client

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'service': 'Plex YouTube Scrobbler',
        'webhook_endpoint': '/plex-webhook'
    })

@app.route('/plex-webhook', methods=['POST'])
def plex_webhook():
    """
    Webhook endpoint for Plex
    Configure this URL in your Plex Server settings under Webhooks
    """
    try:
        # Parse the Plex payload
        payload = PlexWebhookParser.parse_payload(request.form)
        if not payload:
            return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
        
        # Get video info for logging
        video_info = PlexWebhookParser.get_video_info(payload)
        event = payload.get('event')
        
        print(f"\n{'='*60}")
        print(f"Received webhook: {event}")
        print(f"Title: {video_info['title']}")
        print(f"Library: {video_info['library_section_title']}")
        print(f"User: {video_info['user']}")
        
        # Filter by library if configured
        if PLEX_LIBRARY_FILTER:
            library = video_info['library_section_title']
            if library not in PLEX_LIBRARY_FILTER:
                print(f"Skipping: Library '{library}' not in filter list")
                print('='*60 + '\n')
                return jsonify({'status': 'skipped', 'reason': 'library_filter'}), 200
        
        # Check if video was watched
        if not PlexWebhookParser.is_video_watched(payload, MIN_WATCH_PERCENTAGE):
            print(f"Skipping: Video not sufficiently watched")
            print('='*60 + '\n')
            return jsonify({'status': 'skipped', 'reason': 'not_watched'}), 200
        
        # Extract YouTube video ID
        youtube_id = PlexWebhookParser.extract_youtube_id(payload)
        if not youtube_id:
            print("Warning: Could not extract YouTube video ID from metadata")
            print("This may not be a YouTube video, or the ID is not stored in metadata")
            print('='*60 + '\n')
            return jsonify({'status': 'skipped', 'reason': 'no_youtube_id'}), 200
        
        print(f"YouTube Video ID: {youtube_id}")
        
        # Initialize YouTube client if needed
        yt_client = init_youtube_client()
        
        # Mark video as watched on YouTube
        success = yt_client.mark_as_watched(youtube_id)
        
        if success:
            print(f"✓ Successfully scrobbled to YouTube")
            print('='*60 + '\n')
            return jsonify({
                'status': 'success',
                'youtube_id': youtube_id,
                'title': video_info['title']
            }), 200
        else:
            print(f"✗ Failed to scrobble to YouTube")
            print('='*60 + '\n')
            return jsonify({
                'status': 'error',
                'message': 'Failed to mark as watched on YouTube'
            }), 500
            
    except Exception as e:
        print(f"Error processing webhook: {e}")
        print('='*60 + '\n')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/test', methods=['GET'])
def test_youtube():
    """Test endpoint to verify YouTube API connection"""
    try:
        video_id = request.args.get('video_id')
        if not video_id:
            return jsonify({
                'status': 'error',
                'message': 'Please provide a video_id parameter'
            }), 400
        
        yt_client = init_youtube_client()
        video_info = yt_client.get_video_info(video_id)
        
        if video_info:
            return jsonify({
                'status': 'success',
                'video_id': video_id,
                'title': video_info.get('snippet', {}).get('title', 'Unknown'),
                'message': 'YouTube API is working correctly'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Could not retrieve video info'
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Plex YouTube Scrobbler")
    print("="*60)
    print(f"Starting webhook server on port {WEBHOOK_PORT}")
    print(f"Webhook URL: http://localhost:{WEBHOOK_PORT}/plex-webhook")
    print(f"Min watch percentage: {MIN_WATCH_PERCENTAGE}%")
    if PLEX_LIBRARY_FILTER:
        print(f"Library filter: {', '.join(PLEX_LIBRARY_FILTER)}")
    print("="*60 + "\n")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=WEBHOOK_PORT, debug=False)
