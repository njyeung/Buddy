#!/usr/bin/env python3
"""
Audio Service - TTS + RVC Voice Conversion
Standalone HTTP service for text-to-speech with voice conversion
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from openai import OpenAI

# Load environment variables
load_dotenv()

# Add RVC modules to path
sys.path.append(str(Path(__file__).parent / "rvc"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Configuration
TEMP_DIR = Path(__file__).parent / "temp"
MODELS_DIR = Path(__file__).parent / "models"
TEMP_DIR.mkdir(exist_ok=True)

# Global instances (will be initialized on first use)
rvc_instance = None
available_voices = {}
openai_client = None

def init_openai():
    """Initialize OpenAI client for TTS"""
    global openai_client
    if openai_client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        openai_client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")

def init_voice_cloning():
    """Initialize Coqui voice cloning system"""
    global rvc_instance, available_voices
    if rvc_instance is None:
        try:
            from coqui_voice_cloner import CoquiVoiceCloner
            
            # Initialize Coqui voice cloner with training data
            training_dir = Path(__file__).parent / "cleaned"
            temp_dir = Path(__file__).parent / "temp"
            
            voice_cloner = CoquiVoiceCloner(
                training_data_dir=str(training_dir),
                temp_dir=str(temp_dir)
            )
            
            # Get voice info
            voice_info = voice_cloner.get_voice_info()
            
            if voice_info['num_training_samples'] > 0:
                # We have training data - offer custom voice
                available_voices = {
                    'custom': {
                        'name': 'custom',
                        'type': 'coqui_cloned',
                        'num_samples': voice_info['num_training_samples'],
                        'tts_only': False
                    }
                }
                rvc_instance = voice_cloner
                logger.info(f"Coqui voice cloning initialized with {voice_info['num_training_samples']} training samples")
            else:
                logger.warning("No training samples found, falling back to OpenAI TTS only")
                available_voices = {}
                rvc_instance = None
            
            # Add OpenAI TTS voices as additional options
            openai_voices = ['nova', 'alloy', 'echo', 'fable', 'onyx', 'shimmer']
            for voice in openai_voices:
                available_voices[voice] = {'tts_only': True, 'name': voice, 'type': 'openai'}
            
            logger.info(f"Voice system initialized with voices: {list(available_voices.keys())}")
            
        except Exception as e:
            logger.warning(f"Voice cloning initialization failed, using TTS-only mode: {e}")
            # Fallback: use OpenAI TTS only
            available_voices = {
                'nova': {'tts_only': True, 'name': 'nova', 'type': 'openai'},
                'alloy': {'tts_only': True, 'name': 'alloy', 'type': 'openai'},  
                'echo': {'tts_only': True, 'name': 'echo', 'type': 'openai'},
                'fable': {'tts_only': True, 'name': 'fable', 'type': 'openai'},
                'onyx': {'tts_only': True, 'name': 'onyx', 'type': 'openai'},
                'shimmer': {'tts_only': True, 'name': 'shimmer', 'type': 'openai'}
            }
            rvc_instance = None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'audio-service',
        'voice_cloning_initialized': rvc_instance is not None,
        'available_voices': list(available_voices.keys()) if available_voices else []
    })

@app.route('/api/voices', methods=['GET'])
def list_voices():
    """List available voice models"""
    init_voice_cloning()
    return jsonify({
        'voices': list(available_voices.keys()),
        'default_voice': list(available_voices.keys())[0] if available_voices else None
    })

@app.route('/api/tts-rvc', methods=['POST'])
def tts_rvc():
    """
    Main TTS + Voice Cloning endpoint
    Request: {"text": "Hello world", "voice": "custom"}
    Response: Audio file stream
    """
    try:
        # Parse request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
            
        text = data['text']
        voice = data.get('voice', 'custom')  # Default voice
        
        if not text.strip():
            return jsonify({'error': 'Empty text provided'}), 400
            
        logger.info(f"Processing voice cloning request: text='{text[:50]}...', voice='{voice}'")
        
        # Initialize voice cloning if needed
        init_voice_cloning()
        
        if voice not in available_voices:
            return jsonify({
                'error': f'Voice "{voice}" not available',
                'available_voices': list(available_voices.keys())
            }), 400
        
        # Step 1: Generate TTS
        tts_audio_path = generate_tts(text, voice)
        
        # Step 2: Apply voice cloning (if available and not a TTS-only voice)
        if rvc_instance and voice in available_voices and not available_voices[voice].get('tts_only', False):
            output_audio_path = apply_voice_cloning(text, voice)
        else:
            # TTS-only mode or voice cloning not available
            output_audio_path = tts_audio_path
            logger.info(f"Using TTS-only mode for voice: {voice}")
        
        # Step 3: Return audio file
        return send_file(
            output_audio_path,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'voice_{voice}_{uuid.uuid4().hex[:8]}.mp3'
        )
        
    except Exception as e:
        logger.error(f"Error processing voice cloning request: {e}")
        return jsonify({'error': str(e)}), 500

def generate_tts(text, voice_name="nova"):
    """Generate TTS using OpenAI TTS API"""
    try:
        # Initialize OpenAI client
        init_openai()
        
        temp_path = TEMP_DIR / f"tts_{uuid.uuid4().hex}.mp3"
        
        # Map voice name to OpenAI voice (fallback for RVC voices)
        openai_voice = voice_name if voice_name in ['alloy', 'echo', 'fable', 'nova', 'onyx', 'shimmer'] else 'nova'
        
        # Generate TTS using OpenAI
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice=openai_voice,
            input=text,
            response_format="mp3"
        )
        
        # Save audio to file
        response.stream_to_file(temp_path)
        
        logger.info(f"Generated TTS audio: {temp_path} ({temp_path.stat().st_size} bytes)")
        return temp_path
        
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise

def apply_voice_cloning(text, voice):
    """Apply Coqui voice cloning directly"""
    try:
        output_path = TEMP_DIR / f"cloned_{voice}_{uuid.uuid4().hex}.wav"
        
        # Use Coqui voice cloner directly (bypassing TTS step)
        if rvc_instance and hasattr(rvc_instance, 'clone_voice'):
            success = rvc_instance.clone_voice(text, str(output_path))
            
            if success:
                logger.info(f"Applied voice cloning: {output_path}")
                return output_path
            else:
                logger.warning(f"Voice cloning failed, falling back to TTS")
                return generate_tts(text, voice)
        else:
            logger.warning(f"Voice cloner not available")
            return generate_tts(text, voice)
        
    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        return generate_tts(text, voice)

@app.route('/api/cleanup', methods=['POST'])
def cleanup_temp_files():
    """Clean up temporary audio files"""
    try:
        count = 0
        for file_path in TEMP_DIR.glob("*.mp3"):
            file_path.unlink()
            count += 1
        for file_path in TEMP_DIR.glob("*.wav"):
            file_path.unlink()
            count += 1
        
        return jsonify({'message': f'Cleaned up {count} temporary files'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Audio Service...")
    logger.info(f"Temp directory: {TEMP_DIR}")
    logger.info(f"Models directory: {MODELS_DIR}")
    
    # Run Flask app
    app.run(
        host='127.0.0.1',
        port=8081,
        debug=True,
        threaded=True
    )