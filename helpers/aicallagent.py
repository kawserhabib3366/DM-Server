import os
import signal
import sys
import threading
import time
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation,ConversationInitiationData
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
import pyaudio
import numpy as np

import queue
import threading
import pyaudio

from dotenv import load_dotenv


load_dotenv()


AGENT_NAME=os.getenv("AGENT_NAME")

#username="Daniel"

need_send_sms=False





class VACAudioInterface:
    """Custom audio interface for Virtual Audio Cable routing compatible with ElevenLabs."""

    INPUT_FRAMES_PER_BUFFER = 4000   # 250ms @ 16kHz
    OUTPUT_FRAMES_PER_BUFFER = 1000  # 62.5ms @ 16kHz

    def __init__(self, input_device_index=None, output_device_index=None,
                 sample_rate=16000):
        self.input_device_index = input_device_index
        self.output_device_index = output_device_index
        self.sample_rate = sample_rate

        self.audio = pyaudio.PyAudio()
        self.input_callback = None
        self.output_queue: queue.Queue[bytes] = queue.Queue()
        self.should_stop = threading.Event()
        self.output_thread = None

        self.in_stream = None
        self.out_stream = None
        self.stopped = False  # <-- new flag to prevent double stop

    def start(self, input_callback):
        """Start the audio interface (required by ElevenLabs)."""
        self.input_callback = input_callback
        self.should_stop.clear()
        self.stopped = False

        # Start input stream
        self.in_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.input_device_index,
            stream_callback=self._in_callback,
            frames_per_buffer=self.INPUT_FRAMES_PER_BUFFER,
            start=True,
        )

        # Start output stream
        self.out_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            output=True,
            output_device_index=self.output_device_index,
            frames_per_buffer=self.OUTPUT_FRAMES_PER_BUFFER,
            start=True,
        )

        # Start background thread for audio output
        self.output_thread = threading.Thread(target=self._output_thread, daemon=True)
        self.output_thread.start()

        print("VAC Audio interface started")

    def stop(self):
        """Stop the audio interface (required by ElevenLabs)."""
        if self.stopped:
            return  # prevent multiple stops
        self.stopped = True

        self.should_stop.set()

        if self.output_thread:
            self.output_thread.join(timeout=1.0)
            self.output_thread = None

        # Stop and close input stream safely
        if self.in_stream:
            try:
                if self.in_stream.is_active():
                    self.in_stream.stop_stream()
            except OSError as e:
                print(f"[Warning] Could not stop input stream: {e}")
            finally:
                try:
                    self.in_stream.close()
                except Exception as e:
                    print(f"[Warning] Could not close input stream: {e}")
                self.in_stream = None

        # Stop and close output stream safely
        if self.out_stream:
            try:
                if self.out_stream.is_active():
                    self.out_stream.stop_stream()
            except OSError as e:
                print(f"[Warning] Could not stop output stream: {e}")
            finally:
                try:
                    self.out_stream.close()
                except Exception as e:
                    print(f"[Warning] Could not close output stream: {e}")
                self.out_stream = None

        try:
            self.audio.terminate()
        except Exception as e:
            print(f"[Warning] Could not terminate PyAudio: {e}")

        print("VAC Audio interface stopped")

    def output(self, audio: bytes):
        """Queue audio data for playback."""
        if not self.should_stop.is_set():
            self.output_queue.put(audio)

    def interrupt(self):
        """Interrupt playback by clearing queued audio (required by ElevenLabs)."""
        try:
            while True:
                self.output_queue.get(block=False)
        except queue.Empty:
            pass
        print("Audio interface interrupted")

    def _output_thread(self):
        """Background thread to play audio from queue."""
        while not self.should_stop.is_set():
            try:
                audio = self.output_queue.get(timeout=0.25)
                if self.out_stream and self.out_stream.is_active():
                    self.out_stream.write(audio)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Output thread error: {e}")

    def _in_callback(self, in_data, frame_count, time_info, status):
        """Internal input callback from PyAudio."""
        if self.input_callback:
            try:
                self.input_callback(in_data)
            except Exception as e:
                print(f"Input callback error: {e}")
        return (None, pyaudio.paContinue)


def find_vac_devices():
    """Helper function to find Virtual Audio Cable devices"""
    audio = pyaudio.PyAudio()
    vac_devices = []
    
    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        device_name = device_info['name'].lower()
        
        # Look for common virtual audio cable names
        
        vac_devices.append({
            'index': i,
            'name': device_info['name'],
            'max_input_channels': device_info['maxInputChannels'],
            'max_output_channels': device_info['maxOutputChannels']
        })

    audio.terminate()
    for x in vac_devices:
        print(x)
    return vac_devices




def pre_conn():

    AGENT_ID = os.getenv("AGENT_ID")
    API_KEY = os.getenv("API_KEY")
    INPUT_DEVICE_INDEX = int(os.getenv("INPUT_VAC"))#4   # VAC Input (where you'll send audio TO the AI)  #1 for testing without vac
    OUTPUT_DEVICE_INDEX = int(os.getenv("OUTPUT_VAC"))#11 # # VAC Output (where AI response will be sent) # 8
    
    if not AGENT_ID:
        sys.stderr.write("AGENT_ID must be set\n")
        sys.exit(1)
    
    if not API_KEY:
        sys.stderr.write("ELEVENLABS_API_KEY not set, assuming the agent is public\n")
        sys.exit(1)
    
    # Find Virtual Audio Cable devices
    #print("Searching for Virtual Audio Cable devices...")
    #vac_devices = find_vac_devices()
    
 
    
    # Create ElevenLabs client
    client = ElevenLabs(api_key=API_KEY)
    
    # Create custom audio interface with Virtual Audio Cable
    # Adjust these indices based on your Virtual Audio Cable setup

    
    audio_interface = VACAudioInterface(
        input_device_index=INPUT_DEVICE_INDEX,
        output_device_index=OUTPUT_DEVICE_INDEX
    )
    return client,audio_interface,AGENT_ID




def start_conversation(client, audio_interface, AGENT_ID,username,ai_profile):

    agent_script = ai_profile.get('script', '')
    agent_name = ai_profile.get('name', 'AI Agent')
    agent_personality = ai_profile.get('personality', '')

    agent_voice = ai_profile.get('voice', '')



    if agent_voice=="Male":
        agent_voice_id="IKne3meq5aSn9XLyUdCD" #charlie
    elif agent_voice =="Female":
        agent_voice_id="SAz9YHcvj6GT2YYXdXww" #river
    else:
        agent_voice_id="bIHbv24MWmeRgasZH58o" #will

    system_prompt=f""" 
# Personality

You are a warm, knowledgeable representative from Good Shepherd Tours, named {agent_name}.
{agent_personality}

{agent_script}


# Guardrails

Do not make any promises or guarantees that cannot be fulfilled beyond the free tour invitation.
Do not pressure the pastor to provide their email or phone number. If they are hesitant, reassure them that the information will only be used to send them details about the tour.
Do not disclose any confidential information about Good Shepherd Tours or its clients.
Do not engage in any unethical or illegal behavior.
Always be respectful of the pastor's time and beliefs.
If the pastor expresses no interest in receiving information, politely thank them for their time and end the call.
If the pastor asks specific questions you cannot answer, offer to have a live tour representative contact them.

# Tools

You have access to information about Good Shepherd Tours' tour destinations and the free tour opportunity.
You have access to a confirmation tool to verify the accuracy of the email address and mobile number provided.
You have access to a tool to end the call [end_call function called] .


    """



    #print(agent_profile)
    


    config = ConversationInitiationData(
    dynamic_variables={
            "agent_name": agent_name or AGENT_NAME,
            "recipientlast_name": username
            },
    conversation_config_override={
                "agent": {
                    "prompt": {
                        "prompt":system_prompt 
                    },
                    "first_message": f"Hello, this is {agent_name}, calling on behalf of Good Shepherd Tours. May I please speak with Pastor {username}?",
                    "language": "en"
                },
                "tts": {
                    "voice_id": agent_voice_id
                }
            }
        )




    def send_message():
        print("User is not available so sending sms")
        global need_send_sms
        need_send_sms=True

    conversation = Conversation(
        client,
        AGENT_ID,
        config=config,
        requires_auth=True,
        audio_interface=audio_interface,
        callback_agent_response=lambda response: (
    send_message() if "No problem — I’ll leave a quick message" in response  else print(f"Agent: {response}")
),
        callback_agent_response_correction=lambda original, corrected: print(f"Agent: {original} -> {corrected}"),
        callback_user_transcript=lambda transcript: print(f"User: {transcript}"),
    )

    try:
        print("Starting conversation session...")
        conversation.start_session()

        print("Conversation active.")
        conversation_id = conversation.wait_for_session_end()
        print(f"Conversation ID: {conversation_id}")

    except Exception as e:
        print(f"Error during conversation: {e}")
    finally:
        audio_interface.stop()
        conversation.end_session()
        if need_send_sms:
            return True
        else:
            return False
    return False


# if __name__ == '__main__':
#     find_vac_devices()
    

#     scri=""" 
#     # Environment

#     You are calling pastors to introduce Good Shepherd Tours' hosting program over the phone.
#     Your goal is to connect with Pastor {username}.
#     You are aware that the person you are speaking with may be busy and may have limited time.
#     You have access to information about Good Shepherd Tours, including tour destinations, and the free tour opportunity.
#     You are using a pre-defined script to guide the conversation.

#     # Tone

#     Your tone is enthusiastic, respectful, and inviting.
#     You speak clearly and concisely, avoiding jargon or overly technical terms.
#     You express genuine enthusiasm for the opportunity to offer a free tour to the Holy Land.
#     You are conversational and engaging, making the listener feel comfortable and valued.
#     You use a warm and inviting tone, similar to a friendly conversation rather than a sales pitch.

#     # Goal

#     Your primary goal is to share a special invitation with pastors from Good Shepherd Tours, offering them and their spouse a free, faith-enriching tour to destinations like Israel, Turkey, Greece, and Egypt, and to collect their email address and mobile number for follow-up.

#     1. **Greeting:** “Hello, this is {agent_name}, calling on behalf of Good Shepherd Tours. May I please speak with Pastor {{recipientlast_name}}?”

#     2. **If the person is NOT available:** “No problem — I’ll leave a quick message. ” → [end_call function called].

#     3. **If the person IS available:** “Wonderful, thank you for taking my call, Pastor {username}. I’m calling with a very special invitation from Good Shepherd Tours. We’d love to invite you and your spouse on a free, faith-enriching tour to destinations like Israel, Turkey, Greece, and Egypt — walking where the apostles and prophets once walked.”

#     4. **Offer Information:** “We’d like to send you more information by email so you can prayerfully consider this opportunity. Would it be alright if I verify your best email address and mobile number so you don’t miss any details?”

#     5. **Email & Phone Verification:** “Great — could you please confirm your best email address?” [Collect email and confirm it is correct]. “And may I confirm your mobile number as well?” [Collect mobile number and confirm it is correct].

#     6. **Closing:** “Thank you so much, Pastor {username}. We’ll send your information right away. And please know, if at any point you’d like to speak directly with one of our live tour representatives, we are always available to answer your questions. It’s been a blessing speaking with you today. God bless you.” → [end_call function called] .

#     """ 

#     per="""You are a warm, knowledgeable representative from Good Shepherd Tours, named {agent_name}.
# You are enthusiastic and respectful, with a passion for faith-enriching travel experiences.
# You focus on how hosting a tour can inspire pastors' and tour leaders' groups while providing great benefits.
# You use simple, accessible language and reference Biblical sites to create a connection with the listener. """

#     client,audio_interface,AGENT_ID=pre_conn()
#     start_conversation(client,audio_interface,AGENT_ID,"kawser",{'script':f'{scri}','name':'rifat','personality':f'{per}','voice':'male'})

