
import asyncio
from app.dab_service import dab_service

async def test_search():
    print("Searching Dab Music for Album 'The Beatles'...")
    try:
        # Test 1: Album Search
        resp = await dab_service.client.get(
            f"{dab_service.BASE_URL}/search",
            params={"q": "The Beatles", "type": "album", "limit": 1}
        )
        data = resp.json()
        
        album_id = None
        if "albums" in data and data['albums']:
            album_id = data['albums'][0]['id']
            print(f"Album ID: {album_id}")

        # Test 2: Track Search (Check for ISRC)
        print("\nSearching Track 'Come Together'...")
        resp = await dab_service.client.get(
            f"{dab_service.BASE_URL}/search",
            params={"q": "Come Together The Beatles", "type": "track", "limit": 1}
        )
        t_data = resp.json()
        if "tracks" in t_data and t_data['tracks']:
             print("Track Sample:", t_data['tracks'][0])

        # Test 3: Get Album Details (Guessing endpoint)
        if album_id:
            print(f"\nFetching Album Details for {album_id}...")
            # Try /album endpoint with albumId
            tags = ["/album", "/getAlbum"]
            for tag in tags:
                try:
                    url = f"{dab_service.BASE_URL}{tag}"
                    print(f"Trying {url} with albumId={album_id}")
                    resp = await dab_service.client.get(url, params={"albumId": album_id})
                    if resp.status_code == 200:
                        print(f"SUCCESS {tag}!")
                        print(resp.json())
                        break
                    else:
                        print(f"Failed {tag}: {resp.status_code}")
                        
                    # Try 'id' again just in case for getAlbum
                    resp = await dab_service.client.get(url, params={"id": album_id})
                    if resp.status_code == 200: print(f"SUCCESS {tag} (id)!"); break
                except: pass

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await dab_service.close()

if __name__ == "__main__":
    asyncio.run(test_search())
