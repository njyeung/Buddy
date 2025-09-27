#!/usr/bin/env python3
"""
Final working RVC inference - properly configured
"""
import os
import sys
import torch
import numpy as np
import soundfile as sf

# Set up environment variables that RVC expects
os.environ["weight_root"] = "."  # Current directory where our G_2333333.pth is located
os.environ["rmvpe_root"] = "."   # For RMVPE model (if needed)
os.environ["index_root"] = "."   # For index files (optional for RVC)

# Set up paths like the original
current_dir = os.getcwd()
sys.path.append(current_dir)

# Core imports from RVC
from infer.modules.vc.modules import VC
from configs.config import Config

class FinalRVC:
    def __init__(self):
        self.config = Config()
        self.vc = VC(self.config)
        self.model_ready = False
        
    def auto_convert_checkpoint(self, checkpoint_path):
        """Auto-convert training checkpoint if needed"""
        try:
            from convert_checkpoint import convert_checkpoint
            print(f"🔄 Auto-converting checkpoint: {checkpoint_path}")
            
            # Convert to model.pth
            success = convert_checkpoint(checkpoint_path, "model.pth")
            if success:
                # Also ensure the model file without extension exists
                import shutil
                if not os.path.exists("model"):
                    print("Creating model file without extension...")
                    shutil.copy2("model.pth", "model")
                print("✅ Auto-conversion successful!")
                return True
            else:
                print("❌ Auto-conversion failed")
                return False
        except Exception as e:
            print(f"❌ Auto-conversion error: {e}")
            return False
        
    def load_model(self, model_name="model.pth"):
        """Load RVC model properly"""
        try:
            print(f"Loading RVC model: {model_name}")
            
            # Check if model.pth exists, if not look for training checkpoints
            if not os.path.exists(model_name) and model_name == "model.pth":
                print("model.pth not found, looking for training checkpoints...")
                
                # Look for G_*.pth files (training checkpoints)
                import glob
                checkpoints = glob.glob("G_*.pth")
                
                if checkpoints:
                    # Use the most recent checkpoint
                    latest_checkpoint = max(checkpoints, key=os.path.getmtime)
                    print(f"Found checkpoint: {latest_checkpoint}")
                    
                    # Auto-convert it
                    if self.auto_convert_checkpoint(latest_checkpoint):
                        print(f"✅ Converted {latest_checkpoint} → model.pth")
                    else:
                        print(f"❌ Failed to convert {latest_checkpoint}")
                        return False
                else:
                    print("❌ No model.pth or G_*.pth files found!")
                    print("💡 Drag your RVC training checkpoint (G_*.pth) into this directory")
                    return False
            
            # Extract just the name without extension for the VC system
            model_id = os.path.splitext(model_name)[0]
            
            # Verify the model file exists
            if not os.path.exists(model_name):
                print(f"Model file not found: {model_name}")
                return False
            
            print(f"Using model ID: {model_id}")
            print(f"Environment weight_root: {os.getenv('weight_root')}")
            
            # Initialize VC with model ID
            # The VC system will look for: {weight_root}/{model_id}
            result = self.vc.get_vc(model_id)
            
            self.model_ready = True
            print("RVC model loaded successfully!")
            print(f"Model target sample rate: {self.vc.tgt_sr}")
            print(f"Model f0 enabled: {self.vc.if_f0}")
            return True
            
        except Exception as e:
            print(f"Model loading failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def convert_audio(self, input_path, output_path="final_output.wav"):
        """Convert audio using RVC"""
        if not self.model_ready:
            print("Model not ready!")
            return None
            
        try:
            print(f"Converting: {input_path}")
            
            # Normalize input audio sample rate using ffmpeg
            import tempfile
            import subprocess
            import shutil
            
            # Create temporary file with normalized sample rate (48kHz to match model)
            normalized_input = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            normalized_input.close()
            
            # Use ffmpeg to normalize to model's expected format but preserve timing
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000",  # Back to RVC's preferred rate
                "-ac", "1",      # Convert to mono
                "-c:a", "pcm_s16le",  # 16-bit PCM
                normalized_input.name
            ]
            
            print(f"Normalizing input with ffmpeg: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"ffmpeg error: {result.stderr}")
                import os
                os.unlink(normalized_input.name)
                return None
            
            # Use the normalized file for RVC processing
            rvc_input_path = normalized_input.name
            
            # Standard RVC parameters for good quality
            sid = 0                # Speaker ID (0 for single speaker models)
            f0_up_key = 0         # Pitch shift in semitones (0 = no change)
            f0_method = "rmvpe"    # F0 extraction method (rmvpe is fast and good quality)
            file_index = ""       # Index file (empty = no index file used)
            file_index2 = ""      # Backup index file
            index_rate = 0.5      # Index influence rate (doesn't matter with no index)
            filter_radius = 3     # Median filter radius for F0
            resample_sr = 0       # Output sample rate (0 = use model's rate)
            rms_mix_rate = 0.25   # RMS volume mixing rate
            protect = 0.33        # Consonant protection level
            
            print(f"Conversion parameters:")
            print(f"  F0 method: {f0_method}")
            print(f"  Pitch shift: {f0_up_key} semitones")
            print(f"  Filter radius: {filter_radius}")
            print(f"  RMS mix rate: {rms_mix_rate}")
            print(f"  Protect: {protect}")
            
            # Perform voice conversion using normalized input
            result_info, (sample_rate, converted_audio) = self.vc.vc_single(
                sid=sid,
                input_audio_path=rvc_input_path,
                f0_up_key=f0_up_key,
                f0_file=None,
                f0_method=f0_method,
                file_index=file_index,
                file_index2=file_index2,
                index_rate=index_rate,
                filter_radius=filter_radius,
                resample_sr=resample_sr,
                rms_mix_rate=rms_mix_rate,
                protect=protect
            )
            
            # Clean up temporary normalized file
            import os
            os.unlink(normalized_input.name)
            
            if "Success" in result_info:
                # Save initial RVC output
                temp_rvc_output = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                temp_rvc_output.close()
                sf.write(temp_rvc_output.name, converted_audio, sample_rate)
                
                # Get durations for stretching
                import librosa
                orig_audio, orig_sr = librosa.load(input_path, sr=None)
                orig_duration = len(orig_audio) / orig_sr
                rvc_duration = len(converted_audio) / sample_rate
                
                print(f"Original duration: {orig_duration:.2f}s")
                print(f"RVC output duration: {rvc_duration:.2f}s")
                
                # Calculate stretch factor
                stretch_factor = rvc_duration / orig_duration
                print(f"Stretch factor needed: {stretch_factor:.3f}")
                
                if abs(stretch_factor - 1.0) > 0.02:  # More than 2% difference
                    print(f"Applying time stretch to match original duration...")
                    
                    # Use ffmpeg to stretch without pitch change
                    stretch_cmd = [
                        "ffmpeg", "-y", "-i", temp_rvc_output.name,
                        "-filter:a", f"atempo={stretch_factor:.6f}",
                        output_path
                    ]
                    
                    print(f"Stretch command: {' '.join(stretch_cmd)}")
                    stretch_result = subprocess.run(stretch_cmd, capture_output=True, text=True)
                    
                    if stretch_result.returncode != 0:
                        print(f"Stretch failed, using original: {stretch_result.stderr}")
                        # Fallback to original RVC output
                        shutil.move(temp_rvc_output.name, output_path)
                    else:
                        print(f"✓ Successfully stretched output to match timing")
                        os.unlink(temp_rvc_output.name)
                else:
                    # No stretching needed, use RVC output directly
                    shutil.move(temp_rvc_output.name, output_path)
                
                print(f"✓ Conversion successful!")
                print(f"  Result: {result_info}")
                print(f"  Output: {output_path}")
                return output_path
            else:
                print(f"✗ Conversion failed: {result_info}")
                return None
                
        except Exception as e:
            print(f"Conversion error: {e}")
            import traceback
            traceback.print_exc()
            return None

def test_final_rvc():
    """Test the final RVC implementation"""
    print("=== Final RVC Test ===")
    
    rvc = FinalRVC()
    
    # Load the model
    print("\n1. Loading model...")
    if not rvc.load_model("model.pth"):
        print("Failed to load model!")
        return
    
    # Test conversion
    print("\n2. Testing conversion...")
    input_file = "test_input.mp3"
    output_file = "final_converted.wav"
    
    if os.path.exists(input_file):
        print(f"Input file found: {input_file}")
        print(f"Input file size: {os.path.getsize(input_file):,} bytes")
        
        result = rvc.convert_audio(input_file, output_file)
        if result and os.path.exists(result):
            output_size = os.path.getsize(result)
            print(f"\n✅ SUCCESS! Converted audio saved: {result}")
            print(f"   Output file size: {output_size:,} bytes")
            print(f"\nYou can now play {result} to hear the converted audio!")
        else:
            print("\n❌ Conversion failed")
    else:
        print(f"❌ Input file not found: {input_file}")

if __name__ == "__main__":
    test_final_rvc()