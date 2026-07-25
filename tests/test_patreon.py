import asyncio
import httpx


async def main():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(
            "https://www.patreon.com/c/brianjnorton/posts",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )

        print(r.status_code)
        print(r.headers)
        print(r.text[:500])


asyncio.run(main())
