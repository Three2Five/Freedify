import asyncio
import os
import sys

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dab_service import dab_service

async def test_album_details():
    # ID from the user's logs
    album_id = "0060254767034" 
    print(f"Testing fetch for album ID: {album_id}")
    
    print(f"Using Session: {dab_service.SESSION_TOKEN[:10]}...")
    
    try:
        print(f"Calling dab_service.get_album('{album_id}')...")
        album = await dab_service.get_album(f"dab_{album_id}")
        
        if album:
            print("Success!")
            print(f"Title: {album.get('name')}")
            print(f"Artist: {album.get('artists')}")
            print(f"Tracks: {len(album.get('tracks', []))}")
            if album.get('tracks'):
                t1 = album['tracks'][0]
                print(f"Track 1: {t1.get('name')} - {t1.get('duration')}")
            print("Full Album Object Keys:", album.keys())
        else:
            print("Failed: get_album returned None")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_album_details())
