"""
Test script to diagnose problems with particularly problematic SSML.
This script focuses on testing the most difficult SSML cases with the Long Audio API.
"""

import os
from utils.google_wavenet_tts import GoogleWavenetTTS
from utils.logger import get_logger

logger = get_logger(__name__)

def create_problematic_ssml():
    """Create SSML with nested speak tags that might cause issues."""
    ssml = """<?xml version="1.0"?>
<speak>
    <prosody rate="95%" pitch="+5%" volume="+10%">
        <speak>This is a nested speak tag that previously caused issues with the Long Audio API.</speak>
        <break time="1s"/>
        If you can hear this message, it means the Long Audio API is handling nested speak tags correctly.
    </prosody>
</speak>"""
    return ssml

def test_problematic_ssml():
    """Test each step of the SSML normalization process."""
    tts = GoogleWavenetTTS()
    
    # Check if Long Audio API is available
    if not tts.long_audio_available:
        logger.warning("Long Audio API is not available, skipping test")
        return
    
    # Create the problematic SSML
    ssml = create_problematic_ssml()
    logger.info(f"Original SSML:\n{ssml}")
    
    # Test step by step preprocessing
    import re
    
    # Step 1: Remove XML declaration
    step1 = re.sub(r'<\?xml.*?\?>\s*', '', ssml)
    logger.info(f"After removing XML declaration:\n{step1}")
    
    # Step 2: Count speak tags
    speak_count = len(re.findall(r'<speak[^>]*>', step1))
    logger.info(f"Found {speak_count} speak tags")
    
    # Step 3: Extract content from speak tags
    all_content = []
    for match in re.finditer(r'<speak[^>]*>(.*?)</speak>', step1, re.DOTALL):
        all_content.append(match.group(1).strip())
    
    # Log extracted content
    for i, content in enumerate(all_content):
        logger.info(f"Content from speak tag {i+1}:\n{content}")
    
    # Step 4: Combine content and create new SSML
    core_content = " ".join(all_content)
    step4 = f"<speak>{core_content}</speak>"
    logger.info(f"After combining content:\n{step4}")
    
    # Step 5: Fix attributes
    # Fix rate attributes
    for rate_match in re.finditer(r'rate="(\d+)%"', step4):
        rate_value = int(rate_match.group(1))
        decimal_rate = rate_value / 100.0
        step4 = step4.replace(rate_match.group(0), f'rate="{decimal_rate}"')
    
    # Fix pitch and volume attributes
    step5 = re.sub(r'pitch="\+\d+%"', 'pitch="high"', step4)
    step5 = re.sub(r'pitch="-\d+%"', 'pitch="low"', step5)
    step5 = re.sub(r'volume="\+\d+%"', 'volume="loud"', step5)
    logger.info(f"After fixing attributes:\n{step5}")
    
    # Step 6: Apply the full normalization function
    normalized = tts._prepare_ssml_for_google(ssml, for_long_audio_api=True)
    logger.info(f"After full normalization:\n{normalized}")
    
    # Final check for speak tags
    final_open_tags = len(re.findall(r'<speak[^>]*>', normalized))
    final_close_tags = len(re.findall(r'</speak>', normalized))
    logger.info(f"Final SSML has {final_open_tags} opening and {final_close_tags} closing speak tags")
    
    # Check if we still have any doubled speak tags
    if "<speak><speak>" in normalized or "</speak></speak>" in normalized:
        logger.error("PROBLEMATIC: Found doubled speak tags in normalized SSML")
    
    # Try sending to API
    try:
        logger.info("Attempting Long Audio API synthesis with normalized SSML")
        audio_data = tts._long_audio_synthesis(normalized, is_ssml=True)
        output_file = "test_ssml/fixed_problematic.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        logger.info(f"Success! Audio output saved to {output_file}")
    except Exception as e:
        logger.error(f"Long Audio API synthesis failed: {e}")
        # If there's an error, try a simpler SSML as last resort
        logger.info("Attempting with a simpler fallback SSML")
        simple_ssml = "<speak>This is a simplified version of the SSML used as a last fallback.</speak>"
        try:
            audio_data = tts._long_audio_synthesis(simple_ssml, is_ssml=True)
            output_file = "test_ssml/fallback_simple.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            logger.info(f"Fallback succeeded, output saved to {output_file}")
        except Exception as e:
            logger.error(f"Even fallback SSML failed: {e}")

if __name__ == "__main__":
    logger.info("Starting problematic SSML test")
    test_problematic_ssml()
    logger.info("Completed problematic SSML test")