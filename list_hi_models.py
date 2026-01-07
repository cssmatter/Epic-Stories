
from TTS.api import TTS

# Get all models
print("Listing all Hindi models...")
tts = TTS()
for model in tts.list_models():
    if "/hi/" in model or "multilingual" in model:
        print(model)
