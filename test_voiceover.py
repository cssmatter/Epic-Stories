
import asyncio
import edge_tts

async def generate_voiceover():
    TEXT = "कर्म का अटल नियम। तुम्हें केवल कर्म करने का अधिकार है, उसके फल की चिंता नहीं करनी चाहिए।"
    VOICE = "hi-IN-MadhurNeural"
    OUTPUT_FILE = "test_voiceover.mp3"
    
    # SSML to control rate and pauses
    # Note: edge-tts support for deep SSML pauses can be tricky, 
    # we might need to concatenate files or use rate adjustments.
    
    # Madhur is Grainy and Chest-resonant
    communicate = edge_tts.Communicate(TEXT, VOICE, rate="-5%", pitch="-5Hz")
    await communicate.save(OUTPUT_FILE)
    print(f"Voiceover saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(generate_voiceover())
