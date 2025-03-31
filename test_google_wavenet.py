"""
Test script to validate Google Wavenet TTS with service account authentication.
This script tests both standard TTS and Long Audio API functionality.
"""

import os
import datetime
from utils.google_wavenet_tts import GoogleWavenetTTS
from utils.logger import get_logger

logger = get_logger(__name__)

def create_test_ssml():
    """Create the simplest possible SSML that should work with Long Audio API."""
    ssml = """<speak>
Hello, this is a test of the Google Cloud Text to Speech Long Audio API with SSML.
<break time="1s"/>
This test uses service account authentication to access the Long Audio API.
<break time="1s"/>
If you can hear this message, it means the Long Audio API is working correctly with SSML.
</speak>"""
    return ssml

def create_test_ssml_with_issues():
    """Create SSML with nested speak tags that would have previously failed."""
    ssml = """<?xml version="1.0"?>
<speak>
    <prosody rate="95%" pitch="+5%" volume="+10%">
        <speak>This is a nested speak tag that previously caused issues with the Long Audio API.</speak>
        <break time="1s"/>
        If you can hear this message, it means the Long Audio API is handling nested speak tags correctly.
    </prosody>
</speak>"""
    return ssml

def create_test_folder():
    """Create test folder structure."""
    test_dir = "test_wavenet"
    os.makedirs(test_dir, exist_ok=True)
    return test_dir

def test_standard_tts():
    """Test standard TTS API with a small text string."""
    logger.info("Testing standard TTS API with text input")
    tts = GoogleWavenetTTS()
    text = "This is a test of the standard Google Text to Speech API using service account authentication."
    
    test_dir = create_test_folder()
    output_file = os.path.join(test_dir, "standard_tts_test.mp3")
    
    # Generate audio from text
    try:
        audio_data = tts.generate_audio(text, is_ssml=False)
        with open(output_file, "wb") as f:
            f.write(audio_data)
        logger.info(f"Standard TTS test succeeded, output saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Standard TTS test failed: {e}")
        return False

def test_standard_tts_with_ssml():
    """Test standard TTS API with SSML input."""
    logger.info("Testing standard TTS API with SSML input")
    tts = GoogleWavenetTTS()
    ssml = """<speak>
This is a test of the standard Google Text to Speech API with <emphasis level="strong">SSML</emphasis>.
<break time="1s"/>
This test is using service account authentication.
</speak>"""
    
    test_dir = create_test_folder()
    output_file = os.path.join(test_dir, "standard_tts_ssml_test.mp3")
    
    # Generate audio from SSML
    try:
        audio_data = tts.generate_audio(ssml, is_ssml=True)
        with open(output_file, "wb") as f:
            f.write(audio_data)
        logger.info(f"Standard TTS with SSML test succeeded, output saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Standard TTS with SSML test failed: {e}")
        return False

def test_long_audio_api():
    """Test Long Audio API with a simple SSML input."""
    logger.info("Testing Long Audio API with simple SSML")
    tts = GoogleWavenetTTS()
    
    # Check if Long Audio API is available
    if not tts.long_audio_available:
        logger.warning("Long Audio API is not available, skipping test")
        return False
    
    ssml = create_test_ssml()
    
    test_dir = create_test_folder()
    output_file = os.path.join(test_dir, "long_audio_test.mp3")
    
    # Generate audio from SSML using Long Audio API
    try:
        # Use _long_audio_synthesis directly to bypass chunking fallbacks
        ssml_prepared = tts._prepare_ssml_for_google(ssml, for_long_audio_api=True)
        audio_data = tts._long_audio_synthesis(ssml_prepared, is_ssml=True)
        with open(output_file, "wb") as f:
            f.write(audio_data)
        logger.info(f"Long Audio API test succeeded, output saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Long Audio API test failed: {e}")
        return False

def test_long_audio_api_with_problematic_ssml():
    """Test Long Audio API with SSML that has nested speak tags."""
    logger.info("Testing Long Audio API with problematic SSML (nested speak tags)")
    tts = GoogleWavenetTTS()
    
    # Check if Long Audio API is available
    if not tts.long_audio_available:
        logger.warning("Long Audio API is not available, skipping test")
        return False
    
    ssml = create_test_ssml_with_issues()
    
    test_dir = create_test_folder()
    output_file = os.path.join(test_dir, "long_audio_nested_test.mp3")
    
    # Generate audio from SSML using Long Audio API
    try:
        # First prepare the SSML with our new preprocessing
        ssml_prepared = tts._prepare_ssml_for_google(ssml, for_long_audio_api=True)
        
        # Log the before and after
        logger.info(f"Original SSML: {ssml[:100]}...")
        logger.info(f"Prepared SSML: {ssml_prepared[:100]}...")
        
        # Check if it still has multiple speak tags
        import re
        open_tags = len(re.findall(r'<speak[^>]*>', ssml_prepared))
        close_tags = len(re.findall(r'</speak>', ssml_prepared))
        logger.info(f"After preparation: {open_tags} open speak tags, {close_tags} close speak tags")
        
        # Use the prepared SSML with Long Audio API
        audio_data = tts._long_audio_synthesis(ssml_prepared, is_ssml=True)
        with open(output_file, "wb") as f:
            f.write(audio_data)
        logger.info(f"Long Audio API test with problematic SSML succeeded, output saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Long Audio API test with problematic SSML failed: {e}")
        logger.error(f"Error details: {str(e)}")
        return False

def test_get_script_and_generate():
    """Test the full script getting and audio generation workflow."""
    logger.info("Testing script getting and audio generation workflow")
    tts = GoogleWavenetTTS()
    
    # Create a test script
    test_dir = create_test_folder()
    test_team_code = "TST"
    date = datetime.date.today()
    date_str = date.strftime("%Y-%m-%d")
    
    # Create the directory structure for the test script
    team_script_dir = os.path.join("scripts", test_team_code)
    os.makedirs(team_script_dir, exist_ok=True)
    
    # Create both regular and optimized SSML files
    regular_ssml_path = os.path.join(team_script_dir, f"{date_str}.ssml")
    optimized_ssml_path = os.path.join(team_script_dir, f"{date_str}_optimized.ssml")
    
    # Regular SSML (with nested speak tags to test fixing)
    with open(regular_ssml_path, "w") as f:
        f.write(create_test_ssml_with_issues())
    
    # Optimized SSML (clean and ready for Long Audio API)
    with open(optimized_ssml_path, "w") as f:
        f.write(create_test_ssml())
    
    # Create the audio output directory
    team_audio_dir = os.path.join("audio", test_team_code)
    os.makedirs(team_audio_dir, exist_ok=True)
    
    # Test the full workflow
    try:
        output_file = tts.generate_and_save_audio(test_team_code, date)
        if output_file:
            logger.info(f"Full workflow test succeeded, output saved to {output_file}")
            return True
        else:
            logger.error("Full workflow test failed: No output file generated")
            return False
    except Exception as e:
        logger.error(f"Full workflow test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    logger.info("Starting Google Wavenet TTS tests")
    
    results = {}
    
    # Run tests
    results["standard_tts"] = test_standard_tts()
    results["standard_tts_with_ssml"] = test_standard_tts_with_ssml()
    results["long_audio_api"] = test_long_audio_api()
    results["long_audio_with_problematic_ssml"] = test_long_audio_api_with_problematic_ssml()
    results["full_workflow"] = test_get_script_and_generate()
    
    # Print summary
    logger.info("\n--- Test Results Summary ---")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    # Calculate overall result
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    return all(results.values())

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)