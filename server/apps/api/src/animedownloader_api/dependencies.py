from collections.abc import AsyncIterator

from animedownloader_nyaa import NyaaClient


async def get_nyaa_client() -> AsyncIterator[NyaaClient]:
    async with NyaaClient() as client:
        yield client
