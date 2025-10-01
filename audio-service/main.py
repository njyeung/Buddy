
import os
import sys
import torch
import numpy as np
import soundfile as sf
import tempfile
import uuid
import openai
from openai import OpenAI, AsyncOpenAI
from openai.helpers import LocalAudioPlayer
from dotenv import load_dotenv
import asyncio
from pathlib import Path
import threading
import time
import pygame
import glob
import signal
import json
from uprint import uprint


# Load environment variables from .env file
load_dotenv()

# Set up environment variables that RVC expects
os.environ["weight_root"] = "."                 # Current directory where our G_2333333.pth is located
os.environ["rmvpe_root"] = "./assets/rmvpe"     # For RMVPE model (if needed)
os.environ["index_root"] = "."                  # For index files (optional for RVC)

# Set up paths like the original
current_dir = os.getcwd()
sys.path.append(current_dir)

# Import RVC wrapper
from rvc_wrapper import RVC

# Initialize OpenAI client (handle missing API key gracefully)
openai_api_key = os.getenv('OPENAI')  # Using OPENAI instead of OPENAI_API_KEY
client = None
async_client = None
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
    async_client = AsyncOpenAI(api_key=openai_api_key)
else:
    print("Warning: OPENAI API key not found in environment")

# RVC class is now imported from rvc_wrapper.py

# Initialize pygame mixer for audio playback
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Global RVC instance
rvc_instance = None

# Global shutdown flag
shutdown_flag = threading.Event()

def initialize_rvc():
    """Initialize RVC model on server startup"""
    global rvc_instance
    
    rvc_instance = RVC()

    if not rvc_instance.load_model("model.pth"):
        return False
    
    return True

def convert_audio(base_path) -> str | None:
    """Convert audio using RVC and return output path or None if failed"""
    if rvc_instance is None or not rvc_instance.model_ready:
        return None
    
    try:
        # Generate unique output filename in tmp directory
        output_filename = f"converted_{uuid.uuid4().hex}.wav"
        output_path = str(Path(__file__).parent / "tmp" / output_filename)
        
        # Convert audio
        result = rvc_instance.convert_audio(base_path, output_path)
        
        if result and os.path.exists(result):
            return str(result)
        else:
            return None
            
    except Exception as e:
        print(f"Conversion error: {e}")
        return None

def text_to_speech(text) -> str | None:
    if client is None:
        return None
    
    # translation_response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         # {"role": "system", "content": "Convert the following English text to Japanese. Respond only with the Japanese text."},
    #         # {"role": "system", "content": "Convert the following English text to katakana (Japanese phonetic characters). Write the English words using katakana characters to represent how they would sound when pronounced by Japanese speakers. Respond only with the katakana text."},
    #         {"role": "user", "content": text}
    #     ]
    # )
    # japanese_text = translation_response.choices[0].message.content.strip()
    speech_file_path = Path(__file__).parent / "tmp" / "speech.wav"

    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="marin",
        input=text,
        instructions="Add a gentle breathiness to the voice so that the air is audible between words. Avoid sharp or exaggerated consonants; instead, let them blend smoothly into vowels."
    ) as response:
        response.stream_to_file(speech_file_path)

    return speech_file_path

def play_audio(audio_path):
    """Play audio file using pygame"""
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    
    # Wait for playback to finish
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)

def cleanup_tmp_files():
    """Delete all wav files in tmp directory"""
    try:
        tmp_dir = Path(__file__).parent / "tmp"
        wav_files = glob.glob(str(tmp_dir / "*.wav"))
        
        for wav_file in wav_files:
            try:
                os.remove(wav_file)
                pass
            except Exception as e:
                pass
                
    except Exception as e:
        pass

def test_timer():
    while not shutdown_flag.wait(10):
        uprint("TEST")
        pass

def main_loop():
    """Main processing loop that handles input"""
    while not shutdown_flag.is_set():
        try:
            line = input()
            if line.strip() == "":
                continue
            if shutdown_flag.is_set():
                break
            
            # Parse JSON input
            try:
                data = json.loads(line)
                message_type = data.get("type")
                payload = data.get("payload")
                meta = data.get("meta")
                
                if message_type in ["frontend-audio-service", "backend-audio-service"]:
                    # Process TTS request
                    base_path = text_to_speech(payload)
                    
                    dubbed_path = convert_audio(base_path)
                        
                    play_audio(dubbed_path)
                    cleanup_tmp_files()
                    
            except json.JSONDecodeError:
                # Send error response for invalid JSON
                uprint("Received nvalid json")
                
        except EOFError:
            break
        except KeyboardInterrupt:
            break

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    shutdown_flag.set()

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if initialize_rvc() == False:
        sys.stderr.write("Error: Could not initialize RVC\n")
        sys.exit(1)
    
    # WE NEED THIS
    uprint("ready")
    
    
    # Start test timer in daemon thread
    test_thread = threading.Thread(target=test_timer, daemon=True)
    test_thread.start()
    
    # Start main loop in separate thread
    main_thread = threading.Thread(target=main_loop, daemon=True)
    main_thread.start()
    
    # Main thread stays alive to handle signals
    try:
        while not shutdown_flag.is_set():
            shutdown_flag.wait(1)
    except KeyboardInterrupt:
        shutdown_flag.set()
    
    # Graceful shutdown
    exit(0)


