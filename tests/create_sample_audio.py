#!/usr/bin/env python3
"""
Create a sample MP3 file for testing Podbean distribution.
This script creates a minimal MP3 file that can be used for testing.
"""

import os
import sys
import random

def create_sample_audio(output_path="tests/sample_audio.mp3", size_kb=50):
    """Create a sample MP3 file for testing."""
    print(f"Creating sample audio file at {output_path}...")
    
    # Make sure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create a minimal MP3 file with a valid header and some frames
    with open(output_path, "wb") as f:
        # ID3v2 tag header
        f.write(b"ID3\x03\x00\x00\x00\x00\x00\x1A")  # ID3v2.3 tag header
        
        # Title frame
        f.write(b"TIT2\x00\x00\x00\x0E\x00\x00\x00Test MP3 File")
        
        # Artist frame
        f.write(b"TPE1\x00\x00\x00\x0C\x00\x00\x00Test Artist")
        
        # Some MP3 frame data (not real audio, just a placeholder)
        # We're adding enough frames to reach approximately the requested size
        bytes_written = f.tell()
        target_size = size_kb * 1024
        
        frame_size = 192  # A typical MP3 frame size
        
        while bytes_written < target_size:
            # Each frame starts with a sync word (0xFFF) and has some bit flags
            f.write(b"\xFF\xFB\x90\x44")
            
            # Add random data for the rest of the frame
            random_data = bytearray(random.getrandbits(8) for _ in range(frame_size - 4))
            f.write(random_data)
            
            bytes_written += frame_size
    
    # Get the size of the MP3 file
    size_bytes = os.path.getsize(output_path)
    print(f"Created sample MP3 file: {output_path} ({size_bytes} bytes, {size_bytes/1024:.1f} KB)")
    
    return output_path

if __name__ == "__main__":
    # Parse arguments
    if len(sys.argv) > 1:
        size_kb = int(sys.argv[1])
        create_sample_audio(size_kb=size_kb)
    else:
        create_sample_audio() 