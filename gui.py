import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
from collections import deque, Counter
try:
    from hand_tracker import HandTracker
    HAS_MEDIAPIPE = True
except Exception as e:
    HAS_MEDIAPIPE = False
    print(f"MediaPipe not found or broken: {e}. Using simulation mode.")

from classifier import GestureClassifier
from translator import TranslationService
import threading
import time
import os

class SignLanguageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Sign Language Recognition - High Precision Mode")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")

        if HAS_MEDIAPIPE:
            self.tracker = HandTracker()
        else:
            self.tracker = None
            
        self.classifier = GestureClassifier()
        self.translator = TranslationService()
        
        self.current_gesture = None
        self.last_gesture_time = 0
        self.gesture_threshold = 1.0 # Seconds to hold gesture
        
        # New State for V2
        self.current_sentence = ""
        self.last_added_char = None
        
        # Live Translation State
        self.live_translated_sentence = ""
        self.live_translated_sign = ""
        self.last_translated_sign_raw = ""
        
        # Stability Buffer for Temporal Smoothing
        self.gesture_buffer = deque(maxlen=15)
        self.buffer_threshold = 0.8 # 80% consensus required
        
        # Load Unicode Fonts for rendering (Hindi/Tamil etc.)
        self.font_path = "C:\\Windows\\Fonts\\arial.ttf" # Default for Windows
        if not os.path.exists(self.font_path):
             self.font_path = "arial.ttf" # Try current dir or fallback
        
        self.setup_ui()
        
        self.cap = cv2.VideoCapture(0)
        self.update_video()

        # Keyboard shortcuts for simulation
        import string
        for char in string.ascii_lowercase:
            self.root.bind(f'<{char}>', lambda e, c=char.upper(): self.simulate_gesture(c))
            
        self.root.bind('<space>', lambda e: self.simulate_gesture("SPACE"))
        self.root.bind('<BackSpace>', lambda e: self.simulate_gesture("BACKSPACE"))
        self.root.bind('<Return>', lambda e: self.simulate_gesture("ENTER"))

    def setup_ui(self):
        # Header
        header = tk.Label(self.root, text="Sign Language Translator (Live Subtitles)", font=("Helvetica", 24, "bold"), bg="#f0f0f0")
        header.pack(pady=10)
        
        if not HAS_MEDIAPIPE:
            warning = tk.Label(self.root, text="Warning: MediaPipe not found. Using Keyboard Simulation (Type A-Z, Space, Backspace, Enter)", font=("Arial", 10), fg="red", bg="#f0f0f0")
            warning.pack()

        # Video Frame
        self.video_label = tk.Label(self.root)
        self.video_label.pack(pady=10)

        # Controls Frame
        controls_frame = tk.Frame(self.root, bg="#f0f0f0")
        controls_frame.pack(pady=10)

        tk.Label(controls_frame, text="Select Language:", font=("Arial", 12), bg="#f0f0f0").pack(side=tk.LEFT, padx=10)
        
        self.languages = {
            'English': 'en',
            'Hindi': 'hi',
            'Tamil': 'ta',
            'Telugu': 'te',
            'Kannada': 'kn',
            'Malayalam': 'ml',
            'Bengali': 'bn',
            'Gujarati': 'gu',
            'Marathi': 'mr'
        }
        self.selected_lang = tk.StringVar()
        self.selected_lang.set('Hindi') # Set default to Hindi for better demo
        
        lang_dropdown = ttk.Combobox(controls_frame, textvariable=self.selected_lang, values=list(self.languages.keys()), state="readonly")
        lang_dropdown.pack(side=tk.LEFT, padx=10)

        # Output Text
        output_frame = tk.Frame(self.root, bg="#f0f0f0")
        output_frame.pack(pady=10)

        tk.Label(output_frame, text="Final Translation:", font=("Arial", 16, "bold"), bg="#f0f0f0").grid(row=0, column=0, padx=20, pady=10)
        self.translated_label = tk.Label(output_frame, text="Waiting for [ENTER]...", font=("Arial", 16), fg="green", bg="#f0f0f0") # Placeholder
        self.translated_label.grid(row=0, column=1, padx=20, pady=10)
        
    def async_translate(self, text, type):
        def task():
            if not text.strip():
                if type == 'sign': self.live_translated_sign = ""
                else: self.live_translated_sentence = ""
                return
                
            lang_name = self.selected_lang.get()
            target_lang_code = self.languages[lang_name]
            translated = self.translator.translate_text(text, target_lang_code)
            
            if type == 'sign':
                self.live_translated_sign = translated
            else:
                self.live_translated_sentence = translated
        
        threading.Thread(target=task, daemon=True).start()

    def draw_unicode_text(self, frame, text, position, font_size=30, color=(255, 255, 255)):
        """Helper to draw Unicode text (Hindi, Tamil, etc.) on an OpenCV frame"""
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        try:
            font = ImageFont.truetype(self.font_path, font_size)
        except:
            font = ImageFont.load_default()
            
        draw.text(position, text, font=font, fill=(color[2], color[1], color[0])) # RGB to BGR swap for filler
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def update_video(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            
            if self.tracker:
                try:
                    frame = self.tracker.findFullLandmarks(frame)
                    handLms, faceLms = self.tracker.getPositions(frame)
                    
                    if handLms:
                        raw_gesture = self.classifier.get_gesture(handLms, faceLms, frame.shape)
                        if raw_gesture:
                            self.gesture_buffer.append(raw_gesture)
                        else:
                            self.gesture_buffer.append("None")

                        # Consensus Logic
                        if len(self.gesture_buffer) == self.gesture_buffer.maxlen:
                            counts = Counter(self.gesture_buffer)
                            gesture, count = counts.most_common(1)[0]
                            
                            if gesture != "None" and count >= (self.gesture_buffer.maxlen * self.buffer_threshold):
                                # Live translation of current sign
                                if gesture != self.last_translated_sign_raw:
                                    self.last_translated_sign_raw = gesture
                                    self.async_translate(gesture, 'sign')
                                
                                # Line 1: English (Clean)
                                frame = self.draw_unicode_text(frame, gesture, (15, 20), font_size=38, color=(255, 255, 0)) 
                                
                                # Line 2: Translated (Clean)
                                if self.live_translated_sign:
                                    frame = self.draw_unicode_text(frame, self.live_translated_sign, (15, 75), font_size=34, color=(0, 255, 0))
                                
                                if gesture != self.current_gesture:
                                    self.current_gesture = gesture
                                    self.last_gesture_time = time.time()
                                    self.last_added_char = None
                                elif time.time() - self.last_gesture_time > self.gesture_threshold:
                                     if self.last_added_char != gesture:
                                         self.process_gesture(gesture)
                                         self.last_added_char = gesture
                    else:
                         self.gesture_buffer.append("None")
                except Exception as e:
                    print(f"Tracking Error: {e}")

            # --- Overlay Subtitles ---
            h, w, c = frame.shape
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, h-120), (w, h), (0, 0, 0), -1)
            alpha = 0.6
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
            
            # Sentence text lines (Unicode Aware)
            display_text = self.current_sentence + "_"
            frame = self.draw_unicode_text(frame, display_text, (20, h-90), font_size=30, color=(255, 255, 255))
            
            if self.live_translated_sentence:
                frame = self.draw_unicode_text(frame, self.live_translated_sentence, (20, h-45), font_size=30, color=(0, 255, 255))

            # Convert to Tkinter image
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_tk = ImageTk.PhotoImage(image=img_pil)
            
            self.video_label.imgtk = img_tk
            self.video_label.configure(image=img_tk)
        
        self.root.after(10, self.update_video)

    def simulate_gesture(self, gesture):
        if len(gesture) == 1:
            print(f"Simulating Key: {gesture}")
        self.process_gesture(gesture)

    def process_gesture(self, gesture):
        if not gesture or gesture == "Unknown":
            return

        if gesture == "SPACE":
            self.current_sentence += " "
        elif gesture == "BACKSPACE":
            self.current_sentence = self.current_sentence[:-1]
        elif gesture == "ENTER":
            lang_name = self.selected_lang.get()
            target_lang_code = self.languages[lang_name]
            
            sentence_to_translate = self.current_sentence
            if not sentence_to_translate.strip():
                return
                
            print(f"Final Translation: '{sentence_to_translate}' to {lang_name}")
            self.translated_label.config(text="Processing...")
            
            # Clear buffer
            self.current_sentence = ""
            self.live_translated_sentence = ""
            
            # Run final translation and speech
            threading.Thread(target=self.run_translation, args=(sentence_to_translate, lang_name, target_lang_code)).start()
        elif len(gesture) > 1:
            if self.current_sentence and not self.current_sentence.endswith(" "):
                self.current_sentence += " "
            self.current_sentence += gesture + " "
        elif len(gesture) == 1:
            self.current_sentence += gesture
            
        # Update live sentence translation
        self.async_translate(self.current_sentence, 'sentence')

    def run_translation(self, text, lang_name, lang_code):
        translated_text = self.translator.translate_text(text, lang_code)
        self.root.after(0, lambda: self.translated_label.config(text=translated_text))
        self.translator.text_to_speech(translated_text, lang_name)

    def on_closing(self):
        self.cap.release()
        self.root.destroy()
