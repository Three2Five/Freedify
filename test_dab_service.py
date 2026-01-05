
import asyncio
from app.dab_service import dab_service

async def test_service():
    print("Searching for 'The Beatles'...")
    tracks = await dab_service.search_tracks("The Beatles", limit=1)
    if not tracks:
        print("No tracks found or error.")
        return

    track = tracks[0]
    print(f"Found: {track['title']} by {track['artist']} (ID: {track['id']})")
    print(f"Quality: {track.get('audioQuality')}")

    print("\nfetching Stream URL...")
    url = await dab_service.get_stream_url(track['id'])
    if url:
        print(f"Stream URL: {url[:100]}...")
    else:
        print("Failed to get stream URL")

    await dab_service.close()

if __name__ == "__main__":
    asyncio.run(test_service())
