# voz.py
# Módulo de reconocimiento de voz (ASR)
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
import tempfile

def escuchar_comando():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Habla ahora...")
        audio = r.listen(source, phrase_time_limit=6)
    try:
        texto = r.recognize_google(audio, language='es-ES')
        print(f"Transcripción: {texto}")
        tts = gTTS(text=f"Dijiste: {texto}", lang='es', slow=False)
        tmp_mp3 = tempfile.mktemp(suffix='.mp3')
        tts.save(tmp_mp3)
        playsound(tmp_mp3)
        return texto
    except Exception as e:
        print(f"[ERROR] No se pudo transcribir el audio: {e}")
        return None

# Escucha continuamente hasta captar un comando válido
def escuchar_comando_continuo():
    print("(Micrófono activo, di un comando...)")
    while True:
        texto = escuchar_comando()
        if texto:
            return texto
