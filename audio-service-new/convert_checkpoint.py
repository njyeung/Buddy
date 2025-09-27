#!/usr/bin/env python3
"""
Convert RVC training checkpoint to inference format

Usage:
    python convert_checkpoint.py G_12345.pth
    python convert_checkpoint.py G_12345.pth --output custom_model.pth
"""
import os
import sys
import torch
import argparse
from collections import OrderedDict

def convert_checkpoint(checkpoint_path, output_path=None):
    """Convert RVC training checkpoint to inference format"""
    
    if not os.path.exists(checkpoint_path):
        print(f"❌ Checkpoint file not found: {checkpoint_path}")
        return False
    
    if output_path is None:
        output_path = "model.pth"
    
    try:
        print(f"Loading checkpoint: {checkpoint_path}")
        
        # Load the training checkpoint
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        
        # Extract model state (handle different checkpoint formats)
        if "model" in checkpoint:
            model_state = checkpoint["model"]
        elif "state_dict" in checkpoint:
            model_state = checkpoint["state_dict"]
        else:
            # Assume the checkpoint is the model state directly
            model_state = checkpoint
        
        print(f"Found {len(model_state)} parameters in checkpoint")
        
        # Create inference format
        opt = OrderedDict()
        opt["weight"] = {}
        
        # Extract generator weights only (skip discriminator weights)
        generator_keys = []
        for key in model_state.keys():
            # Skip discriminator weights (enc_q is discriminator encoder)
            if "enc_q" in key:
                continue
            
            # Convert to half precision for faster inference and smaller file size
            opt["weight"][key] = model_state[key].half()
            generator_keys.append(key)
        
        print(f"Extracted {len(generator_keys)} generator parameters")
        
        # Add RVC configuration parameters for inference
        # These are the standard RVC v2 configuration parameters
        opt["config"] = [
            513,    # filter_length
            32,     # hop_length 
            192,    # win_length
            192,    # n_mel_channels
            768,    # hidden_channels
            2,      # filter_channels
            6,      # n_heads
            3,      # n_layers
            0.1,    # dropout_p
            "1",    # version
            [3, 7, 11],  # kernel_size
            [[1, 3, 5], [1, 3, 5], [1, 3, 5]],  # dilation
            [10, 10, 2, 2],  # upsample_rates
            512,    # upsample_initial_channel
            [24, 20, 4, 4],  # upsample_kernel_sizes
            109,    # spk_embed_dim
            256,    # gin_channels
            48000   # sample_rate
        ]
        
        # Save the inference model
        print(f"Saving inference model: {output_path}")
        torch.save(opt, output_path)
        
        # Also create the model file without extension (RVC needs both)
        model_name_no_ext = os.path.splitext(output_path)[0]
        if model_name_no_ext != output_path:  # Only if different
            print(f"Creating model file without extension: {model_name_no_ext}")
            import shutil
            shutil.copy2(output_path, model_name_no_ext)
        
        # Get file sizes for comparison
        original_size = os.path.getsize(checkpoint_path)
        converted_size = os.path.getsize(output_path)
        
        print(f"✅ Conversion successful!")
        print(f"   Original size: {original_size:,} bytes ({original_size/1024/1024:.1f} MB)")
        print(f"   Converted size: {converted_size:,} bytes ({converted_size/1024/1024:.1f} MB)")
        print(f"   Size reduction: {100*(1-converted_size/original_size):.1f}%")
        print(f"   Output: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Convert RVC training checkpoint to inference format")
    parser.add_argument("checkpoint", help="Path to RVC training checkpoint (G_*.pth)")
    parser.add_argument("-o", "--output", default="model.pth", 
                       help="Output path for converted model (default: model.pth)")
    parser.add_argument("--backup", action="store_true",
                       help="Backup existing model.pth before overwriting")
    
    args = parser.parse_args()
    
    # Check if output file exists and create backup if requested
    if os.path.exists(args.output):
        if args.backup:
            backup_path = f"{args.output}.backup"
            print(f"Creating backup: {backup_path}")
            import shutil
            shutil.copy2(args.output, backup_path)
        else:
            response = input(f"Output file {args.output} exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Conversion cancelled")
                return
    
    # Perform conversion
    success = convert_checkpoint(args.checkpoint, args.output)
    
    if success:
        print(f"\n🎉 Your model is ready! Use it with:")
        print(f"   python main.py")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("RVC Checkpoint Converter")
        print("Usage: python convert_checkpoint.py G_12345.pth")
        print("       python convert_checkpoint.py G_12345.pth --output my_model.pth")
        sys.exit(1)
    
    main()