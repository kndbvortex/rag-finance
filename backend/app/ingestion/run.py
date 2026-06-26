import asyncio
import logging

from app.db.session import async_session
from app.ingestion.scraper import run_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


async def main() -> None:
    async with async_session() as session:
        docs = await run_scraper(session)
    print(f"\n{len(docs)} new documents downloaded.")


if __name__ == "__main__":
    asyncio.run(main())
