
import subprocess
import json
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, validator
import re
import unicodedata

router = APIRouter()


class TaskRequest(BaseModel):
    type: str
    phone: str
    username: str
    ai_profile: Optional[dict] = None
    msg: Optional[str] = None
    voicemsg_path: Optional[str] = None

    @validator('phone', pre=True)
    def normalize_phone(cls, v):
        digits = re.sub(r"\D", "", unicodedata.normalize("NFKD", v))
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
        return digits

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


def sanitize_task(task: TaskRequest) -> dict:
    """
    Convert TaskRequest to dict and sanitize strings
    to avoid JSON/validation issues.
    """
    task_dict = task.dict()
    
    # Sanitize strings recursively
    def sanitize_value(value):
        if isinstance(value, str):
            # Strip, remove control chars, normalize newlines
            return value.replace('\r', '').strip()
        elif isinstance(value, dict):
            return {k: sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [sanitize_value(v) for v in value]
        else:
            return value

    return sanitize_value(task_dict)


@router.post("/gvoice")
async def gvoice(tasks: List[TaskRequest]):
    try:
        #print("Received tasks:", type(tasks))

        # Sanitize all tasks
        tasks_data = [sanitize_task(task) for task in tasks]
        
        # Optional: print JSON to debug before sending to subprocess
        import json
        #print(json.dumps(tasks_data[3], indent=2))
        
        # Run gvoice_runner.py
        # proc = subprocess.Popen(
        #     ["python", "gvoice_runner.py", json.dumps(tasks_data)],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE,
        # )

        # Save tasks to a file

        with open("tasks.json", "w") as f:
            json.dump(tasks_data, f)

   


        result = subprocess.run(
            ["python", "gvoice_runner.py", "tasks.json"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"status": "error", "detail": result.stderr}

        return {"status": "success", "output": result.stdout}
    except Exception as e:
        return {"status": "error", "detail": str(e)}