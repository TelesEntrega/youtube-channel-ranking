import os
import logging
from dotenv import load_dotenv
from app.youtube_client import YouTubeClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()
api_key = os.getenv('YT_API_KEY')
print(f"API Key available: {'Yes' if api_key else 'No'}")

if not api_key:
    exit(1)

client = YouTubeClient(api_key)

# Test handles
handles = ['@google', '@Google', 'google', '@YouTube']

print("\n--- Testing Handle Resolution ---")
for handle in handles:
    print(f"\nResolving {handle}...")
    try:
        channel_id = client.resolve_channel_id(handle)
        print(f"Result: {channel_id}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

# Test direct API call to see error
print("\n--- Direct API Call Test ---")
try:
    request = client.youtube.channels().list(
        part='id',
        forHandle='google'
    )
    response = request.execute()
    print(f"Response: {response}")
except Exception as e:
    print(f"DIRECT API ERROR: {e}")
