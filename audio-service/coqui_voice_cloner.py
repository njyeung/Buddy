"""
Coqui TTS Voice Cloning Module
High-quality voice cloning using XTTS v2 with your 20 minutes of training data
"""

import os
import uuid
import logging
import random
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class CoquiVoiceCloner:
    """Voice cloning using Coqui TTS XTTS v2"""
    
    def __init__(self, training_data_dir: str, temp_dir: str):
        self.training_data_dir = Path(training_data_dir)
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize TTS model (will be loaded on first use)
        self.tts_model = None
        self.training_samples = []
        
        # Load training samples
        self._load_training_samples()
        
    def _load_training_samples(self):
        """Load available training audio samples"""
        if not self.training_data_dir.exists():
            logger.warning(f"Training data directory not found: {self.training_data_dir}")
            return
            
        # Find all audio files
        audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
        for ext in audio_extensions:
            self.training_samples.extend(list(self.training_data_dir.glob(f"*{ext}")))
            
        logger.info(f"Found {len(self.training_samples)} training samples")
        for sample in self.training_samples[:5]:  # Show first 5
            logger.info(f"  - {sample.name}")
        if len(self.training_samples) > 5:
            logger.info(f"  ... and {len(self.training_samples) - 5} more")
    
    def _initialize_model(self):
        """Initialize the Coqui TTS model"""
        if self.tts_model is None:
            try:
                from TTS.api import TTS
                
                # Use XTTS v2 - the best model for voice cloning
                model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
                logger.info(f"Loading Coqui TTS model: {model_name}")
                
                self.tts_model = TTS(model_name, progress_bar=False)
                logger.info("Coqui TTS model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load Coqui TTS model: {e}")
                raise
    
    def get_random_reference_sample(self) -> Optional[str]:
        """Get a random training sample as reference"""
        if not self.training_samples:
            return None
        return str(random.choice(self.training_samples))
    
    def get_best_reference_samples(self, num_samples: int = 3) -> List[str]:
        """Get best reference samples (for multi-sample inference)"""
        if not self.training_samples:
            return []
        
        # For now, return random samples, but could be enhanced with
        # quality scoring based on audio properties
        selected = random.sample(
            self.training_samples, 
            min(num_samples, len(self.training_samples))
        )
        return [str(sample) for sample in selected]
    
    def clone_voice(self, text: str, output_path: str, 
                   reference_sample: Optional[str] = None,
                   language: str = "en") -> bool:
        """
        Clone voice using Coqui TTS
        
        Args:
            text: Text to synthesize
            output_path: Path to save the generated audio
            reference_sample: Specific reference audio (if None, uses random)
            language: Language code for synthesis
        """
        try:
            # Initialize model if needed
            self._initialize_model()
            
            # Get reference sample
            if reference_sample is None:
                reference_sample = self.get_random_reference_sample()
            
            if reference_sample is None:
                raise ValueError("No training samples available for voice cloning")
            
            logger.info(f"Cloning voice with reference: {Path(reference_sample).name}")
            logger.info(f"Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Generate audio using voice cloning
            self.tts_model.tts_with_vc_to_file(
                text=text,
                speaker_wav=reference_sample,
                file_path=output_path,
                language=language
            )
            
            # Verify output file was created
            if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                logger.info(f"Voice cloning successful: {output_path}")
                return True
            else:
                logger.error("Voice cloning failed: output file not created or empty")
                return False
                
        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            return False
    
    def clone_voice_multi_reference(self, text: str, output_path: str,
                                   num_references: int = 3,
                                   language: str = "en") -> bool:
        """
        Enhanced voice cloning using multiple reference samples
        This can improve quality and consistency
        """
        try:
            # Get multiple reference samples
            reference_samples = self.get_best_reference_samples(num_references)
            if not reference_samples:
                return self.clone_voice(text, output_path, language=language)
            
            logger.info(f"Multi-reference cloning with {len(reference_samples)} samples")
            
            # For now, use the first sample (could be enhanced to blend multiple)
            # Full multi-reference would require model modifications
            return self.clone_voice(text, output_path, reference_samples[0], language)
            
        except Exception as e:
            logger.error(f"Multi-reference cloning failed: {e}")
            return False
    
    def generate_temp_filename(self, prefix: str = "cloned") -> str:
        """Generate a temporary filename"""
        return str(self.temp_dir / f"{prefix}_{uuid.uuid4().hex[:8]}.wav")
    
    def get_voice_info(self) -> dict:
        """Get information about available voice data"""
        return {
            'num_training_samples': len(self.training_samples),
            'training_samples': [sample.name for sample in self.training_samples],
            'model_loaded': self.tts_model is not None,
            'supported_languages': ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'ja', 'hu', 'ko']
        }


# Test function
def test_coqui_voice_cloner():
    """Test the Coqui voice cloner"""
    try:
        cloner = CoquiVoiceCloner(
            training_data_dir="cleaned",
            temp_dir="temp"
        )
        
        info = cloner.get_voice_info()
        print("Voice cloner info:")
        for key, value in info.items():
            if key == 'training_samples':
                print(f"  {key}: {len(value)} samples")
            else:
                print(f"  {key}: {value}")
        
        return cloner
        
    except Exception as e:
        print(f"Voice cloner test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_coqui_voice_cloner()