from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from typing import Optional




#from helpers.email_sender_mailjet import  email_sender_mailjet
from helpers.email_sender import  send_email_full,download_file



import os
import requests
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

SENDER_EMAIL=os.getenv("SENDER_EMAIL")
SENDER_APP_PASS=os.getenv("SENDER_APP_PASS")



router = APIRouter()





class EmailRequest(BaseModel):
    receiver_email: str
    subject: str
    html_body: str
    attachment: Optional[str] = None

  

@router.post("/send-email")
async def send_email(payload: EmailRequest):
    try:    

        # Download the attachment file if provided
        attachment_file = download_file(payload.attachment) if payload.attachment else None

        # Send email with or without attachment
        send_email_full(
            sender_email=SENDER_EMAIL,
            receiver_email=payload.receiver_email,
            app_password=SENDER_APP_PASS,
            subject=payload.subject,
            html_body=payload.html_body,  # Use the fetched HTML content
            attachment=payload.attachment,  # Pass the attachment file path
        )

        return {"status": "success", "message": "Email sent successfully."}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch content from URL: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
