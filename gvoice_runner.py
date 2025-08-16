import sys, json,asyncio
from service import gvoice
from playwright.async_api import async_playwright


async def main():
    tasks = json.loads(sys.argv[1])
    async with async_playwright() as p:
        await gvoice.run_tasks(p, tasks)
    print(" Task finished")

if __name__ == "__main__":
    asyncio.run(main())