import os
import uuid
import logging
from pathlib import Path
from dotenv import load_dotenv
import io
import soundfile as sf
import pygame
import threading
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CLEANED_DIR = Path(__file__).parent / "cleaned"

tts_model = None

# Initialize pygame mixer for audio playback
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

def init_voice_cloning():
    """Initialize Coqui TTS voice cloning system"""
    global tts_model
    
    if tts_model is None:
        try:
            from TTS.api import TTS
            import torch
            import warnings
            
            # Auto-accept Coqui license
            os.environ['COQUI_TOS_AGREED'] = '1'
            
            # Suppress warnings
            warnings.filterwarnings("ignore")
            
            # Fix PyTorch weights loading
            os.environ['TORCH_WEIGHTS_ONLY'] = 'False'
            original_load = torch.load
            def patched_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            torch.load = patched_load
            
            if torch.cuda.is_available():
                tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True).to("cuda")
            else:
                tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            torch.load = original_load
            
            logger.info("Voice cloning system initialized")
            
        except Exception as e:
            logger.error(f"Voice cloning initialization failed: {e}")
            tts_model = None

def play_audio_async(audio_data):
    """Play audio in a separate thread to avoid blocking the Flask response"""
    try:
        # Create a temporary file for pygame to play
        temp_file = f"/tmp/buddy_audio_{uuid.uuid4().hex[:8]}.wav"
        with open(temp_file, 'wb') as f:
            f.write(audio_data)
        
        # Play the audio
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        # Clean up temp file
        os.remove(temp_file)
        logger.info("Audio playback completed")
        
    except Exception as e:
        logger.error(f"Error playing audio: {e}")

def listen_to_pipe():
    """Listen for commands from named pipe"""
    pipe_path = "/tmp/buddy_to_audio"
    
    while True:
        try:
            # Wait for pipe to exist
            while not os.path.exists(pipe_path):
                time.sleep(0.1)
            
            # Open pipe for reading - this will unblock the C bridge
            with open(pipe_path, 'r') as pipe:
                logger.info("Pipe connection established - ready for commands")
                
                for line in pipe:
                    line = line.strip()
                    if line.startswith("TTS:"):
                        text = line[4:]  # Remove "TTS:" prefix
                        logger.info(f"Received TTS request: {text}")
                        
                        # Check if TTS is ready
                        if tts_model is None:
                            logger.warning("TTS not initialized yet, skipping request")
                            continue
                        
                        try:
                            # Generate and play audio
                            audio_data = clone_voice(text)
                            audio_thread = threading.Thread(target=play_audio_async, args=(audio_data,))
                            audio_thread.daemon = True
                            audio_thread.start()
                        except Exception as e:
                            logger.error(f"Error processing TTS: {e}")
                            
        except Exception as e:
            logger.error(f"Pipe listener error: {e}")
            time.sleep(1)

def clone_voice(text):
    try:
        
        # Priority: speaking_cut.mp3 first
        speaking_cut = CLEANED_DIR / "speaking_cut.mp3"
        
        
        # Generate voice cloned audio directly to memory using all references
        audio_array = tts_model.tts(
            text=text,
            speaker_wav=speaking_cut, 
            language="ja"
        )
        
        sample_rate = tts_model.synthesizer.output_sample_rate
        
        audio_buffer = io.BytesIO()
        
        sf.write(audio_buffer, audio_array, sample_rate, format='WAV')
        audio_buffer.seek(0)
        
        return audio_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        raise

if __name__ == '__main__':
    logger.info("Starting Buddy Audio Service")
    
    # Start TTS initialization in background thread
    def init_tts_async():
        logger.info("Initializing TTS system...")
        init_voice_cloning()
        if tts_model is not None:
            logger.info("TTS system ready")
        else:
            logger.error("TTS system failed to initialize")
    
    tts_thread = threading.Thread(target=init_tts_async)
    tts_thread.daemon = True  
    tts_thread.start()
    
    # Start pipe listener immediately (this will unblock C bridge)
    logger.info("Starting pipe listener - C bridge can now connect")
    listen_to_pipe()
    
    