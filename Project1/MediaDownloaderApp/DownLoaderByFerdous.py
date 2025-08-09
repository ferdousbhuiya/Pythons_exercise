
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

class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook & YouTube Video Downloader (Updated July 2025)")
        self.root.geometry("500x450")

        # Set up logging
        self.app_dir = os.path.abspath(os.path.dirname(__file__) if '__file__' in globals() else os.getcwd())
        self.setup_logging()

        # Threading queue for progress updates
        self.progress_queue = queue.Queue()
        self.is_downloading = False
        self.active_button = None

        # Apply colorful theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=5, font=("Helvetica", 10), foreground="black", background="#FFFFFF")
        style.configure("Download.TButton", background="#4CAF50", foreground="white")
        style.configure("Active.TButton", background="#B0BEC5", foreground="black")
        style.configure("Action.TButton", background="#2196F3", foreground="white")
        style.map("Download.TButton", background=[("active", "#81C784")])
        style.map("Active.TButton", background=[("active", "#CFD8DC")])
        style.configure("TLabel", font=("Helvetica", 10), foreground="#333333")
        style.configure("TProgressbar", troughcolor="#BBDEFB", background="#9C27B0")
        style.configure("TRadiobutton", background="#E3F2FD", font=("Helvetica", 10))
        self.root.configure(bg="#E3F2FD")

        # URL Entry
        ttk.Label(root, text="Video or Playlist URL (Facebook or YouTube):", style="TLabel").pack(pady=10)
        self.url_entry = ttk.Entry(root, width=50, font=("Helvetica", 10))
        self.url_entry.pack(pady=5)
        ttk.Label(
            root,
            text="Examples:\nFacebook: https://www.facebook.com/watch?v=123456789\nYouTube: https://www.youtube.com/watch?v=abc123\nPlaylist: https://www.youtube.com/playlist?list=PL...",
            justify="center",
            style="TLabel",
            foreground="#1976D2"
        ).pack(pady=5)

        # Quality Options
        ttk.Label(root, text="Quality:", style="TLabel").pack(pady=5)
        self.quality_var = tk.StringVar(value="best")
        ttk.Radiobutton(root, text="Highest", variable=self.quality_var, value="bestvideo+bestaudio/best", style="TRadiobutton").pack()
        ttk.Radiobutton(root, text="Medium", variable=self.quality_var, value="bestvideo[height<=720]+bestaudio/best", style="TRadiobutton").pack()
        ttk.Radiobutton(root, text="Lowest", variable=self.quality_var, value="worst", style="TRadiobutton").pack()

        # Save Location
        ttk.Label(root, text="Save To:", style="TLabel").pack(pady=5)
        self.location_entry = ttk.Entry(root, width=40, font=("Helvetica", 10))
        self.location_entry.pack(pady=5)
        self.location_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Button(root, text="Browse", command=self.browse_location, style="Action.TButton").pack(pady=5)

        # Action Buttons
        ttk.Button(root, text="Analyze URL", command=lambda: threading.Thread(target=self.analyze_url).start(), style="Action.TButton").pack(pady=10)
        ttk.Button(root, text="Download Video", command=self.download_single_video, style="Action.TButton").pack(pady=5)

        # Status Label
        self.status_label = ttk.Label(root, text="", foreground="blue", style="TLabel")
        self.status_label.pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", style="TProgressbar")
        self.progress.pack(pady=10)

        # Start polling for progress updates
        self.check_progress_queue()

    def setup_logging(self):
        log_file = os.path.join(self.app_dir, 'download_log.txt')
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
            except (ValueError, AttributeError):
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
                    color = extra[0] if extra else 'blue'
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
        if "facebook.com/watch/?" in url:
            return url, "facebook"

        youtube_patterns = [
            r'youtube\.com/watch\?v=[\w-]+',
            r'youtu\.be/[\w-]+',
            r'youtube\.com/shorts/[\w-]+',
            r'youtube\.com/playlist\?list=[\w-]+',
            r'youtube\.com.*list=[\w-]+'
        ]
        if any(re.search(pattern, url) for pattern in youtube_patterns):
            return url, "youtube"

        url = url.replace('m.facebook.com', 'www.facebook.com')
        facebook_patterns = [
            r'v=(\d+)',
            r'videos/(\d+)',
            r'watch/\?v=(\d+)',
            r'reel/(\d+)',
            r'/(\d+)/?$'
        ]
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
            img = img.resize((100, 56), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
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
            self.status_label.config(text="Analyzing URL...", foreground="blue")
            working_url, platform = self.validate_url(raw_url)
            if not working_url:
                raise ValueError("Invalid video or playlist URL")

            if platform == "youtube":
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,
                    'age_limit': 99,
                    'http_headers': {
                        'User-Agent': (
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                            '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
                        ),
                        'Accept-Language': 'en-US,en;q=0.9',
                    }
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(working_url, download=False)

                if 'entries' in info:
                    self.show_playlist_videos(info['entries'], save_path)
                    self.status_label.config(text="Playlist loaded, select videos to download", foreground="blue")
                else:
                    self.start_download_thread(working_url, platform, save_path, None)
            else:
                self.start_download_thread(working_url, platform, save_path, None)

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def show_playlist_videos(self, videos, save_path):
        playlist_window = tk.Toplevel(self.root)
        playlist_window.title("Select Videos to Download")
        playlist_window.geometry("600x400")
        playlist_window.configure(bg="#E8F5E9")

        canvas = tk.Canvas(playlist_window, bg="#E8F5E9")
        scrollbar = ttk.Scrollbar(playlist_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_button_4(event):
            canvas.yview_scroll(-1, "units")

        def on_button_5(event):
            canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", on_mouse_wheel)
        canvas.bind_all("<Button-4>", on_button_4)
        canvas.bind_all("<Button-5>", on_button_5)

        self.photo_references = []
        playlist_window.photo_references = self.photo_references

        for idx, video in enumerate(videos):
            if not video.get('url'):
                continue
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill="x", padx=5, pady=5)

            thumbnail_url = video.get('thumbnail')
            if thumbnail_url:
                photo = self.fetch_thumbnail(thumbnail_url)
                if photo:
                    self.photo_references.append(photo)
                    ttk.Label(frame, image=photo).pack(side="left", padx=5)

            title = video.get('title', f"Video {idx + 1}")
            ttk.Label(frame, text=title, wraplength=400, style="TLabel", foreground="#2E7D32").pack(side="left", padx=5)

            button = ttk.Button(
                frame,
                text="Download",
                style="Download.TButton"
            )
            button.pack(side="right", padx=5)
            button.config(command=lambda url=video['url'], plat="youtube", sp=save_path, btn=button: self.start_download_thread(url, plat, sp, btn))

    def start_download_thread(self, url, platform, save_path, button):
        if self.is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait.")
            return

        self.is_downloading = True
        self.active_button = button
        if button:
            button.configure(style="Active.TButton")

        self.status_label.config(text=f"Starting {platform.capitalize()} download...", foreground="blue")
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
                raise ValueError("Invalid video URL")
            self.start_download_thread(working_url, platform, save_path, None)
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def download_video(self, url, platform, save_path):
        try:
            ffmpeg_path = os.path.join(self.app_dir, 'ffmpeg.exe') if os.path.exists(os.path.join(self.app_dir, 'ffmpeg.exe')) else 'ffmpeg'
            ydl_opts = {
                'outtmpl': os.path.join(save_path, '%(title).100s_%(id)s.%(ext)s'),
                'progress_hooks': [self.update_progress],
                'format': self.quality_var.get(),
                'quiet': True,
                'no_warnings': True,
                'restrictfilenames': True,
                'http_headers': {
                    'User-Agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
                    ),
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
                cookie_file = os.path.join(self.app_dir, 'cookies.txt')
                if os.path.exists(cookie_file):
                    ydl_opts['cookiefile'] = cookie_file
                else:
                    logging.warning("No cookies.txt found. Facebook download may fail due to authentication.")

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
