from googletrans import Translator
from gtts import gTTS
import os
import pygame
import time

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        pygame.mixer.init()

    def translate_text(self, text, dest_lang='en'):
        try:
            translation = self.translator.translate(text, dest=dest_lang)
            return translation.text
        except Exception as e:
            print(f"Translation Error: {e}")
            return text

    def text_to_speech(self, text, lang='en'):
        try:
            # Map language codes if necessary, gTTS uses ISO 639-1
            # Dictionary for Indian languages support in gTTS
            lang_map = {
                'hindi': 'hi',
                'tamil': 'ta',
                'telugu': 'te',
                'kannada': 'kn',
                'malayalam': 'ml',
                'bengali': 'bn',
                'gujarati': 'gu',
                'marathi': 'mr',
                'english': 'en'
            }
            
            lang_code = lang_map.get(lang.lower(), 'en')
            
            tts = gTTS(text=text, lang=lang_code, slow=False)
            import uuid
            filename = f"temp_output_{uuid.uuid4()}.mp3"
            tts.save(filename)
            
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                continue
            
            pygame.mixer.music.unload()
            try:
                os.remove(filename)
            except PermissionError:
                pass 
                
        except Exception as e:
            print(f"TTS Error: {e}")
