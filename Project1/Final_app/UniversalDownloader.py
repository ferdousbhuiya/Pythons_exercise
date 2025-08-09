import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import yt_dlp
import re
import datetime
import logging

class UniversalDownloader:
    def __init__(self, master):
        self.master = master
        self.master.title("Universal Video Downloader")
        self.master.geometry("600x500")
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
        title_label = ttk.Label(main_frame, text="Universal Video Downloader", 
                               foreground="#4CAF50")
        title_label.pack(pady=(0, 20))

        # URL input
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill="x", pady=10)

        ttk.Label(url_frame, text="Paste any video link here:").pack(anchor="w")
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url)
        self.url_entry.pack(fill="x", pady=(5, 10))
        self.url_entry.bind('<Return>', lambda e: self.analyze_url())

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
                 wraplength=400, justify="left").pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=20)

        self.analyze_button = ttk.Button(button_frame, text="Analyze & Download", 
                                       command=self.analyze_url)
        self.analyze_button.pack(fill="x", pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, length=500, mode='determinate')
        self.progress.pack(fill="x", pady=10)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to download", 
                                     foreground="#888888")
        self.status_label.pack(pady=5)

        # Info text
        info_text = """
Supported platforms: YouTube, Facebook, TikTok, Instagram, Twitter, Reddit, Vimeo, Dailymotion, Twitch, SoundCloud, and many more!

Just paste any video link and click 'Analyze & Download'
        """
        info_label = ttk.Label(main_frame, text=info_text, foreground="#CCCCCC")
        info_label.pack(pady=20)

    def choose_directory(self):
        path = filedialog.askdirectory(parent=self.master)
        if path:
            self.output_path.set(path)

    def update_status(self, message):
        self.master.after(0, lambda: self.status_label.config(text=message))

    def analyze_url(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a video URL.")
            return
        
        if self.download_in_progress:
            messagebox.showinfo("Please Wait", "A download is in progress, please wait.")
            return

        self.update_status("Analyzing URL...")
        self.progress['value'] = 0
        self.analyze_button.config(state=tk.DISABLED)

        threading.Thread(target=self._analyze_and_download, args=(url,), daemon=True).start()

    def _analyze_and_download(self, url):
        try:
            # Check if it's a Facebook URL and use special handling
            is_facebook = 'facebook.com' in url.lower()
            
            if is_facebook:
                success = self._try_facebook_extraction(url)
                if not success:
                    self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))
                    return
            else:
                # Universal extraction options for non-Facebook URLs
                ydl_opts = {
                    'quiet': True,
                    'extract_flat': False,
                    'skip_download': True,
                    'simulate': True,
                    'getthumbnail': True,
                    'ignoreerrors': False,
                    'dump_single_json': True,
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
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    self._handle_extracted_info(info, url)

        except Exception as e:
            error_msg = f"Error analyzing URL: {str(e)}"
            self.master.after(0, lambda: self.update_status(error_msg))
            self.master.after(0, lambda: messagebox.showerror("Error", f"Failed to analyze URL:\n{str(e)}"))
            self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))
            logging.error(f"Analysis error: {e}")

    def _try_facebook_extraction(self, url):
        """Try multiple methods for Facebook videos"""
        methods = [
            self._try_facebook_method_1,
            self._try_facebook_method_2,
            self._try_facebook_method_3
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                self.master.after(0, lambda: self.update_status(f"Trying Facebook method {i}..."))
                if method(url):
                    return True
            except Exception as e:
                logging.error(f"Facebook method {i} failed: {e}")
                continue
        
        # If all methods fail, show helpful error
        self.master.after(0, lambda: self.update_status("Facebook extraction failed"))
        self.master.after(0, lambda: messagebox.showerror("Facebook Error", 
            "Could not access this Facebook video.\n\n"
            "Possible reasons:\n"
            "1. Video is private or requires login\n"
            "2. Video is from a private group\n"
            "3. Facebook has updated their security\n\n"
            "Try:\n"
            "1. Using a public Facebook video URL\n"
            "2. Making sure the video is publicly accessible\n"
            "3. Trying a different Facebook video"))
        return False

    def _try_facebook_method_1(self, url):
        """Method 1: Standard Facebook extraction"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'skip_download': True,
            'simulate': True,
            'getthumbnail': True,
            'ignoreerrors': False,
            'dump_single_json': True,
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
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and self._has_valid_media(info):
                    self._handle_extracted_info(info, url)
                    return True
        except Exception as e:
            logging.error(f"Facebook method 1 failed: {e}")
        return False

    def _try_facebook_method_2(self, url):
        """Method 2: Facebook with mobile URL format"""
        mobile_url = url.replace('www.facebook.com', 'm.facebook.com')
        if '/reel/' in mobile_url:
            mobile_url = mobile_url.replace('/reel/', '/watch/?v=')
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'skip_download': True,
            'simulate': True,
            'getthumbnail': True,
            'ignoreerrors': False,
            'dump_single_json': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(mobile_url, download=False)
                if info and self._has_valid_media(info):
                    self._handle_extracted_info(info, url)
                    return True
        except Exception as e:
            logging.error(f"Facebook method 2 failed: {e}")
        return False

    def _try_facebook_method_3(self, url):
        """Method 3: Facebook with external hit headers"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'skip_download': True,
            'simulate': True,
            'getthumbnail': True,
            'ignoreerrors': False,
            'dump_single_json': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'http_headers': {
                'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and self._has_valid_media(info):
                    self._handle_extracted_info(info, url)
                    return True
        except Exception as e:
            logging.error(f"Facebook method 3 failed: {e}")
        return False

    def _has_valid_media(self, item_info):
        """Check if item has valid media for download"""
        if item_info.get('url'):
            return True
        
        formats = item_info.get('formats', [])
        for fmt in formats:
            if fmt.get('url'):
                return True
        
        if item_info.get('webpage_url'):
            return True
            
        return False

    def _handle_extracted_info(self, info, url):
        """Handle extracted video information"""
        if info:
            platform = info.get('extractor', 'Unknown')
            title = info.get('title', 'Untitled')
            duration = info.get('duration_string', 'N/A')
            
            self.master.after(0, lambda: self.update_status(f"Found: {title} ({platform})"))
            
            # Show info and ask for confirmation
            confirm_msg = f"Found video:\n\nTitle: {title}\nPlatform: {platform}\nDuration: {duration}\n\nDownload this video?"
            
            if self.master.after(0, lambda: messagebox.askyesno("Confirm Download", confirm_msg)):
                self.master.after(0, lambda: self._start_download(url, title, platform))
            else:
                self.master.after(0, lambda: self.update_status("Download cancelled"))
                self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))
        else:
            self.master.after(0, lambda: self.update_status("No video found at this URL"))
            self.master.after(0, lambda: messagebox.showerror("Error", "No video found at this URL"))
            self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))

    def _start_download(self, url, title, platform):
        if not self.output_path.get():
            messagebox.showerror("Error", "Please choose a download location first.")
            self.analyze_button.config(state=tk.NORMAL)
            return

        self.download_in_progress = True
        self.update_status(f"Starting download: {title}")
        self.progress['value'] = 0

        threading.Thread(target=self._download_video, args=(url, title, platform), daemon=True).start()

    def _download_video(self, url, title, platform):
        try:
            # Sanitize filename
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '', title) if title else f"video_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            sanitized_title = sanitized_title[:50].strip()

            ydl_opts = {
                'progress_hooks': [self.update_progress],
                'outtmpl': os.path.join(self.output_path.get(), f'{sanitized_title}.%(ext)s'),
                'restrictfilenames': True,
                'retries': 10,
                'fragment_retries': 10,
                'extractor_retries': 5,
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
                logging.info(f"Starting download: {title} from {platform}")
                ydl.download([url])
                logging.info(f"Download completed: {title}")

            self.master.after(0, lambda: self.update_status(f"Download complete: {title}"))
            self.master.after(0, lambda: messagebox.showinfo("Success", f"'{title}' downloaded successfully!"))

        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self.master.after(0, lambda: self.update_status(error_msg))
            self.master.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download '{title}':\n{str(e)}"))
            logging.error(f"Download error for {title}: {e}")
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
        self.analyze_button.config(state=tk.NORMAL)

if __name__ == '__main__':
    root = tk.Tk()
    app = UniversalDownloader(root)
    root.mainloop() 