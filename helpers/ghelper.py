import asyncio
import re
from playwright.async_api import Page
import os
import unicodedata
from dotenv import load_dotenv
load_dotenv()


PASSW=os.getenv("PASSW")

async def expiredlogin(page: Page):
    """Handle Google Voice expired login popup (async version)."""
    async with page.expect_popup() as page1_info:
        #await page.get_by_role("link", name="Sign in to use Google Voice", exact=True).click()
        await page.get_by_role("banner").get_by_role("link", name="Open the Sign in to use").click()
    page1 = await page1_info.value



    await page1.get_by_role("link", name="daniel malka admin@digiqube.").click()
    await page1.get_by_label("Enter your password").fill(PASSW)
    await page1.get_by_role("button", name="Next").click()
    return page1


async def set_virtual_audio(page: Page):
    await page.get_by_label("Audio settings").click()
    await asyncio.sleep(0.2)
    await page.get_by_label("Microphone").locator("svg").click()
    await asyncio.sleep(0.2)
    await page.get_by_role("option", name="CABLE Output (VB-Audio").locator("span").click()
    await asyncio.sleep(0.3)
    await page.get_by_role("combobox", name="Microphone").press("Escape")
    return page


async def set_default_audio(page: Page):
    await page.get_by_label("Audio settings").click()
    await asyncio.sleep(0.2)
    await page.get_by_label("Microphone").locator("svg").click()
    await asyncio.sleep(0.2)
    await page.get_by_text("Default - Microphone Array (").click()
    await asyncio.sleep(0.5)
    await page.get_by_role("combobox", name="Microphone").press("Escape")



def format_for_google_voice(number: str) -> str:
    """Format phone number into Google Voice style."""
    # Normalize to remove hidden Unicode marks
    number = unicodedata.normalize("NFKD", number)
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", number)
    
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    
    return " ".join(digits)
