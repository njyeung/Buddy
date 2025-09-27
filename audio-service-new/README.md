# RVC Audio Service

Fast voice conversion service using RVC (Retrieval-based Voice Conversion).

## Quick Start for New Models

1. **Drag and drop** your RVC training checkpoint (`G_*.pth`) into this directory
2. **Run** `python main.py` - it will auto-convert and use your model
3. **Done!** Your voice model is ready for fast inference

## Files

- `main.py` - Main audio service script with auto-conversion
- `convert_checkpoint.py` - Manual checkpoint conversion script
- `model.pth` - RVC model (converted from training checkpoint)
- `rmvpe.pt` - RMVPE F0 extraction model
- `requirements.txt` - Python dependencies
- `venv/` - Python virtual environment
- `assets/` - HuBERT and RMVPE model files
- `infer/` - RVC inference modules
- `configs/` - RVC configuration files
- `i18n/` - Internationalization files

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Option 1: Use existing model.pth
python main.py

# Option 2: Drag your RVC training checkpoint (G_*.pth) into this directory
# main.py will auto-convert it to model.pth

# Option 3: Manual conversion
python convert_checkpoint.py G_12345.pth
python convert_checkpoint.py G_12345.pth --output my_model.pth

# Test mode
python main.py --test
```

## Features

- **Fast processing**: ~5-6 seconds for 3+ minute audio
- **Accurate timing**: Automatically stretches output to match input duration
- **Any input format**: Accepts any audio format via ffmpeg normalization
- **Auto-conversion**: Drag and drop training checkpoints for instant setup
- **Pipe interface**: Listens on `/tmp/buddy_to_audio` for TTS commands
- **RMVPE F0 extraction**: Fast and high-quality pitch detection

## Performance

- Input normalization: ffmpeg → 16kHz mono
- F0 extraction: ~2s (RMVPE)
- Voice conversion: ~3s
- Output stretching: ~1s (if needed)
- **Total**: ~5-6 seconds

## Integration

Designed to replace slow TTS with fast voice conversion. Listens for commands like:
```
TTS:Hello world
```

Outputs converted audio and plays it automatically.

## Attribution

This project uses [RVC (Retrieval-based Voice Conversion)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) for voice conversion inference. RVC is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**RVC Copyright**: Copyright (c) 2023 liujing04, 源文雨, Ftps