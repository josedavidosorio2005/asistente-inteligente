# Legacy: módulo OCR sencillo (reubicado desde src/vision.py)
import mss
import numpy as np
import cv2
import requests
import tempfile
from gtts import gTTS
from playsound import playsound

def analizar_pantalla():
    print("Capturando pantalla (legacy)...")
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        cv2.imwrite(tmp.name, img)
        tmp_path = tmp.name
    with open(tmp_path, 'rb') as f:
        r = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': f},
            data={'language': 'spa', 'isOverlayRequired': False},
            headers={'apikey': 'helloworld'}
        )
    try:
        result = r.json()
        texto = result['ParsedResults'][0]['ParsedText']
        print("Texto detectado (legacy):\n", texto)
        tts = gTTS(text=texto, lang='es', slow=False)
        tmp_mp3 = tempfile.mktemp(suffix='.mp3')
        tts.save(tmp_mp3)
        playsound(tmp_mp3)
    except Exception as e:
        print(f"[ERROR] Legacy vision: {e}")
