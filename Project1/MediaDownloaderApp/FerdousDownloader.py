import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL
import os
import re
import urllib.request
from PIL import Image, ImageTk
from io import BytesIO
import threading
import queue
import logging
import sys

# -- Helper to detect if running in PyInstaller bundle --
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Ferdous Video Downloader")
        self.root.geometry("550x520")
        self.root.configure(bg="#2E2E2E")  # Dark background

        # Set up logging
        self.setup_logging()

        # Threading queue for progress updates
        self.progress_queue = queue.Queue()
        self.is_downloading = False
        self.active_button = None
        self.thumbnail_photo = None  # Keep reference to avoid GC

        # Style: Dark Mode
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", foreground="white", background="#2E2E2E", font=("Helvetica", 11))
        style.configure("TButton", font=("Helvetica", 10), background="#444444", foreground="white", padding=5)
        style.map("TButton", background=[('active', '#666666')])
        style.configure("Download.TButton", background="#4CAF50", foreground="white")
        style.map("Download.TButton", background=[("active", "#81C784")])
        style.configure("Active.TButton", background="#B0BEC5", foreground="black")
        style.configure("Action.TButton", background="#2196F3", foreground="white")
        style.map("Action.TButton", background=[("active", "#1976D2")])
        style.configure("TProgressbar", troughcolor="#555555", background="#9C27B0")

        # UI Elements

        # URL Entry
        ttk.Label(root, text="Video or Playlist URL (Facebook, YouTube, TikTok, Instagram):", style="TLabel").pack(pady=(10, 2))
        self.url_entry = ttk.Entry(root, width=60, font=("Helvetica", 11))
        self.url_entry.pack(pady=5)

        # Thumbnail Preview Label
        self.thumbnail_label = ttk.Label(root, text="Thumbnail will appear here", style="TLabel")
        self.thumbnail_label.pack(pady=5)

        # Quality Options
        ttk.Label(root, text="Quality:", style="TLabel").pack(pady=(10, 2))
        self.quality_var = tk.StringVar(value="best")
        quality_frame = ttk.Frame(root)
        quality_frame.pack()
        ttk.Radiobutton(quality_frame, text="Highest", variable=self.quality_var, value="bestvideo+bestaudio/best", style="TButton").pack(side="left", padx=8)
        ttk.Radiobutton(quality_frame, text="Medium (720p)", variable=self.quality_var, value="bestvideo[height<=720]+bestaudio/best", style="TButton").pack(side="left", padx=8)
        ttk.Radiobutton(quality_frame, text="Lowest", variable=self.quality_var, value="worst", style="TButton").pack(side="left", padx=8)

        # Save Location
        ttk.Label(root, text="Save To:", style="TLabel").pack(pady=(10, 2))
        location_frame = ttk.Frame(root)
        location_frame.pack(pady=5)
        self.location_entry = ttk.Entry(location_frame, width=45, font=("Helvetica", 11))
        self.location_entry.pack(side="left", padx=(0, 5))
        default_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.location_entry.insert(0, default_path)
        ttk.Button(location_frame, text="Browse", command=self.browse_location, style="Action.TButton").pack(side="left")

        # Action Buttons
        buttons_frame = ttk.Frame(root)
        buttons_frame.pack(pady=15)
        ttk.Button(buttons_frame, text="Analyze URL", command=self.analyze_url, style="Action.TButton").pack(side="left", padx=10)
        ttk.Button(buttons_frame, text="Download Video", command=self.download_single_video, style="Action.TButton").pack(side="left", padx=10)

        # Status Label
        self.status_label = ttk.Label(root, text="", foreground="lightblue", style="TLabel")
        self.status_label.pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate", style="TProgressbar")
        self.progress.pack(pady=10)

        # Start polling for progress updates
        self.check_progress_queue()

    def setup_logging(self):
        log_file = os.path.join(os.path.abspath("."), 'download_log.txt')
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def browse_location(self):
        folder = filedialog.askdirectory()
        if folder:
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, folder)

    def update_progress(self, d):
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '0%')
                clean_percent = re.sub(r'\x1b\[[0-9;]*[mK]', '', percent_str).replace('%', '')
                percent = float(clean_percent)
                self.progress_queue.put(('progress', percent))
            except Exception:
                self.progress_queue.put(('progress', min(self.progress['value'] + 1, 100)))
        elif d['status'] == 'finished':
            self.progress_queue.put(('progress', 100))
            self.progress_queue.put(('status', 'Download complete!', 'green'))

    def check_progress_queue(self):
        try:
            while True:
                msg_type, value, *extra = self.progress_queue.get_nowait()
                if msg_type == 'progress':
                    self.progress['value'] = value
                elif msg_type == 'status':
                    color = extra[0] if extra else 'lightblue'
                    self.status_label.config(text=value, foreground=color)
                    if value == 'Download complete!' and self.active_button:
                        self.active_button.configure(style="Download.TButton")
                        self.active_button = None
                self.root.update_idletasks()
        except queue.Empty:
            pass
        self.root.after(100, self.check_progress_queue)

    def validate_url(self, url):
        url = url.strip()
        # Patterns for supported platforms
        youtube_patterns = [
            r'youtube\.com/watch\?v=[\w-]+',
            r'youtu\.be/[\w-]+',
            r'youtube\.com/shorts/[\w-]+',
            r'youtube\.com/playlist\?list=[\w-]+',
            r'youtube\.com.*list=[\w-]+'
        ]
        tiktok_patterns = [r'tiktok\.com/@[\w.-]+/video/\d+']
        instagram_patterns = [r'instagram\.com/(reel|p)/[\w-]+']
        facebook_patterns = [
            r'v=(\d+)',
            r'videos/(\d+)',
            r'watch/\?v=(\d+)',
            r'reel/(\d+)',
            r'/(\d+)/?$'
        ]

        # Check YouTube
        if any(re.search(p, url) for p in youtube_patterns):
            return url, "youtube"
        # Check TikTok
        if any(re.search(p, url) for p in tiktok_patterns):
            return url, "tiktok"
        # Check Instagram
        if any(re.search(p, url) for p in instagram_patterns):
            return url, "instagram"
        # Check Facebook
        url = url.replace('m.facebook.com', 'www.facebook.com')
        for pattern in facebook_patterns:
            match = re.search(pattern, url)
            if match:
                return f"https://www.facebook.com/watch/?v={match.group(1)}", "facebook"
        return None, None

    def fetch_thumbnail(self, url):
        try:
            with urllib.request.urlopen(url) as response:
                img_data = response.read()
            img = Image.open(BytesIO(img_data))
            img = img.resize((160, 90), Image.Resampling.LANCZOS)
            self.thumbnail_photo = ImageTk.PhotoImage(img)
            return self.thumbnail_photo
        except Exception:
            return None

    def analyze_url(self):
        if self.is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait.")
            return

        raw_url = self.url_entry.get().strip()
        save_path = self.location_entry.get().strip()

        if not raw_url:
            self.status_label.config(text="Error: No URL provided", foreground="red")
            messagebox.showerror("Error", "Please enter a video or playlist URL")
            return

        if not save_path or not os.path.isdir(save_path):
            self.status_label.config(text="Error: Invalid save location", foreground="red")
            messagebox.showerror("Error", "Please select a valid download location")
            return

        try:
            self.status_label.config(text="Analyzing URL...", foreground="lightblue")
            working_url, platform = self.validate_url(raw_url)
            if not working_url:
                raise ValueError(
                    "Invalid or unsupported video URL.\nSupported: YouTube, Facebook, TikTok, Instagram."
                )

            # Fetch thumbnail preview if possible
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(working_url, download=False)
            thumb_url = info.get('thumbnail')
            if thumb_url:
                photo = self.fetch_thumbnail(thumb_url)
                if photo:
                    self.thumbnail_label.config(image=photo, text="")

            self.status_label.config(text=f"Ready to download from {platform.capitalize()}", foreground="lightblue")

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def start_download_thread(self, url, platform, save_path, button):
        if self.is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait.")
            return

        self.is_downloading = True
        self.active_button = button
        if button:
            button.configure(style="Active.TButton")

        self.status_label.config(text=f"Starting {platform.capitalize()} download...", foreground="lightblue")
        self.progress['value'] = 0

        thread = threading.Thread(target=self.download_video, args=(url, platform, save_path))
        thread.daemon = True
        thread.start()

    def download_single_video(self):
        if self.is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait.")
            return

        raw_url = self.url_entry.get().strip()
        save_path = self.location_entry.get().strip()

        if not raw_url:
            self.status_label.config(text="Error: No URL provided", foreground="red")
            messagebox.showerror("Error", "Please enter a video URL")
            return

        if not save_path or not os.path.isdir(save_path):
            self.status_label.config(text="Error: Invalid save location", foreground="red")
            messagebox.showerror("Error", "Please select a valid download location")
            return

        try:
            working_url, platform = self.validate_url(raw_url)
            if not working_url:
                raise ValueError("Invalid or unsupported video URL")
            self.start_download_thread(working_url, platform, save_path, None)
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def download_video(self, url, platform, save_path):
        try:
            ffmpeg_path = resource_path('ffmpeg.exe')
            if not os.path.isfile(ffmpeg_path):
                ffmpeg_path = 'ffmpeg'  # fallback to system path

            ydl_opts = {
                'outtmpl': os.path.join(save_path, '%(title).100s_%(id)s.%(ext)s'),
                'progress_hooks': [self.update_progress],
                'format': self.quality_var.get(),
                'quiet': True,
                'no_warnings': True,
                'restrictfilenames': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                  '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'ffmpeg_location': ffmpeg_path,
                'verbose': True,
            }

            if platform == "facebook":
                ydl_opts['extractor_args'] = {'facebook': {'skip_dash_manifest': True}}
                ydl_opts['http_headers']['Referer'] = 'https://www.facebook.com/'
                cookie_file = resource_path('cookies.txt')
                if os.path.exists(cookie_file):
                    ydl_opts['cookiefile'] = cookie_file
                else:
                    logging.warning("No cookies.txt found; Facebook download may fail if authentication is required.")

            with YoutubeDL(ydl_opts) as ydl:
                logging.info(f"Starting download for URL: {url}")
                ydl.download([url])
                logging.info("Download completed successfully")

            self.progress_queue.put(('status', f"{platform.capitalize()} video downloaded successfully!", 'green'))
            self.progress_queue.put(('progress', 100))

        except Exception as e:
            logging.error(f"Download failed: {str(e)}")
            self.progress_queue.put(('status', f"Error: {str(e)}", 'red'))
            self.progress_queue.put(('progress', 0))
        finally:
            self.is_downloading = False


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()
