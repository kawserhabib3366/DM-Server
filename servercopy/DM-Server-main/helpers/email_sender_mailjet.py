import os
import base64
import aiohttp
import asyncio
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(filename='mailjet_async.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET")
MAILJET_API_URL = "https://api.mailjet.com/v3.1/send"
AUTH = aiohttp.BasicAuth(login=MAILJET_API_KEY, password=MAILJET_API_SECRET)

MAX_RETRIES = 3
BATCH_SIZE = 50


async def download_file(url):
    """Download file and return bytes content."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logging.warning(f"Failed to download attachment: {url}")
                    return None
    except Exception as e:
        logging.error(f"Error downloading attachment: {e}")
        return None


async def prepare_attachment(attachment_path_or_url):
    """
    Return dict for Mailjet attachment or None if no attachment.
    Supports local file or http(s) URL.
    """
    if not attachment_path_or_url:
        return None

    parsed = urlparse(attachment_path_or_url)
    filename = os.path.basename(parsed.path)

    if parsed.scheme in ("http", "https"):
        content_bytes = await download_file(attachment_path_or_url)
        if not content_bytes:
            return None
    else:
        # Local file
        if not os.path.isfile(attachment_path_or_url):
            logging.error(f"Attachment file not found: {attachment_path_or_url}")
            return None
        with open(attachment_path_or_url, "rb") as f:
            content_bytes = f.read()

    base64_content = base64.b64encode(content_bytes).decode('utf-8')

    return {
        "ContentType": "application/octet-stream",
        "Filename": filename,
        "Base64Content": base64_content,
    }


async def send_batch(session, sender_email, template_id, batch_recipients, attachment=None):
    messages = []

    for recipient in batch_recipients:
        message = {
            "From": {"Email": sender_email, "Name": "Kawser"},
            "To": [{"Email": recipient["email"], "Name": recipient.get("name", "Customer")}],
            "TemplateID": template_id,
            "TemplateLanguage": True,
            "Subject": recipient.get("subject", "No Subject"),
            "Variables": recipient.get("variables", {}),
        }
        if attachment:
            message["Attachments"] = [attachment]
        messages.append(message)

    payload = {"Messages": messages}

    for attempt in range(MAX_RETRIES):
        try:
            async with session.post(MAILJET_API_URL, json=payload, auth=AUTH) as resp:
                resp_json = await resp.json()
                if resp.status == 200:
                    logging.info(f"Sent batch of {len(batch_recipients)} emails")
                    return True
                else:
                    logging.warning(f"Attempt {attempt+1} failed: {resp_json}")
        except Exception as e:
            logging.error(f"Exception in sending batch: {e}")
        await asyncio.sleep(2)

    return False


async def send_emails_with_template(sender_email, recipients, template_id, attachment_path_or_url=None):
    attachment = await prepare_attachment(attachment_path_or_url)

    async with aiohttp.ClientSession() as session:
        tasks = []

        for i in range(0, len(recipients), BATCH_SIZE):
            batch = recipients[i:i + BATCH_SIZE]
            tasks.append(send_batch(session, sender_email, template_id, batch, attachment))

        results = await asyncio.gather(*tasks)
        success_count = results.count(True)
        logging.info(f"Finished sending {len(recipients)} emails; successful batches: {success_count}")


# Example usage
if __name__ == "__main__":
    recipients = [
        {
            "email": "user1@example.com",
            "name": "Alice",
            "subject": "Hello Alice!",
            "variables": {"name": "Alice", "product": "Camera"}
        },
        {
            "email": "user2@example.com",
            "name": "Bob",
            "subject": "Hello Bob!",
            "variables": {"name": "Bob", "product": "Laptop"}
        },
    ]

    sender_email = "your@domain.com"
    template_id = 1234567  # Replace with your Mailjet template ID
    attachment_url_or_path = "https://example.com/file.pdf"  # or local path like "/tmp/file.pdf" or None

    asyncio.run(send_emails_with_template(sender_email, recipients, template_id, attachment_url_or_path))
