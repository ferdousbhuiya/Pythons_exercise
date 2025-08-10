import tkinter as tk
from tkinter import messagebox
import requests
import datetime
import time
import schedule
import threading
from playsound import playsound

# 🎧 Default audio files
DEFAULT_ADHAN = "adhan.mp3"
DEFAULT_FAJR_ADHAN = "fajr_adhan.mp3"

class AdhanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🕌 Adhan Scheduler")
        self.root.geometry("450x400")
        self.root.configure(bg="#f0f4f7")

        title = tk.Label(root, text="🕌 Adhan Scheduler", font=("Helvetica", 18, "bold"), bg="#f0f4f7", fg="#2c3e50")
        title.pack(pady=10)

        # 🌍 Location Frame
        location_frame = tk.LabelFrame(root, text="🌍 Location Settings", bg="#e8f6f3", fg="#117864", padx=10, pady=10)
        location_frame.pack(padx=10, pady=5, fill="x")

        self.city_entry = self._add_labeled_entry(location_frame, "🏙️ City:", "Coral Springs")
        self.country_entry = self._add_labeled_entry(location_frame, "🌐 Country:", "United States")

        # 🧮 Method Frame
        method_frame = tk.LabelFrame(root, text="🧮 Calculation Method", bg="#fef9e7", fg="#b7950b", padx=10, pady=10)
        method_frame.pack(padx=10, pady=5, fill="x")

        self.method_entry = self._add_labeled_entry(method_frame, "📐 Method (0–12):", "2")

        # 🎧 Audio Frame
        audio_frame = tk.LabelFrame(root, text="🎧 Adhan Audio Files", bg="#f9ebea", fg="#943126", padx=10, pady=10)
        audio_frame.pack(padx=10, pady=5, fill="x")

        self.adhan_entry = self._add_labeled_entry(audio_frame, "🔊 Standard Adhan:", DEFAULT_ADHAN)
        self.fajr_entry = self._add_labeled_entry(audio_frame, "🌅 Fajr Adhan:", DEFAULT_FAJR_ADHAN)

        # 🚀 Start Button
        start_btn = tk.Button(root, text="✅ Start Scheduler", font=("Helvetica", 12, "bold"), bg="#58d68d", fg="white", command=self.start_scheduler)
        start_btn.pack(pady=15)

        # 🔄 Status Label
        self.status_label = tk.Label(root, text="", bg="#f0f4f7", fg="#34495e", font=("Helvetica", 10))
        self.status_label.pack()

    def _add_labeled_entry(self, parent, label_text, default_value):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.pack(fill="x", pady=2)
        label = tk.Label(frame, text=label_text, width=18, anchor="w", bg=parent["bg"], fg="#2c3e50")
        label.pack(side="left")
        entry = tk.Entry(frame, width=25)
        entry.insert(0, default_value)
        entry.pack(side="left")
        return entry

    def start_scheduler(self):
        city = self.city_entry.get().strip()
        country = self.country_entry.get().strip()
        method = self.method_entry.get().strip()
        adhan_file = self.adhan_entry.get().strip()
        fajr_file = self.fajr_entry.get().strip()

        if not city or not country or not method.isdigit():
            messagebox.showerror("Input Error", "Please enter valid city, country, and method.")
            return

        try:
            method = int(method)
            prayer_times = self.get_prayer_times(city, country, method)
            self.schedule_adhan(prayer_times, adhan_file, fajr_file)
            self.status_label.config(text="✅ Scheduler started successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start scheduler:\n{e}")
            self.status_label.config(text="❌ Scheduler failed.")

    def get_prayer_times(self, city, country, method):
        today = datetime.date.today()
        url = f"https://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method={method}&date={today}"
        response = requests.get(url)
        data = response.json()["data"]["timings"]
        return {
            "Fajr": data["Fajr"],
            "Dhuhr": data["Dhuhr"],
            "Asr": data["Asr"],
            "Maghrib": data["Maghrib"],
            "Isha": data["Isha"]
        }

    def schedule_adhan(self, prayer_times, adhan_file, fajr_file):
        for prayer, time_str in prayer_times.items():
            hour, minute = map(int, time_str.split(":"))
            schedule_time = datetime.time(hour, minute).strftime("%H:%M")
            schedule.every().day.at(schedule_time).do(self.play_adhan, prayer, adhan_file, fajr_file)

        threading.Thread(target=self.run_scheduler, daemon=True).start()

    def play_adhan(self, prayer_name, adhan_file, fajr_file):
        print(f"🔔 {prayer_name} time!")
        if prayer_name == "Fajr":
            playsound(fajr_file)
        else:
            playsound(adhan_file)

    def run_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(30)

# 🏁 Launch the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = AdhanApp(root)
    root.mainloop()