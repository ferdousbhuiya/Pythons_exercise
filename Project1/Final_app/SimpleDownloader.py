import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import yt_dlp
import re
import datetime
import logging

class SimpleDownloader:
    def __init__(self, master):
        self.master = master
        self.master.title("Simple Video Downloader")
        self.master.geometry("500x400")
        self.master.resizable(True, True)
        self.master.configure(bg="#2E2E2E")

        self.url = tk.StringVar()
        self.download_in_progress = False
        self.output_path = tk.StringVar(value=os.getcwd())
        self.selected_quality = tk.StringVar(value="best")

        self.setup_logging()
        self.create_widgets()

    def setup_logging(self):
        log_file = os.path.join(os.path.dirname(__file__), 'download_log.txt')
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def create_widgets(self):
        # Configure styles
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("TLabel", background="#2E2E2E", foreground="white")
        style.configure("TButton", background="#4CAF50", foreground="white")
        style.map("TButton", background=[('active', '#45a049')])
        style.configure("TEntry", fieldbackground="#3E3E3E", foreground="white")
        style.configure("TCombobox", fieldbackground="#3E3E3E", foreground="white")
        style.configure("TProgressbar", troughcolor="#3E3E3E", background="#4CAF50")

        # Main frame
        main_frame = ttk.Frame(self.master)
        main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Simple Video Downloader", 
                               foreground="#4CAF50")
        title_label.pack(pady=(0, 20))

        # URL input
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill="x", pady=10)

        ttk.Label(url_frame, text="Paste video URL:").pack(anchor="w")
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url)
        self.url_entry.pack(fill="x", pady=(5, 10))
        self.url_entry.bind('<Return>', lambda e: self.start_download())

        # Quality selection
        quality_frame = ttk.Frame(main_frame)
        quality_frame.pack(fill="x", pady=10)

        ttk.Label(quality_frame, text="Quality:").pack(anchor="w")
        self.quality_combo = ttk.Combobox(quality_frame, textvariable=self.selected_quality, 
                                         values=["best", "worst", "audio"], state="readonly")
        self.quality_combo.pack(fill="x", pady=(5, 10))
        self.quality_combo.set("best")

        # Download location
        location_frame = ttk.Frame(main_frame)
        location_frame.pack(fill="x", pady=10)

        ttk.Label(location_frame, text="Download Location:").pack(anchor="w")
        location_button_frame = ttk.Frame(location_frame)
        location_button_frame.pack(fill="x", pady=(5, 10))

        ttk.Button(location_button_frame, text="Choose Folder", 
                  command=self.choose_directory).pack(side="left")
        ttk.Label(location_button_frame, textvariable=self.output_path, 
                 wraplength=300, justify="left").pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Action button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=20)

        self.download_button = ttk.Button(button_frame, text="Download Video", 
                                        command=self.start_download)
        self.download_button.pack(fill="x", pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.progress.pack(fill="x", pady=10)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to download", 
                                     foreground="#888888")
        self.status_label.pack(pady=5)

        # Info text
        info_text = """
Supported: YouTube, TikTok, Instagram, Twitter, Reddit, Vimeo, Dailymotion, and more!

Note: Some Facebook videos may not work due to restrictions.
        """
        info_label = ttk.Label(main_frame, text=info_text, foreground="#CCCCCC")
        info_label.pack(pady=20)

    def choose_directory(self):
        path = filedialog.askdirectory(parent=self.master)
        if path:
            self.output_path.set(path)

    def update_status(self, message):
        self.master.after(0, lambda: self.status_label.config(text=message))

    def start_download(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a video URL.")
            return
        
        if self.download_in_progress:
            messagebox.showinfo("Please Wait", "A download is in progress, please wait.")
            return

        if not self.output_path.get():
            messagebox.showerror("Error", "Please choose a download location first.")
            return

        self.download_in_progress = True
        self.download_button.config(state=tk.DISABLED)
        self.update_status("Starting download...")
        self.progress['value'] = 0

        threading.Thread(target=self._download_video, args=(url,), daemon=True).start()

    def _download_video(self, url):
        try:
            # Sanitize filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"video_{timestamp}"

            ydl_opts = {
                'progress_hooks': [self.update_progress],
                'outtmpl': os.path.join(self.output_path.get(), f'{filename}.%(ext)s'),
                'restrictfilenames': True,
                'retries': 5,
                'fragment_retries': 5,
                'extractor_retries': 3,
                'no_warnings': True,
                'quiet': True,
                'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
            }

            # Set quality
            quality = self.selected_quality.get()
            if quality == "audio":
                ydl_opts['format'] = "bestaudio/best"
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                ydl_opts['extract_audio'] = True
            elif quality == "worst":
                ydl_opts['format'] = "worstvideo+worstaudio/worst"
                ydl_opts['merge_output_format'] = 'mp4'
            else:  # "best"
                ydl_opts['format'] = "best[height<=1080]/bestvideo[height<=1080]+bestaudio/best"
                ydl_opts['merge_output_format'] = 'mp4'

            # Add ffmpeg path if available
            ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')
            if os.path.exists(ffmpeg_path):
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logging.info(f"Starting download for URL: {url}")
                ydl.download([url])
                logging.info(f"Download completed for URL: {url}")

            self.master.after(0, lambda: self.update_status("Download complete!"))
            self.master.after(0, lambda: messagebox.showinfo("Success", "Video downloaded successfully!"))

        except Exception as error:
            error_msg = f"Download failed: {str(error)}"
            self.master.after(0, lambda: self.update_status(error_msg))
            self.master.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download video:\n{str(error)}"))
            logging.error(f"Download error: {error}")
        finally:
            self.master.after(0, self.reset_download_state)

    def update_progress(self, d):
        self.master.after(0, self._update_progress_gui, d)

    def _update_progress_gui(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes:
                try:
                    percent = (downloaded_bytes / total_bytes) * 100
                    self.progress.config(mode='determinate', value=percent)
                    status_text = f"Downloading: {d.get('_percent_str', '')} at {d.get('_speed_str', 'N/A')}"
                except ZeroDivisionError:
                    self.progress.config(mode='indeterminate')
                    status_text = f"Downloading: {d.get('_percent_str', '')}"
            else:
                self.progress.config(mode='indeterminate')
                status_text = f"Downloading: {d.get('_percent_str', '')}"

            self.status_label.config(text=status_text)

        elif d['status'] == 'finished':
            self.progress['value'] = 100
            self.status_label.config(text="Processing...")

    def reset_download_state(self):
        self.download_in_progress = False
        self.progress['value'] = 0
        self.progress.config(mode='determinate')
        self.update_status("Ready to download")
        self.download_button.config(state=tk.NORMAL)

if __name__ == '__main__':
    root = tk.Tk()
    app = SimpleDownloader(root)
    root.mainloop() 