import subprocess
import json
from fastapi import APIRouter

from typing import Optional, List
from pydantic import BaseModel, validator, ValidationError



router = APIRouter()



import re
import unicodedata

"""
type: ai_call,sms,voice_message

[
  {
    "type": "voice_message",
    "phone": "16054774432",
    "username": "kawser",
    "ai_profile": {},
    "msg": "string",
    "voicemsg_path": "C:\\Users\\KAWSER\\Desktop\\project\\DM server\\upload\\audio\\demo.mp3"
  }
]



""" 


class TaskRequest(BaseModel):
    type: str
    phone: str
    username: str
    ai_profile: Optional[dict] =None
    msg: Optional[str] = None
    voicemsg_path: Optional[str] = None




    @validator('phone', pre=True)
    def normalize_phone(cls, v):
        digits = re.sub(r"\D", "", unicodedata.normalize("NFKD", v))    
        # Remove country code if it starts with '1' (USA country code)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        
        # Ensure we have exactly 10 digits now
        if len(digits) == 10:
            return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
        else:
            return digits  # fallback to raw digits if formatting doesn't apply


    @validator('msg', always=True)
    def msg_required_if_sms(cls, v, values):
        if values.get('type') == 'sms' and not v:
            raise ValueError('msg is required when type is "sms"')
        return v

    @validator('voicemsg_path', always=True)
    def voice_required_if_voicemsg(cls, v, values):
        if values.get('type') == 'voice_message' and not v:
            raise ValueError('voicemsg_path is required when type is "voice_message"')
        return v




@router.post("/gvoice")
async def gvoice(tasks: List[TaskRequest]):
    try:
        # Convert all TaskRequest objects to dicts
        tasks_data = [task.dict() for task in tasks]

        # Run gvoice_runner.py with the tasks JSON
        proc = subprocess.Popen(
           ["python", "gvoice_runner.py", json.dumps(tasks_data)],
 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            return {"status": "error", "detail": stderr.decode(errors="replace")}

        return {"status": "success", "output": stdout.decode(errors="replace")}

    except Exception as e:
        return {"status": "error", "detail": str(e)}
