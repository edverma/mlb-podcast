"""
Test script to verify Google Cloud Text-to-Speech Long Audio API with SSML that has nested speak tags.
This script creates multiple test cases with varying levels of nested <speak> tags and other SSML issues
to test our SSML normalization functions.
"""

import os
import re
import json
from utils.logger import get_logger
from utils.google_wavenet_tts import GoogleWavenetTTS
from utils.processor import PodcastProcessor

logger = get_logger(__name__)

# Create various test SSML files with known issues
def create_test_ssml_files():
    """
    Create various test SSML files with formatting issues that might occur in real-world data.
    """
    test_dir = "test_ssml"
    os.makedirs(test_dir, exist_ok=True)
    
    # Test Case 1: Nested <speak> tags
    nested_speak = """<?xml version="1.0"?>
<speak>
    <prosody rate="medium" pitch="medium">
        <speak>This is a nested speak tag that should be fixed</speak>
        <break time="1s"/>
        This content should be preserved
    </prosody>
</speak>"""

    with open(os.path.join(test_dir, "nested_speak.ssml"), "w") as f:
        f.write(nested_speak)
        
    # Test Case 2: Multiple <speak> tags at same level
    multiple_speak = """<speak>This is the first speak tag</speak>
<speak>This is the second speak tag that should be combined with the first</speak>"""

    with open(os.path.join(test_dir, "multiple_speak.ssml"), "w") as f:
        f.write(multiple_speak)
        
    # Test Case 3: Complex nested structure with attributes
    complex_nested = """<?xml version="1.0"?>
<speak xmlns="http://www.w3.org/2001/10/synthesis" version="1.0">
    <prosody rate="95%" pitch="+5%">
        <speak xmlns="http://www.w3.org/2001/10/synthesis">
            <emphasis level="strong">Nested content with improper formatting</emphasis>
            <break time="0.5s"/>
            <prosody volume="+10%">This has problematic attributes</prosody>
        </speak>
    </prosody>
</speak>"""

    with open(os.path.join(test_dir, "complex_nested.ssml"), "w") as f:
        f.write(complex_nested)

    return test_dir

def test_ssml_normalization():
    """Test our SSML normalization functions with the test files."""
    # Create the test files
    test_dir = create_test_ssml_files()
    
    # Initialize the normalizers
    tts = GoogleWavenetTTS()
    processor = PodcastProcessor()
    
    # Test each file with both normalizers
    test_files = ["nested_speak.ssml", "multiple_speak.ssml", "complex_nested.ssml"]
    
    results = {}
    
    for file_name in test_files:
        file_path = os.path.join(test_dir, file_name)
        
        with open(file_path, "r") as f:
            ssml_content = f.read()
            
        # Test with TTS normalizer
        tts_normalized = tts._prepare_ssml_for_google(ssml_content, for_long_audio_api=True)
        
        # Test with Processor normalizer
        processor_normalized = processor.fix_ssml_for_long_audio_api(ssml_content)
        
        # Count speak tags in original and normalized versions
        orig_speak_count = len(re.findall(r'<speak[^>]*>', ssml_content))
        orig_close_count = len(re.findall(r'</speak>', ssml_content))
        
        tts_speak_count = len(re.findall(r'<speak[^>]*>', tts_normalized))
        tts_close_count = len(re.findall(r'</speak>', tts_normalized))
        
        proc_speak_count = len(re.findall(r'<speak[^>]*>', processor_normalized))
        proc_close_count = len(re.findall(r'</speak>', processor_normalized))
        
        # Store results
        results[file_name] = {
            "original": {
                "speak_tags": orig_speak_count,
                "close_tags": orig_close_count,
                "content": ssml_content[:100] + "..." if len(ssml_content) > 100 else ssml_content
            },
            "tts_normalized": {
                "speak_tags": tts_speak_count,
                "close_tags": tts_close_count,
                "content": tts_normalized[:100] + "..." if len(tts_normalized) > 100 else tts_normalized,
                "fixed": tts_speak_count == 1 and tts_close_count == 1
            },
            "processor_normalized": {
                "speak_tags": proc_speak_count,
                "close_tags": proc_close_count,
                "content": processor_normalized[:100] + "..." if len(processor_normalized) > 100 else processor_normalized,
                "fixed": proc_speak_count == 1 and proc_close_count == 1
            }
        }
        
        # Print summary
        print(f"\nTesting file: {file_name}")
        print(f"  Original: {orig_speak_count} speak tags, {orig_close_count} close tags")
        print(f"  TTS Norm: {tts_speak_count} speak tags, {tts_close_count} close tags - {'FIXED' if tts_speak_count == 1 and tts_close_count == 1 else 'NOT FIXED'}")
        print(f"  Proc Norm: {proc_speak_count} speak tags, {proc_close_count} close tags - {'FIXED' if proc_speak_count == 1 and proc_close_count == 1 else 'NOT FIXED'}")
        
    # Save detailed results
    with open(os.path.join(test_dir, "normalization_results.json"), "w") as f:
        json.dump(results, f, indent=2)
        
    return results

if __name__ == "__main__":
    logger.info("Starting SSML normalization tests for nested speak tags")
    results = test_ssml_normalization()
    logger.info("SSML normalization tests completed, see test_ssml/normalization_results.json for details")