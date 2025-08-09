import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL
import os
import re
import urllib.request
from PIL import Image, ImageTk
from io import BytesIO

class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook & YouTube Video Downloader (Updated July 2025)")
        self.root.geometry("500x450")

        # URL Entry
        ttk.Label(root, text="Video or Playlist URL (Facebook or YouTube):").pack(pady=10)
        self.url_entry = ttk.Entry(root, width=50)
        self.url_entry.pack(pady=5)
        ttk.Label(
            root,
            text="Examples:\nFacebook: https://www.facebook.com/watch?v=123456789\nYouTube: https://www.youtube.com/watch?v=abc123\nPlaylist: https://www.youtube.com/playlist?list=PL...",
            justify="center"
        ).pack(pady=5)

        # Quality Options
        ttk.Label(root, text="Quality:").pack(pady=5)
        self.quality_var = tk.StringVar(value="best")
        ttk.Radiobutton(root, text="Highest", variable=self.quality_var, value="bestvideo+bestaudio/best").pack()
        ttk.Radiobutton(root, text="Medium", variable=self.quality_var, value="bestvideo[height<=720]+bestaudio/best").pack()
        ttk.Radiobutton(root, text="Lowest", variable=self.quality_var, value="worst").pack()

        # Save Location
        ttk.Label(root, text="Save To:").pack(pady=5)
        self.location_entry = ttk.Entry(root, width=40)
        self.location_entry.pack(pady=5)
        self.location_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Button(root, text="Browse", command=self.browse_location).pack(pady=5)

        # Action Buttons
        ttk.Button(root, text="Analyze URL", command=self.analyze_url).pack(pady=10)
        ttk.Button(root, text="Download Video", command=self.download_video).pack(pady=5)

        # Status Label
        self.status_label = ttk.Label(root, text="", foreground="blue")
        self.status_label.pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)

    def browse_location(self):
        """Open a dialog to select download folder."""
        folder = filedialog.askdirectory()
        if folder:
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, folder)

    def update_progress(self, d):
        """Update progress bar during download."""
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '0%')
                clean_percent = re.sub(r'\x1b\[[0-9;]*[mK]', '', percent_str).replace('%', '')
                percent = float(clean_percent)
                self.progress['value'] = percent
                self.root.update_idletasks()
            except (ValueError, AttributeError):
                self.progress['value'] = min(self.progress['value'] + 1, 100)
                self.root.update_idletasks()

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
            img = img.resize((100, 56), Image.Resampling.LANCZOS)  # Resize to 100x56
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def analyze_url(self):
        """Analyze URL and display playlist videos if applicable."""
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
                # Check if URL is a playlist
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,  # Extract metadata without downloading
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
                    # Playlist detected, show selection window
                    self.show_playlist_videos(info['entries'], save_path)
                    self.status_label.config(text="Playlist loaded, select videos to download", foreground="blue")
                else:
                    # Single video, proceed to download
                    self.download_video(working_url, platform)
            else:
                # Facebook video, proceed to download
                self.download_video(working_url, platform)

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def show_playlist_videos(self, videos, save_path):
        """Display a scrollable list of videos with thumbnails and download buttons."""
        playlist_window = tk.Toplevel(self.root)
        playlist_window.title("Select Videos to Download")
        playlist_window.geometry("600x400")

        # Create scrollable canvas
        canvas = tk.Canvas(playlist_window)
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

        # Store PhotoImage references to prevent garbage collection
        self.photo_references = []

        # Display each video
        for idx, video in enumerate(videos):
            if not video.get('url'):
                continue
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill="x", padx=5, pady=5)

            # Thumbnail
            thumbnail_url = video.get('thumbnail')
            if thumbnail_url:
                photo = self.fetch_thumbnail(thumbnail_url)
                if photo:
                    self.photo_references.append(photo)
                    ttk.Label(frame, image=photo).pack(side="left", padx=5)

            # Title
            title = video.get('title', f"Video {idx + 1}")
            ttk.Label(frame, text=title, wraplength=400).pack(side="left", padx=5)

            # Download Button
            ttk.Button(
                frame,
                text="Download",
                command=lambda url=video['url'], plat="youtube": self.download_video(url, plat, save_path)
            ).pack(side="right", padx=5)

    def download_video(self, url, platform, save_path=None):
        """Handle video download process for a single video."""
        if not save_path:
            save_path = self.location_entry.get().strip()

        try:
            self.status_label.config(text=f"Starting {platform.capitalize()} download...", foreground="blue")
            self.progress['value'] = 0

            # yt-dlp configuration
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

            # Add Facebook-specific options
            if platform == "facebook":
                ydl_opts['extractor_args'] = {'facebook': {'skip_dash_manifest': True}}
                ydl_opts['http_headers']['Referer'] = 'https://www.facebook.com/'

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.status_label.config(text="Download complete!", foreground="green")
            self.progress['value'] = 100
            messagebox.showinfo("Success", f"{platform.capitalize()} video downloaded successfully!")

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))
            self.progress['value'] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()