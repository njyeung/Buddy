# Audio Service - TTS + RVC Voice Conversion

A standalone HTTP service that provides text-to-speech with voice conversion using RVC (Retrieval-based Voice Conversion).

## Features

- Text-to-Speech using OpenAI API
- Voice conversion using pre-trained RVC models
- HTTP streaming of audio responses
- RESTful API for easy integration
- Automatic model discovery and loading

## Architecture

```
Text Input → OpenAI TTS (neutral voice) → RVC Voice Conversion → Custom Voice Output
```

## Setup

1. **Create virtual environment and install dependencies:**
   ```bash
   cd audio-service
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   pip install -r requirements.txt
   
   # Linux/Mac  
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

## Usage

1. **Start the service:**
   ```bash
   python main.py
   ```
   Service runs on `http://localhost:8081`

2. **Check available voices:**
   ```bash
   curl http://localhost:8081/api/voices
   ```

3. **Generate voice audio:**
   ```bash
   curl -X POST http://localhost:8081/api/tts-rvc \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello world", "voice": "zutomayo"}' \
     --output audio.mp3
   ```

## API Endpoints

### `GET /api/health`
Health check and service status.

**Response:**
```json
{
  "status": "healthy",
  "service": "audio-service", 
  "rvc_initialized": true,
  "available_voices": ["zutomayo", "kiki", "keruan"]
}
```

### `GET /api/voices`
List available voice models.

**Response:**
```json
{
  "voices": ["zutomayo", "kiki", "keruan"],
  "default_voice": "zutomayo"
}
```

### `POST /api/tts-rvc`
Generate speech with voice conversion.

**Request:**
```json
{
  "text": "Hello world, this is a test",
  "voice": "zutomayo"
}
```

**Response:** 
- Content-Type: `audio/mpeg`
- Binary MP3 audio data

### `POST /api/cleanup`
Clean up temporary audio files.

**Response:**
```json
{
  "message": "Cleaned up 5 temporary files"
}
```

## Integration with React Frontend

```javascript
// Example React integration
const generateVoiceAudio = async (text, voice) => {
  try {
    const response = await fetch('http://localhost:8081/api/tts-rvc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    
    // Play audio
    const audio = new Audio(audioUrl);
    await audio.play();
    
    return audioUrl;
  } catch (error) {
    console.error('Voice generation failed:', error);
    throw error;
  }
};

// Usage
await generateVoiceAudio("Hello from Zutomayo!", "zutomayo");
```

## Error Handling

The service returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (missing text, invalid voice)
- `500`: Internal error (TTS/RVC processing failed)

Error responses include details:
```json
{
  "error": "Voice 'invalid' not available",
  "available_voices": ["zutomayo", "kiki", "keruan"]
}
```

## Performance Notes

- First request may be slower (model loading)
- Subsequent requests with the same voice are faster (model caching)
- Audio files are temporarily cached in `temp/` directory
- Use `/api/cleanup` to clear temp files periodically

## Troubleshooting

**"RVC modules not found":**
- Ensure `../RVC1006Nvidia/` directory exists
- Check that RVC dependencies are installed

**"No voice models found":**
- Verify models exist in `../RVC1006Nvidia/logs/`
- Each model needs: `G_*.pth` and `config.json`

**"OpenAI API key not set":**
- Set `OPENAI_API_KEY` in `.env` file
- Ensure the API key has TTS permissions