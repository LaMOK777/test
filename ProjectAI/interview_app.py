import os
import threading
import time
import customtkinter as ctk
import sounddevice as sd
import numpy as np
import wave
import tempfile
import ollama
import pyttsx3
from faster_whisper import WhisperModel
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
WHISPER_SIZE = "small"
DEFAULT_MODEL = "qwen2.5:1.5b"
MAX_HISTORY = 6

print("⏳ Загрузка моделей...")
whisper_model = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 160)
tts_engine.setProperty('volume', 1.0)
for voice in tts_engine.getProperty('voices'):
    if 'russian' in voice.name.lower() or 'ru' in voice.id.lower():
        tts_engine.setProperty('voice', voice.id)
        break

history = [
    {"role": "system", "content": (
        "Ты — опытный HR-интервьюер. Проводишь собеседование на позицию Junior Python Developer. "
        "Задавай по одному вопросу, жди ответа, давай фидбек. Говори кратко, на русском."
    )}
]

class OfflineInterviewApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎙️ AI Interviewer Pro")
        self.geometry("650x520")
        self.is_running = False
        self.is_busy = False

        self.status_label = ctk.CTkLabel(self, text="🟢 Готово", text_color="orange", font=("Arial", 12))
        self.status_label.pack(pady=5)

        self.log_box = ctk.CTkTextbox(self, width=600, height=300, font=("Consolas", 12), state="disabled")
        self.log_box.pack(pady=5, padx=20, fill="both", expand=True)

        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame.pack(pady=10, fill="x", padx=20)

        self.model_var = ctk.StringVar(value=DEFAULT_MODEL)
        self.model_menu = ctk.CTkOptionMenu(self.ctrl_frame, variable=self.model_var, values=[
            "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b"
        ], width=160)
        self.model_menu.pack(side="left", padx=5)

        self.btn = ctk.CTkButton(self.ctrl_frame, text="▶ Начать", command=self.toggle, fg_color="#2ecc71", width=120)
        self.btn.pack(side="left", padx=5)

        self.save_btn = ctk.CTkButton(self.ctrl_frame, text="💾 Сохранить", command=self.save_conversation, fg_color="#3498db", width=120)
        self.save_btn.pack(side="left", padx=5)

        self.volume_bar = ctk.CTkProgressBar(self.ctrl_frame, width=180, mode="determinate")
        self.volume_bar.pack(side="right", padx=5)
        self.volume_bar.set(0)

        self.after(100, self.update_volume_indicator)

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def toggle(self):
        if not self.is_running:
            if not self.check_ollama(): 
                return
            self.is_running = True
            self.btn.configure(text="⏹ Стоп", fg_color="#e74c3c")
            self.status_label.configure(text="🎤 Говорите...", text_color="orange")
            threading.Thread(target=self.loop, daemon=True).start()
        else:
            self.is_running = False
            self.btn.configure(text="▶ Начать", fg_color="#2ecc71")
            self.status_label.configure(text="⏹ Остановлено", text_color="gray")

    def check_ollama(self):
        try:
            ollama.list()
            self.status_label.configure(text="🟢 Ollama активен", text_color="green")
            return True
        except Exception as e:
            self.status_label.configure(text="❌ Ollama не запущен!", text_color="red")
            self.log(f"⚠️ Ошибка: {e}")
            return False

    def update_volume_indicator(self):
        if self.is_running and not self.is_busy:
            try:
                chunk = sd.rec(int(0.15 * 16000), samplerate=16000, channels=1, dtype='int16')
                sd.wait()
                vol = np.abs(chunk).mean() / 32768.0
                self.volume_bar.set(vol)
            except: 
                pass
        else:
            self.volume_bar.set(0)
        self.after(200, self.update_volume_indicator)

    def loop(self):
        while self.is_running and not self.is_busy:
            self.is_busy = True
            try:
                self.status_label.configure(text="🎤 Запись...", text_color="orange")
                fs = 16000
                recording = sd.rec(int(10 * fs), samplerate=fs, channels=1, dtype='int16')
                sd.wait()

                self.status_label.configure(text="🔄 Распознаю...", text_color="yellow")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(fs)
                    wf.writeframes(recording.tobytes())

                segments, _ = whisper_model.transcribe(temp_path, beam_size=5, language="ru")
                text = " ".join([seg.text for seg in segments]).strip()
                os.remove(temp_path)

                if text and self.is_running:
                    self.after(0, self.log, f"👤 Вы: {text}")
                    self.get_and_speak(text)
            except Exception as e:
                self.after(0, self.log, f"❌ Ошибка: {e}")
            finally:
                self.is_busy = False
            time.sleep(0.3)

    def get_and_speak(self, user_text):
        history.append({"role": "user", "content": user_text})
        if len(history) > MAX_HISTORY + 1:
            history.pop(1)

        self.status_label.configure(text="🤖 ИИ думает...", text_color="cyan")
        try:
            response = ollama.chat(
                model=self.model_var.get(),
                messages=history,
                options={'temperature': 0.5, 'num_predict': 150, 'num_ctx': 2048}
            )
            ai_text = response['message']['content']
            history.append({"role": "assistant", "content": ai_text})

            self.after(0, self.log, f"🤖 ИИ: {ai_text}")
            self.speak(ai_text)
        except Exception as e:
            self.after(0, self.log, f"❌ Ошибка ИИ: {e}")
            self.status_label.configure(text="❌ Ошибка ИИ", text_color="red")

    def speak(self, text):
        self.status_label.configure(text="🔊 ИИ говорит...", text_color="magenta")
        def run_tts():
            tts_engine.say(text)
            tts_engine.runAndWait()
            if self.is_running:
                self.status_label.configure(text="🎤 Говорите...", text_color="orange")
        threading.Thread(target=run_tts, daemon=True).start()

    def save_conversation(self):
        filename = f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                f.write(f"🤖 Модель: {self.model_var.get()}\n")
                f.write("=" * 50 + "\n")
                for msg in history:
                    if msg['role'] == 'user':
                        f.write(f"👤 Вы: {msg['content']}\n\n")
                    elif msg['role'] == 'assistant':
                        f.write(f"🤖 ИИ: {msg['content']}\n\n")
            self.log(f"💾 Сохранено в {filename}")
        except Exception as e:
            self.log(f"❌ Ошибка сохранения: {e}")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    OfflineInterviewApp().mainloop()