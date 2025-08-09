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

class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook & YouTube Video Downloader (Updated July 2025)")
        self.root.geometry("500x450")

        # Threading queue for progress updates
        self.progress_queue = queue.Queue()
        self.is_downloading = False
        self.active_button = None  # Track the currently downloading button

        # Apply colorful theme
        style = ttk.Style()
        style.configure("TButton", padding=5, font=("Helvetica", 10))
        style.configure("Download.TButton", background="#4CAF50", foreground="white")  # Green for download buttons
        style.configure("Action.TButton", background="#2196F3", foreground="white")  # Blue for action buttons
        style.configure("TLabel", font=("Helvetica", 10), foreground="#333333")
        style.configure("TProgressbar", troughcolor="#BBDEFB", background="#9C27B0")  # Purple progress bar
        self.root.configure(bg="#E3F2FD")  # Light blue background

        # URL Entry
        ttk.Label(root, text="Video or Playlist URL (Facebook or YouTube):", style="TLabel").pack(pady=10)
        self.url_entry = ttk.Entry(root, width=50, font=("Helvetica", 10))
        self.url_entry.pack(pady=5)
        ttk.Label(
            root,
            text="Examples:\nFacebook: https://www.facebook.com/watch?v=123456789\nYouTube: https://www.youtube.com/watch?v=abc123\nPlaylist: https://www.youtube.com/playlist?list=PL...",
            justify="center",
            style="TLabel",
            foreground="#1976D2"  # Blue for example text
        ).pack(pady=5)

        # Quality Options
        ttk.Label(root, text="Quality:", style="TLabel").pack(pady=5)
        self.quality_var = tk.StringVar(value="best")
        ttk.Radiobutton(root, text="Highest", variable=self.quality_var, value="bestvideo+bestaudio/best").pack()
        ttk.Radiobutton(root, text="Medium", variable=self.quality_var, value="bestvideo[height<=720]+bestaudio/best").pack()
        ttk.Radiobutton(root, text="Lowest", variable=self.quality_var, value="worst").pack()

        # Save Location
        ttk.Label(root, text="Save To:", style="TLabel").pack(pady=5)
        self.location_entry = ttk.Entry(root, width=40, font=("Helvetica", 10))
        self.location_entry.pack(pady=5)
        self.location_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Button(root, text="Browse", command=self.browse_location, style="Action.TButton").pack(pady=5)

        # Action Buttons
        ttk.Button(root, text="Analyze URL", command=self.analyze_url, style="Action.TButton").pack(pady=10)
        ttk.Button(root, text="Download Video", command=self.download_video, style="Action.TButton").pack(pady=5)

        # Status Label
        self.status_label = ttk.Label(root, text="", foreground="blue", style="TLabel")
        self.status_label.pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", style="TProgressbar")
        self.progress.pack(pady=10)

        # Start polling for progress updates
        self.check_progress_queue()

    def browse_location(self):
        """Open a dialog to select download folder."""
        folder = filedialog.askdirectory()
        if folder:
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, folder)

    def update_progress(self, d):
        """Update progress bar during download (called from download thread)."""
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
        """Poll the queue for progress and status updates."""
        try:
            while True:
                msg_type, value, *extra = self.progress_queue.get_nowait()
                if msg_type == 'progress':
                    self.progress['value'] = value
                elif msg_type == 'status':
                    color = extra[0] if extra else 'blue'
                    self.status_label.config(text=value, foreground=color)
                    if value == 'Download complete!' and self.active_button:
                        self.active_button.configure(style="Download.TButton")  # Revert button color
                        self.active_button = None
                self.root.update_idletasks()
        except queue.Empty:
            pass
        self.root.after(100, self.check_progress_queue)

    def validate_url(self, url):
        """Validate and standardize URL, detect platform and playlist."""
        url = url.strip()

        # Check for YouTube URLs (including playlists)
        youtube_patterns = [
            r'youtube\.com/watch\?v=[\w-]+',
            r'youtu\.be/[\w-]+',
            r'youtube\.com/shorts/[\w-]+',
            r'youtube\.com/playlist\?list=[\w-]+',
            r'youtube\.com.*list=[\w-]+'
        ]
        if any(re.search(pattern, url) for pattern in youtube_patterns):
            return url, "youtube"

        # Check for Facebook URLs and standardize
        url = url.replace('m.facebook.com', 'www.facebook.com')
        facebook_patterns = [
            r'v=(\d+)',           # For ?v=123 formats
            r'videos/(\d+)',      # For /videos/123 formats
            r'watch/\?v=(\d+)',   # For /watch?v=123 formats
            r'reel/(\d+)',        # For /reel/123 formats
            r'/(\d+)/?$'          # For /123/ formats
        ]
        for pattern in facebook_patterns:
            match = re.search(pattern, url)
            if match:
                return f"https://www.facebook.com/watch/?v={match.group(1)}", "facebook"
        
        return None, None

    def fetch_thumbnail(self, url):
        """Fetch and resize thumbnail image."""
        try:
            with urllib.request.urlopen(url) as response:
                img_data = response.read()
            img = Image.open(BytesIO(img_data))
            img = img.resize((100, 56), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def analyze_url(self):
        """Analyze URL and display playlist videos if applicable."""
        if self.is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait.")
            return

        raw_url = self.url_entry.get().strip()
        save_path = self.location_entry.get().strip()

        # Input validation
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
                raise ValueError(
                    "Invalid video or playlist URL\nExamples:\nFacebook: https://www.facebook.com/watch?v=123456789\n"
                    "YouTube: https://www.youtube.com/watch?v=abc123\nPlaylist: https://www.youtube.com/playlist?list=PL..."
                )

            if platform == "youtube":
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,
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
                    self.start_download_thread(working_url, platform, save_path)
            else:
                self.start_download_thread(working_url, platform, save_path)

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def show_playlist_videos(self, videos, save_path):
        """Display a scrollable list of videos with thumbnails and download buttons."""
        playlist_window = tk.Toplevel(self.root)
        playlist_window.title("Select Videos to Download")
        playlist_window.geometry("600x400")
        playlist_window.configure(bg="#ECB689")  # Light green background

        canvas = tk.Canvas(playlist_window, bg="#75F07F")
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

        # Enable mouse wheel and touchpad scrolling
        def on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_button_4(event):
            canvas.yview_scroll(-1, "units")

        def on_button_5(event):
            canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", on_mouse_wheel)  # Windows
        canvas.bind_all("<Button-4>", on_button_4)  # Linux/macOS
        canvas.bind_all("<Button-5>", on_button_5)  # Linux/macOS

        self.photo_references = []

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
                style="Download.TButton",
                command=lambda url=video['url'], plat="youtube", sp=save_path, btn=frame: self.start_download_thread(url, plat, sp, btn.winfo_children()[-1])
            )
            button.pack(side="right", padx=5)

    def start_download_thread(self, url, platform, save_path, button=None):
        """Start download in a separate thread."""
        if self.is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait.")
            return

        self.is_downloading = True
        self.active_button = button
        if button:
            button.configure(style="TButton")  # Change to default style (gray) when downloading

        self.status_label.config(text=f"Starting {platform.capitalize()} download...", foreground="blue")
        self.progress['value'] = 0

        thread = threading.Thread(target=self.download_video, args=(url, platform, save_path))
        thread.daemon = True
        thread.start()

    def download_video(self, url, platform, save_path):
        """Handle video download process for a single video."""
        try:
            ydl_opts = {
                'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.update_progress],
                'format': self.quality_var.get(),
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
                    ),
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            }

            if platform == "facebook":
                ydl_opts['extractor_args'] = {'facebook': {'skip_dash_manifest': True}}
                ydl_opts['http_headers']['Referer'] = 'https://www.facebook.com/'

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.progress_queue.put(('status', f"{platform.capitalize()} video downloaded successfully!", 'green'))
            self.progress_queue.put(('progress', 100))

        except Exception as e:
            self.progress_queue.put(('status', f"Error: {str(e)}", 'red'))
            self.progress_queue.put(('progress', 0))
        finally:
            self.is_downloading = False

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()