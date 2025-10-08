import asyncio
from playwright.async_api import async_playwright
from service import gvoice

# Example tasks
tasks =[
  {
    "type": "voice_message",
    "phone": "16054774432",
    "username": "kawser",
    "ai_profile": {},
    "msg": "string",
    "voicemsg_path": "C:\\Users\\KAWSER\\Desktop\\project\\DM server\\upload\\audio\\demo.mp3"
  }
]


async def main():
    async with async_playwright() as playwright:
        await gvoice.run_tasks(playwright, tasks)

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
