import os
import uuid
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from dotenv import load_dotenv
import io
import soundfile as sf

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
CLEANED_DIR = Path(__file__).parent / "cleaned"

tts_model = None

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

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'audio-service',
        'voice_cloning_initialized': tts_model is not None
    })

@app.route('/api/tts', methods=['POST'])
def voice_clone():
    try:
        # Parse request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
            
        text = data['text']
        
        if not text.strip():
            return jsonify({'error': 'Empty text provided'}), 400
        
        # Sanity check
        init_voice_cloning()
        
        # Generate voice cloned audio in memory
        audio_data = clone_voice(text)
        
        return Response(
            audio_data,
            mimetype='audio/wav',
            headers={
                'Content-Disposition': f'inline; filename="voice_{uuid.uuid4().hex[:8]}.wav"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing voice cloning: {e}")
        return jsonify({'error': str(e)}), 500

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
    init_voice_cloning()

    app.run(
        host='127.0.0.1',
        port=8081,
        threaded=True
    )