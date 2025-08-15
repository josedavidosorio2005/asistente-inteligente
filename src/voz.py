# voz.py
# Módulo de reconocimiento de voz (ASR)
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
import tempfile

def escuchar_comando(max_reintentos=3):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Calibrando micrófono, por favor guarda silencio...")
        r.adjust_for_ambient_noise(source, duration=1.5)
        print(f"Nivel de ruido detectado: {r.energy_threshold:.2f}")
        for intento in range(max_reintentos):
            print("Habla ahora...")
            try:
                audio = r.listen(source, phrase_time_limit=10)
                print("Procesando...")
                texto = r.recognize_google(audio, language='es-ES')
                print(f"Transcripción: {texto}")
                return texto
            except sr.UnknownValueError:
                print("No se entendió, intenta de nuevo...")
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

# Función para hablar cualquier texto (respuesta profesional)
def hablar(texto):
    try:
        tts = gTTS(text=texto, lang='es', slow=False)
        tmp_mp3 = tempfile.mktemp(suffix='.mp3')
        tts.save(tmp_mp3)
        playsound(tmp_mp3)
    except Exception as e:
        print(f"[ERROR] No se pudo reproducir el audio: {e}")
