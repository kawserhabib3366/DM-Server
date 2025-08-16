import smtplib
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from urllib.parse import urlparse
import time

#from helpers.secretmanager.secrets import SecretManager


#secret_manager = SecretManager()



def download_file(url, save_dir="downloads", max_retries=3):
    """
    Downloads a file from a given URL, saves it in a specified directory, and returns the full path.
    
    Args:
        url (str): The URL of the file to download.
        save_dir (str): The directory where the file will be saved. Defaults to "downloads".
        max_retries (int): Maximum number of retries for downloading the file.
    
    Returns:
        str: Full path to the downloaded file, or None if the download fails.
    """
    retries = 0
    while retries < max_retries:
        try:
            # Create the directory if it doesn't exist
            os.makedirs(save_dir, exist_ok=True)

            # Extract filename from URL
            filename = url.split("/")[-1]
            file_path = os.path.join(save_dir, filename)

            # Download the file
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise error for bad responses (4xx, 5xx)

            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            print(f" File downloaded successfully: {file_path}")
            return file_path  # Return the full path to the downloaded file

        except requests.exceptions.RequestException as e:
            retries += 1
            if retries >= max_retries:
                print(f"Failed to download the file after {max_retries} attempts: {e}")
                return None
            else:
                print(f" Retry {retries}/{max_retries}: Download failed. Retrying...")
                time.sleep(2 ** retries)  # Exponential backoff for retries



def send_email_full(sender_email, receiver_email, app_password, subject, html_body, attachment: str = None):
    """
    Sends an email with an optional attachment.
    - If `attachment` is a URL, it downloads and attaches the file.
    - If `attachment` is a local file path, it attaches it directly.
    
    Args:
        sender_email (str): Sender's email address.
        receiver_email (str): Receiver's email address.
        app_password (str): App password for authentication.
        subject (str): Email subject.
        html_body (str): Email body in HTML format.
        attachment (str, optional): URL or file path to attach.
    """
    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Attach the HTML body
    message.attach(MIMEText(html_body, "html"))

    # Handle attachments
    temp_file = None  # Track temporary file for cleanup
    if attachment:
        
        parsed_url = urlparse(attachment)
        if parsed_url.scheme in ("http", "https"):
            # If it's a URL, download the file first
            temp_file = download_file(attachment)
            if temp_file is None:
                print("❌ Skipping attachment due to download failure.")
            else:
                attachment = temp_file
        elif not os.path.isfile(attachment):
            print(f"❌ File not found: {attachment}")
            return {"status":"error", "message":f"File not found: {attachment}"}

        # Attach the file if it exists
        try:
            with open(attachment, "rb") as file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file.read())

            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(attachment)}"')
            message.attach(part)
        except Exception as e:
            print(f"❌ Error attaching file: {e}")
            return {"status":"error", "message":f"Error attaching file: {e}"}

    # Send the email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()  # Secure the connection
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            print("✅ Email sent successfully!")
            return {"status":"success", "message":"Email sent successfully!"}
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your email and app password.")
        return {"status":"error", "message":"Authentication failed. Check your email and app password."}
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return {"status":"error", "message":f"An error occurred: {e}"}

    # Cleanup temporary file
    if temp_file and os.path.isfile(temp_file):
        os.remove(temp_file)


