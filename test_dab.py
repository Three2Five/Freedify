
import httpx
import asyncio

async def test_dab():
    url = "https://dabmusic.xyz/api/search?q=the+beatles"
    cookies = {
        "session": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6NTg3MzksImlhdCI6MTc2NzU4MTM2OCwiZXhwIjoxNzY4MTg2MTY4fQ.0HXwE88sfB2DhjGRdbjP9u5l3Beez1SS42UthxA_KdQ"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, cookies=cookies, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        if resp.status_code == 200:
            print(f"Body: {resp.text[:500]}...")
        else:
            print(f"Error: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_dab())
