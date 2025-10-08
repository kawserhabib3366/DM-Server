import sys, json, asyncio
from service import gvoice
from playwright.async_api import async_playwright

async def main():
    # sys.argv[1] is the filename
    filename = sys.argv[1]

    # Read JSON data from file
    with open(filename, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    async with async_playwright() as p:
        await gvoice.run_tasks(p, tasks)

    print("Task finished")

if __name__ == "__main__":
    asyncio.run(main())
