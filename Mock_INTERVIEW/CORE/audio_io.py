import json
import os
import time
from queue import Queue
from threading import Lock, Thread

import numpy as np
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import streamlit.components.v1 as components

try:
    from elevenlabs import VoiceSettings
    from elevenlabs.client import ElevenLabs
    from elevenlabs.play import play
except ImportError:
    ElevenLabs = None
    VoiceSettings = None
    play = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

from UTILS.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    RECORDING_CHANNELS,
    RECORDING_DURATION_SECONDS,
    RECORDING_SAMPLE_RATE,
    TEMP_AUDIO_FILENAME,
)

try:
    el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ElevenLabs is not None and ELEVENLABS_API_KEY else None
except Exception as e:
    print(f"Error initializing ElevenLabs client: {e}")
    el_client = None

r = sr.Recognizer()
_speech_queue: Queue[tuple[str, bool]] = Queue()
_speech_worker_lock = Lock()
_speech_worker_started = False

# now 3 function need to be created = 1) speech-to-text, 2)recoding audio, 3) transcript audio

def _speak_fallback(text: str) -> None:
    if pyttsx3 is not None:
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            return
        except Exception as e:
            print(f"Local speech fallback failed: {e}")

    print("Fallback: Printing text instead.")
    print(f"Interviewer: {text}")

def speak_text(text: str, *, use_elevenlabs: bool = True):
    """Uses elevenlabs to convert text to speech and play it."""
    if not use_elevenlabs:
        _speak_fallback(text)
        return

    if not el_client:
        print("Elevenlabs client not initialized. Cannot speak text.")
        _speak_fallback(text)
        return
    try:
        print("Generating audio...")
        
        audio = el_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.6,
                similarity_boost=0.85,
                style=0.1,
                use_speaker_boost=True,
            ),
        )
        print("speaking...") 
        play(audio)
        print("Finished speaking.")
    except Exception as e:
        print(f"Error during Elevenlabs TTS : {e}")
        _speak_fallback(text)


def _speech_worker() -> None:
    while True:
        text, use_elevenlabs = _speech_queue.get()
        try:
            time.sleep(0.05)
            speak_text(text, use_elevenlabs=use_elevenlabs)
        finally:
            _speech_queue.task_done()


def queue_speech(text: str, *, use_elevenlabs: bool = False) -> None:
    global _speech_worker_started

    _speech_queue.put((text, use_elevenlabs))
    with _speech_worker_lock:
        if not _speech_worker_started:
            _speech_worker_started = True
            Thread(target=_speech_worker, daemon=True).start()


def speak_in_browser(text: str) -> None:
    encoded_text = json.dumps(text)
    components.html(
        f"""
        <script>
        window.setTimeout(() => {{
            if (typeof window.speechSynthesis === "undefined" ||
                typeof window.SpeechSynthesisUtterance === "undefined") return;
            const utterance = new window.SpeechSynthesisUtterance({encoded_text});
            utterance.lang = "en-US";
            window.speechSynthesis.speak(utterance);
        }}, 50);
        </script>
        """,
        height=0,
    )


def render_voice_player(
    text: str,
    label: str = "Play interviewer voice",
    *,
    auto_play: bool = False,
) -> None:
    """Render a user-activated speech control to avoid browser autoplay blocking."""
    encoded_text = json.dumps(text)
    encoded_label = json.dumps(label)
    components.html(
        f"""
        <button id="voice-play" type="button">Play interviewer voice</button>
        <span id="voice-status" role="status" aria-live="polite"></span>
        <style>
          body {{ margin: 0; font-family: sans-serif; }}
          #voice-play {{
            border: 1px solid rgba(169, 185, 255, .3); border-radius: 10px; padding: 9px 14px;
            background: rgba(111, 131, 255, .12); color: #eaf0ff; font-size: 14px; font-weight: 650;
            cursor: pointer;
          }}
          #voice-play:hover {{ border-color: #9eacff; background: rgba(111, 131, 255, .23); }}
          #voice-play[hidden] {{ display: none; }}
          #voice-status {{ margin-left: 8px; color: #a4b1cc; font-size: 12px; }}
        </style>
        <script>
          const button = document.getElementById("voice-play");
          const status = document.getElementById("voice-status");
          button.textContent = {encoded_label};
          const autoPlay = {json.dumps(auto_play)};
          let speechStarted = false;
          let speechFinished = false;
          if (autoPlay) button.hidden = true;
          const playVoice = () => {{
            if (!("speechSynthesis" in window) ||
                !("SpeechSynthesisUtterance" in window)) {{
              status.textContent = "Speech playback is not supported in this browser.";
              button.hidden = false;
              return false;
            }}
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance({encoded_text});
            utterance.lang = "en-US";
            const voices = window.speechSynthesis.getVoices();
            utterance.voice = voices.find((voice) => voice.lang === "en-US") || null;
            utterance.onstart = () => {{
              speechStarted = true;
              button.hidden = true;
              status.textContent = "Speaking…";
            }};
            utterance.onend = () => {{
              speechFinished = true;
              button.hidden = true;
              status.textContent = "";
            }};
            utterance.onerror = () => {{
              status.textContent = "If you didn't hear it, use the button to replay.";
              button.hidden = false;
            }};
            try {{
              window.speechSynthesis.speak(utterance);
            }} catch (error) {{
              status.textContent = "Speech could not start. Use the button to try again.";
              button.hidden = false;
              return false;
            }}
            return true;
          }};
          button.addEventListener("click", playVoice);
          if (autoPlay) {{
            window.setTimeout(() => {{
              if (!playVoice()) {{
                status.textContent = "Use the button to hear the welcome.";
              }}
            }}, 250);
            window.setTimeout(() => {{
              if (!speechStarted && !speechFinished &&
                  !window.speechSynthesis.speaking &&
                  !window.speechSynthesis.pending) {{
                button.hidden = false;
                status.textContent = "Autoplay may be blocked. Use the button to hear the welcome.";
              }}
            }}, 2500);
          }}
        </script>
        """,
        height=54,
    )

# ----own core code ⏫

def record_audio(duration: int = None, audio_filename: str = None) -> str:
    """
    Records audio from the microphone/user and saves it as a WAV file.
    This function captures what the user speaks and stores it for later processing.
    
    Args:
        duration: Duration of recording in seconds. Uses RECORDING_DURATION_SECONDS from config if not specified.
        audio_filename: Name of the audio file to save. Uses TEMP_AUDIO_FILENAME from config if not specified.
    
    Returns:
        str: Path to the saved audio file. Returns None if recording fails.
    """
    if duration is None:
        duration = RECORDING_DURATION_SECONDS
    
    if audio_filename is None:
        audio_filename = TEMP_AUDIO_FILENAME
    
    # Create directory for storing audio files if it doesn't exist
    audio_dir = os.path.dirname(audio_filename)
    if audio_dir and not os.path.exists(audio_dir):
        os.makedirs(audio_dir, exist_ok=True)
    
    try:
        print(f"\n🎤 Recording started... Speak now (Duration: {duration} seconds)")
        
        # Record audio from microphone
        audio_frames = sd.rec(
            int(duration * RECORDING_SAMPLE_RATE),
            samplerate=RECORDING_SAMPLE_RATE,
            channels=RECORDING_CHANNELS,
            dtype='float32'
        )
        
        # Wait until recording is complete
        sd.wait()
        
        # Save the recorded audio to a file
        sf.write(audio_filename, audio_frames, RECORDING_SAMPLE_RATE)
        print(f"✓ Recording saved successfully to: {audio_filename}\n")
        
        return audio_filename
        
    except Exception as e:
        print(f"✗ Error during recording: {e}\n")
        return None


def transcribe_audio(audio_file: str) -> str:
    """
    Converts recorded audio file to text format using Google Speech Recognition.
    Takes the audio recorded by record_audio() and converts it to readable text.
    
    Args:
        audio_file: Path to the audio file that needs to be transcribed.
    
    Returns:
        str: Transcribed text from the audio file. Returns empty string if transcription fails.
    """
    try:
        # Check if audio file exists
        if not os.path.exists(audio_file):
            print(f"✗ Audio file not found: {audio_file}")
            return ""
        
        print(f"\n📝 Transcribing audio to text...")
        
        # Load the audio file
        with sr.AudioFile(audio_file) as source:
            # Record audio data from the file
            audio_data = r.record(source)
        
        # Use Google Speech Recognition to convert audio to text
        transcribed_text = r.recognize_google(audio_data)
        print(f"✓ Transcription completed successfully\n")
        
        return transcribed_text
        
    except sr.UnknownValueError:
        print("✗ Transcription failed: Could not understand the audio. Please speak clearly.")
        return ""
    except sr.RequestError as e:
        print(f"✗ Transcription error: {e}")
        return ""
    except Exception as e:
        print(f"✗ Error during transcription: {e}")
        return ""

        