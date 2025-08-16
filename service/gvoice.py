
import asyncio
import time
import re
from playwright.async_api import Playwright
from helpers.ghelper import expiredlogin, format_for_google_voice
from helpers.aicallagent import pre_conn, start_conversation
from helpers.voicemail import play_audio_voice

import os
from dotenv import load_dotenv


load_dotenv()

AGENT_NAME=os.getenv("AGENT_NAME")
MY_PHONE=os.getenv("MY_PHONE")

OUTPUT_VAC_VOICEMAIL=int(os.getenv("OUTPUT_VAC"))


SESSION = os.path.join(os.path.dirname(__file__), "auth1.json")


async def is_calling(page):
    call_panel = page.locator('[aria-label="Call panel"]')
    text = await call_panel.inner_text()
    text = text.lower()
    return ":" in text


async def wait_until_call_received(page, timeout=60):
    """Wait until the call panel shows a timer '00:' (indicating call answered)."""
    call_panel = page.locator('[aria-label="Call panel"]')
    start_time = time.time()
    while True:
        try:
            text = (await call_panel.inner_text()).lower()
            if "00:" in text:
                print(" Call received (timer detected).")
                return True
            elif "calling" in text:
                print(" Still calling...")
            else:
                print(" Waiting for answer...")
        except Exception:
            pass

        if time.time() - start_time > timeout:
            print(" Timeout: No answer detected.")
            return False

        await asyncio.sleep(1)


async def send_message(page, phonenum, msg):
    """Send an SMS message to the given phone number."""
    try:
        await page.get_by_role("tab", name="Messages").click()
        await asyncio.sleep(0.5)
        await page.get_by_label("Send new message").click()
        await asyncio.sleep(0.5)
        await page.locator(".cdk-overlay-backdrop").click()
        await asyncio.sleep(0.5)

        formatted_num = format_for_google_voice(phonenum)

        input_box = page.get_by_placeholder("Type a name or phone number")
        await input_box.fill(phonenum)
        await asyncio.sleep(0.5)

        await page.get_by_role("button", name=f"Send to {formatted_num}").click()
        await asyncio.sleep(0.5)

        msg_box = page.get_by_placeholder("Type a message")
        await msg_box.fill(msg)
        await page.get_by_label("Send message").click()
        await asyncio.sleep(0.5)

        print(f" Message sent to {phonenum}: {msg}")

    except Exception as e:
        print(f" Failed to send message to {phonenum}: {e}")


        
async def end_call(page):
    await page.get_by_label("Hang up call").click()
    print("Call ended after end of conversation")


async def send_voice(page,phonenum,voicemsg_path):
    print("sending voice message..")

    try:
        input_box = page.get_by_placeholder("Enter a name or number")
        await input_box.click()
        await input_box.fill(phonenum)
        await input_box.press("Enter")
        print(f" Calling {phonenum}...")

        if await wait_until_call_received(page):
            print("Call answered.")
            await asyncio.sleep(0.5)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                play_audio_voice,
                voicemsg_path,
                10

            )

            print("VOICE MAIL sent successfully ")
            await end_call(page)

            # while await is_calling(page):
            #     print(" Talking...")
            #     await asyncio.sleep(5)
            #else:
            print(" Call ended")


        else:
            print(" No answer.")

    except Exception as e:
        print(f" Failed to call {phonenum}: {e}")







async def call_number(page, phonenum,username,ai_profile):
    client, audio_interface, AGENT_ID = pre_conn()

    try:
        input_box = page.get_by_placeholder("Enter a name or number")
        await input_box.click()
        await input_box.fill(phonenum)
        await input_box.press("Enter")
        print(f" Calling {phonenum}...")

        if await wait_until_call_received(page):
            print("Call answered.")
            loop = asyncio.get_event_loop()
            need_sms = await loop.run_in_executor(
                None,
                start_conversation,
                client,
                audio_interface,
                AGENT_ID,
                username,
                ai_profile
            )
            print("conversation finish")
            await end_call(page)

            # while await is_calling(page):
            #     print(" Talking...")
            #     await asyncio.sleep(5)
            #else:
            print(" Call ended")
            if need_sms:
                print("Sending SMS")
                SMS=f"This is {AGENT_NAME} from Good Shepherd Tours. We’d love to connect with Pastor {username} about a special opportunity for a free tour to the Holy Land. Please call us back at {MY_PHONE}. Thank you, and God bless"


                time.sleep(2)
                await send_message(page, phonenum,SMS)

        else:
            print(" No answer.")

    except Exception as e:
        print(f" Failed to call {phonenum}: {e}")





async def run_tasks(playwright: Playwright, tasks):
    """Login once, then run all tasks in order."""
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(storage_state=SESSION)
    await context.grant_permissions(["microphone"])
    page = await context.new_page()
    await page.goto("https://voice.google.com/u/0/calls", timeout=30000)

    if page.url.startswith("https://workspace.google.com/products/voice/"):
        page = await expiredlogin(page)

    for task in tasks:
        try:
            if task["type"] == "ai_call":
                await call_number(page, task["phone"],task["username"],task["ai_profile"])
            elif task["type"] == "sms":
                await send_message(page, task["phone"], task["msg"])
            elif task["type"] == "voice_message":
                await send_voice(page, task["phone"], task["voicemsg_path"])
            else:
                print(f" Unknown task type: {task}")
        except Exception as e:
            print(f" Error while processing {task}: {e}")

        print(" Waiting 5 seconds before next task...")
        await asyncio.sleep(5)

    await context.storage_state(path=SESSION)
    time.sleep(2)
    await context.close()
    await browser.close()




