 import subprocess
subprocess.run(["pip", "install", "openai-whisper", "transformers==4.35.0", 
                "gTTS", "sounddevice", "scipy", "streamlit", "pyaudio"], 
               capture_output=True)

import streamlit as st
import whisper  
import numpy as np  
import sounddevice as sd 
from scipy.io import wavfile  
import os
from transformers import pipeline 
from gtts import gTTS
import tempfile
import time
# ════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Live Voice Translation",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════════════════════════════════════
# TITLE & INFO
# ════════════════════════════════════════════════════════════════════════════
st.title("🌍 Live Voice Translation System") 
st.markdown("""
**Speak in English → Get translated to any language → Hear it back as speech**

This system uses:
- 🎤 **Whisper** (OpenAI) — Speech to Text (ASR)
- 🔤 **Helsinki-NLP** — Text Translation
- 🔊 **gTTS** — Text to Speech
""")

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR — SETTINGS
# ════════════════════════════════════════════════════════════════════════════
st.sidebar.header("⚙️ Settings")

# Language selection
language_map = {
    "🇪🇸 Spanish": "es",
    "🇫🇷 French": "fr",
    "🇩🇪 German": "de",
    "🇮🇳 Hindi": "hi",
    "🇯🇵 Japanese": "ja",
    "🇰🇷 Korean": "ko",
    "🇨🇳 Chinese (Simplified)": "zh",
    "🇵🇹 Portuguese": "pt",
    "🇮🇹 Italian": "it",
    "🇷🇺 Russian": "ru",
}

selected_language = st.sidebar.selectbox(
    "Select Target Language:",
    list(language_map.keys()),
    index=0
)
target_lang = language_map[selected_language]

# Recording duration
recording_duration = st.sidebar.slider(
    "Recording Duration (seconds):",
    min_value=3,
    max_value=30,
    value=5,
    step=1
)

# Whisper model size
whisper_model = st.sidebar.radio(
    "Whisper Model Size (larger = more accurate but slower):",
    ["tiny", "base", "small"],
    index=1
)

# ════════════════════════════════════════════════════════════════════════════
# LOAD MODELS (CACHED FOR PERFORMANCE)
# ════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def load_whisper(model_name):
    st.write(f"⏳ Loading Whisper {model_name}...")
    return whisper.load_model(model_name)

@st.cache_resource
def load_translator(lang_code):
    st.write(f"⏳ Loading translator for {lang_code}...")
    model_name = f"Helsinki-NLP/opus-mt-en-{lang_code}"
    try:
        return pipeline("translation", model=model_name)
    except Exception as e:
        st.error(f"Translator not available for {lang_code}: {e}")
        return None

# ════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ════════════════════════════════════════════════════════════════════════════

st.markdown("---")

# STEP 1 — RECORD AUDIO
st.header("📍 Step 1: Record Your Voice")

col1, col2 = st.columns(2)

with col1:
    if st.button("🎙️ Start Recording", key="record_btn", use_container_width=True):
        st.info(f"🔴 Recording for {recording_duration} seconds... Please speak clearly!")
        
        try:
            # Record audio
            sample_rate = 16000  # 16kHz for Whisper
            audio_data = sd.rec(
                int(recording_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()  # Wait for recording to finish
            
            # Save temporarily
            temp_audio_path = "temp_audio.wav"
            wavfile.write(temp_audio_path, sample_rate, (audio_data * 32767).astype(np.int16))
            
            st.success("✅ Recording complete!")
            
            # ════════════════════════════════════════════════════════════════
            # STEP 2 — TRANSCRIBE (WHISPER)
            # ════════════════════════════════════════════════════════════════
            st.header("🎤 Step 2: Transcribing Audio")
            st.info("⏳ Whisper is transcribing your speech...")
            
            whisper_mdl = load_whisper(whisper_model)
            result = whisper_mdl.transcribe(temp_audio_path, language="en")
            original_text = result["text"].strip()
            
            st.success(f"✅ Transcribed: **{original_text}**")
            
            # ════════════════════════════════════════════════════════════════
            # STEP 3 — TRANSLATE
            # ════════════════════════════════════════════════════════════════
            st.header("🔤 Step 3: Translating Text")
            st.info(f"⏳ Translating to {selected_language}...")
            
            translator = load_translator(target_lang)
            if translator:
                translated = translator(original_text, max_length=512)
                translated_text = translated[0]['translation_text']
                
                st.success(f"✅ Translated: **{translated_text}**")
            else:
                translated_text = original_text
                st.warning("Translation not available, using original text")
            
            # ════════════════════════════════════════════════════════════════
            # STEP 4 — TEXT TO SPEECH
            # ════════════════════════════════════════════════════════════════
            st.header("🔊 Step 4: Converting to Speech")
            st.info("⏳ Generating audio with gTTS...")
            
            try:
                tts = gTTS(translated_text, lang=target_lang, slow=False)
                temp_speech_path = "temp_speech.mp3"
                tts.save(temp_speech_path)
                
                st.success("✅ Audio generated!")
                
                # Play audio
                st.audio(temp_speech_path, format="audio/mp3")
                
                # ════════════════════════════════════════════════════════════
                # FINAL SUMMARY
                # ════════════════════════════════════════════════════════════
                st.markdown("---")
                st.header("📋 Translation Summary")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🇬🇧 Original (English)")
                    st.write(original_text)
                
                with col2:
                    st.subheader(f"{selected_language}")
                    st.write(translated_text)
                
                # Cleanup
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                if os.path.exists(temp_speech_path):
                    os.remove(temp_speech_path)
                    
            except Exception as e:
                st.error(f"Error generating speech: {e}")
        
        except Exception as e:
            st.error(f"Recording failed: {e}")
            st.info("Make sure you have microphone permission and PyAudio installed")

with col2:
    st.markdown("""
    **How it works:**
    
    1. Click "Start Recording"
    2. Speak clearly in English
    3. System transcribes with Whisper
    4. Translates using Helsinki-NLP
    5. Plays translated audio
    
    **Supported Languages:**
    - Spanish, French, German
    - Hindi, Japanese, Korean
    - Chinese, Portuguese, Italian, Russian
    - And 10+ more!
    """)

# ════════════════════════════════════════════════════════════════════════════
# TEST MODE — TYPE TEXT INSTEAD OF SPEAKING
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.header("📝 Or Test with Text (No Microphone Needed)")

test_text = st.text_input("Enter English text to translate:")

if test_text:
    st.info("⏳ Translating...")
    
    translator = load_translator(target_lang)
    if translator:
        translated = translator(test_text, max_length=512)
        translated_text = translated[0]['translation_text']
        
        st.success(f"✅ Translated: **{translated_text}**")
        
        # Generate speech
        try:
            tts = gTTS(translated_text, lang=target_lang, slow=False)
            temp_speech_path = "temp_test_speech.mp3"
            tts.save(temp_speech_path)
            
            st.audio(temp_speech_path, format="audio/mp3")
            
            # Summary
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Original:**")
                st.write(test_text)
            with col2:
                st.write(f"**{selected_language}:**")
                st.write(translated_text)
            
            if os.path.exists(temp_speech_path):
                os.remove(temp_speech_path)
        except Exception as e:
            st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
**Built with:** Whisper (OpenAI) + Helsinki-NLP (Facebook) + gTTS (Google) + Streamlit

**By Vaibhav Chaturvedi** | AI/ML Engineer | CSE AI
""")
