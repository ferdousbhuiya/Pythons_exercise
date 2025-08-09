# ferdous_downloader.py
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from yt_dlp import YoutubeDL
import queue
import logging

# Initialize logging
logging.basicConfig(filename="ferdous_downloader.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class VideoDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ferdous Video Downloader")
        self.root.geometry("700x400")
        self.root.configure(bg="#2e2e2e")

        self.style = ttk.Style(self.root)
        self.style.configure("TLabel", foreground="white", background="#2e2e2e")
        self.style.configure("TButton", background="#444", foreground="white")
        self.style.configure("Download.TButton", background="#4CAF50", foreground="white")

        self.url_label = ttk.Label(root, text="Enter Video URL:")
        self.url_label.pack(pady=5)

        self.url_entry = ttk.Entry(root, width=80)
        self.url_entry.pack(pady=5)

        self.platform_label = ttk.Label(root, text="Select Platform:")
        self.platform_label.pack(pady=5)

        self.platform_var = tk.StringVar()
        self.platform_combo = ttk.Combobox(root, textvariable=self.platform_var, values=["youtube", "facebook", "tiktok", "instagram"], state="readonly")
        self.platform_combo.current(0)
        self.platform_combo.pack(pady=5)

        self.quality_label = ttk.Label(root, text="Select Quality:")
        self.quality_label.pack(pady=5)

        self.quality_var = tk.StringVar()
        self.quality_combo = ttk.Combobox(root, textvariable=self.quality_var, values=["best", "worst", "bestvideo+bestaudio"], state="readonly")
        self.quality_combo.current(0)
        self.quality_combo.pack(pady=5)

        self.download_button = ttk.Button(root, text="Download", style="Download.TButton", command=self.start_download_thread)
        self.download_button.pack(pady=10)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        self.status_label = ttk.Label(root, text="", font=("Arial", 10))
        self.status_label.pack(pady=5)

        self.is_downloading = False
        self.active_button = None
        self.progress_queue = queue.Queue()
        self.check_progress_queue()

    def check_progress_queue(self):
        try:
            while True:
                msg_type, value, *extra = self.progress_queue.get_nowait()
                if msg_type == 'progress':
                    self.progress['value'] = value
                elif msg_type == 'status':
                    color = extra[0] if extra else 'lightblue'
                    self.status_label.config(text=value, foreground=color)
                    if 'finished' in value.lower() or 'success' in value.lower():
                        self.progress['value'] = 0
                        self.is_downloading = False
                        if self.active_button:
                            self.active_button.configure(style="Download.TButton")
                            self.active_button = None
                        self.url_entry.delete(0, tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.check_progress_queue)

    def start_download_thread(self):
        if self.is_downloading:
            self.status_label.config(text="One download in progress, please wait.", foreground="red")
            return

        url = self.url_entry.get()
        platform = self.platform_var.get()
        quality = self.quality_var.get()

        if not url:
            self.status_label.config(text="Please enter a valid URL.", foreground="red")
            return

        save_path = filedialog.askdirectory()
        if not save_path:
            return

        self.download_button.configure(style="TButton")
        self.is_downloading = True
        self.active_button = self.download_button
        self.status_label.config(text="Starting download...", foreground="orange")

        threading.Thread(target=self.download_video, args=(url, platform, save_path), daemon=True).start()

    def update_progress(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes:
                progress = int(downloaded_bytes / total_bytes * 100)
                self.progress_queue.put(('progress', progress))

    def download_video(self, url, platform, save_path):
        try:
            ffmpeg_path = resource_path('ffmpeg.exe')
            if not os.path.isfile(ffmpeg_path):
                ffmpeg_path = 'ffmpeg'

            ydl_opts = {
                'outtmpl': os.path.join(save_path, '%(title).100s_%(id)s.%(ext)s'),
                'progress_hooks': [self.update_progress],
                'format': self.quality_var.get(),
                'quiet': True,
                'no_warnings': True,
                'restrictfilenames': True,
                'noplaylist': False,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'ffmpeg_location': ffmpeg_path,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
            }

            with YoutubeDL(ydl_opts) as ydl:
                logging.info(f"Starting download for URL: {url}")
                info_dict = ydl.extract_info(url, download=False)
                is_playlist = 'entries' in info_dict

                if is_playlist:
                    videos = info_dict['entries']
                    total = len(videos)
                    for idx, video in enumerate(videos, 1):
                        self.progress_queue.put(('status', f"Downloading video {idx}/{total}...", 'lightblue'))
                        ydl.download([video['webpage_url']])
                else:
                    ydl.download([url])

            self.progress_queue.put(('status', f"{platform.capitalize()} download finished!", 'green'))
            self.progress_queue.put(('progress', 100))

        except Exception as e:
            logging.error(f"Download failed: {str(e)}")
            self.progress_queue.put(('status', f"Error: {str(e)}", 'red'))
            self.progress_queue.put(('progress', 0))
        finally:
            self.is_downloading = False
            self.active_button = None

if __name__ == '__main__':
    root = tk.Tk()
    app = VideoDownloaderApp(root)
    root.mainloop()
