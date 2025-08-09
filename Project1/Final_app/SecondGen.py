# -*- coding: utf-8 -*-
import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, Canvas, Scrollbar, Frame
from PIL import Image, ImageTk
import yt_dlp
import io
import requests
import datetime
import re
import logging

class VideoDownloader:
    def __init__(self, master):
        self.master = master
        self.master.title("Ferdous Video Downloader")
        self.master.geometry("800x700")
        self.master.resizable(True, True)
        self.master.configure(bg="#2E2E2E")

        self.url = tk.StringVar()
        self.download_in_progress = False
        self.output_path = tk.StringVar(value=os.getcwd())
        self.selected_quality = tk.StringVar(value="best")

        self.tk_thumbnail_images = {}
        self.media_info_list = []

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
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("TLabel", background="#2E2E2E", foreground="white", font=("Arial", 10))
        style.configure("TButton", background="#4CAF50", foreground="white", font=("Arial", 10, "bold"), borderwidth=0)
        style.map("TButton", background=[('active', '#45a049')])
        style.configure("TEntry", fieldbackground="#3E3E3E", foreground="white", insertbackground="white", font=("Arial", 10), borderwidth=1, relief="flat")
        style.configure("TCombobox", fieldbackground="#3E3E3E", foreground="white", font=("Arial", 10))
        style.map('TCombobox', fieldbackground=[('readonly', '#3E3E3E')], selectbackground=[('readonly', '#3E3E3E')])
        style.configure("TProgressbar", troughcolor="#3E3E3E", background="#4CAF50", thickness=15)
        style.configure("ItemFrame.TFrame", background="#3E3E3E", borderwidth=1, relief="solid")
        style.configure("ItemLabel.TLabel", background="#3E3E3E", foreground="white", font=("Arial", 9))
        style.configure("ItemButton.TButton", background="#2e86de", foreground="white", font=("Arial", 9, "bold"), borderwidth=0)
        style.map("ItemButton.TButton", background=[('active', '#256fb2')])

        input_frame = ttk.Frame(self.master, style="TLabel")
        input_frame.pack(pady=(20, 10), padx=20, fill="x")

        ttk.Label(input_frame, text="Enter video or playlist URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.url_entry = ttk.Entry(input_frame, textvariable=self.url, width=60)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Choose Quality:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.quality_combo = ttk.Combobox(input_frame, textvariable=self.selected_quality, state="readonly", width=15)
        self.quality_combo['values'] = ("best", "worst", "audio")
        self.quality_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.quality_combo.set("best")

        ttk.Button(input_frame, text="Choose Download Location", command=self.choose_directory).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(input_frame, textvariable=self.output_path, wraplength=350, justify="left").grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        input_frame.grid_columnconfigure(1, weight=1)

        action_buttons_frame = ttk.Frame(self.master, style="TLabel")
        action_buttons_frame.pack(pady=5, padx=20, fill="x")

        self.analyze_button = ttk.Button(action_buttons_frame, text="Analyze URL", command=self.start_analyze)
        self.analyze_button.pack(side="left", expand=True, fill="x", padx=5)

        self.progress = ttk.Progressbar(self.master, length=500, mode='determinate')
        self.progress.pack(pady=(15, 5), padx=20, fill="x")

        self.status_label = ttk.Label(self.master, text="Idle", foreground="#888888")
        self.status_label.pack(pady=5)
        
        self.preview_canvas_frame = ttk.Frame(self.master, style="TLabel")
        self.preview_canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = Canvas(self.preview_canvas_frame, bg="#fdf6ec", highlightthickness=0)
        self.scrollbar = Scrollbar(self.preview_canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = Frame(self.canvas, bg="#fdf6ec")

        self.scrollable_content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        direction = -1 if event.num == 4 else 1
        self.canvas.yview_scroll(direction, "units")

    def choose_directory(self):
        path = filedialog.askdirectory(parent=self.master)
        if path:
            self.output_path.set(path)

    def update_status(self, message):
        self.master.after(0, lambda: self.status_label.config(text=message))

    def start_analyze(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a video or playlist URL.")
            return
        
        if self.download_in_progress:
            messagebox.showinfo("Please Wait", "A download is in progress, please wait.")
            return

        for widget in self.scrollable_content.winfo_children():
            widget.destroy()
        self.tk_thumbnail_images.clear()

        self.update_status("Analyzing URL...")
        self.progress['value'] = 0
        self.progress.stop()

        self.analyze_button.config(state=tk.DISABLED)

        threading.Thread(target=self._extract_info_task, args=(url,), daemon=True).start()

    def _extract_info_task(self, url):
        # Check if it's a Facebook URL and adjust settings accordingly
        is_facebook = 'facebook.com' in url.lower()
        
        # Try multiple methods for Facebook
        if is_facebook:
            success = self._try_facebook_methods(url)
            if not success:
                self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))
                return
        else:
            # For non-Facebook URLs, use standard method
            success = self._try_standard_extraction(url)
            if not success:
                self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))
                return

        self.master.after(0, self._display_media_items)
        self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))

    def _try_facebook_methods(self, url):
        """Try multiple methods for Facebook videos"""
        methods = [
            self._try_facebook_method_1,
            self._try_facebook_method_2,
            self._try_facebook_method_3,
            self._try_facebook_method_4
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                self.master.after(0, lambda: self.update_status(f"Trying Facebook method {i}..."))
                if method(url):
                    return True
            except Exception as e:
                logging.error(f"Facebook method {i} failed: {e}")
                continue
        
        # If all methods fail, show error
        self.master.after(0, lambda: self.update_status("All Facebook methods failed"))
        self.master.after(0, lambda: messagebox.showerror("Facebook Error", 
            "Could not access this Facebook video/reel.\n\n"
            "Possible reasons:\n"
            "1. Video is private or requires login\n"
            "2. Video is from a private group\n"
            "3. Facebook has updated their security\n"
            "4. Need to update yt-dlp\n\n"
            "Try:\n"
            "1. Using a public Facebook video URL\n"
            "2. Running: pip install --upgrade yt-dlp\n"
            "3. Trying a different Facebook video"))
        return False

    def _try_facebook_method_1(self, url):
        """Method 1: Standard Facebook extraction with cookies"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'force_generic_extractor': False,
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
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and self._has_valid_media(info):
                    self.media_info_list = [info]
                    self.master.after(0, lambda: self.update_status(f"Found Facebook video: {info.get('title', 'Untitled')}"))
                    return True
        except Exception as e:
            logging.error(f"Facebook method 1 failed: {e}")
        return False

    def _try_facebook_method_2(self, url):
        """Method 2: Facebook with external hit headers"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'force_generic_extractor': False,
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
                    self.media_info_list = [info]
                    self.master.after(0, lambda: self.update_status(f"Found Facebook video: {info.get('title', 'Untitled')}"))
                    return True
        except Exception as e:
            logging.error(f"Facebook method 2 failed: {e}")
        return False

    def _try_facebook_method_3(self, url):
        """Method 3: Try with mobile URL format"""
        # Convert to mobile URL format
        mobile_url = url.replace('www.facebook.com', 'm.facebook.com')
        if '/reel/' in mobile_url:
            mobile_url = mobile_url.replace('/reel/', '/watch/?v=')
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'force_generic_extractor': False,
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
                    self.media_info_list = [info]
                    self.master.after(0, lambda: self.update_status(f"Found Facebook video: {info.get('title', 'Untitled')}"))
                    return True
        except Exception as e:
            logging.error(f"Facebook method 3 failed: {e}")
        return False

    def _try_facebook_method_4(self, url):
        """Method 4: Try with different URL format and no redirects"""
        # Try different URL formats
        url_variants = [
            url,
            url.replace('/reel/', '/watch/?v='),
            url.replace('www.facebook.com', 'm.facebook.com'),
            url.replace('m.facebook.com', 'www.facebook.com')
        ]
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'force_generic_extractor': False,
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
            'nocheckcertificate': True,
            'allow_unplayable_formats': True,
        }
        
        for variant_url in url_variants:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(variant_url, download=False)
                    if info and self._has_valid_media(info):
                        self.media_info_list = [info]
                        self.master.after(0, lambda: self.update_status(f"Found Facebook video: {info.get('title', 'Untitled')}"))
                        return True
            except Exception as e:
                logging.error(f"Facebook method 4 failed for {variant_url}: {e}")
                continue
        return False

    def _try_standard_extraction(self, url):
        """Standard extraction for non-Facebook URLs"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'force_generic_extractor': False,
            'skip_download': True,
            'simulate': True,
            'getthumbnail': True,
            'ignoreerrors': False,
            'dump_single_json': True,
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
                logging.info(f"Extracted info for URL: {url} - Extractor: {info.get('extractor', 'Unknown')}")
                
                if 'entries' in info and info['entries']:
                    self.media_info_list = [entry for entry in info['entries'] if entry and self._has_valid_media(entry)]
                    self.master.after(0, lambda: self.update_status(f"Found {len(self.media_info_list)} items in playlist."))
                elif info and self._has_valid_media(info):
                    self.media_info_list = [info]
                    self.master.after(0, lambda: self.update_status(f"Found single video: {info.get('title', 'Untitled')}"))
                else:
                    self.media_info_list = []
                    self.master.after(0, lambda: self.update_status("Error: No valid media found at URL."))
                    logging.warning(f"No valid media extracted from {url}")
                    return False
                return True
        except Exception as e:
            self.master.after(0, lambda err=e: self.update_status(f"Error analyzing: {err}"))
            self.master.after(0, lambda err=e: messagebox.showerror("Analysis Error", f"Failed to analyze URL:\n{err}"))
            logging.error(f"Standard extraction failed for {url}: {e}")
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

    def _get_download_url(self, item_info):
        """Get the best download URL for an item"""
        if item_info.get('webpage_url'):
            return item_info['webpage_url']
        
        if item_info.get('url'):
            return item_info['url']
        
        formats = item_info.get('formats', [])
        for fmt in formats:
            if fmt.get('url'):
                return fmt['url']
        
        return None

    def _display_media_items(self):
        if not self.media_info_list:
            messagebox.showinfo("Info", "No media found for the given URL. Check the log for details.")
            self.update_status("Idle")
            return

        for i, item_info in enumerate(self.media_info_list):
            item_frame = ttk.Frame(self.scrollable_content, style="ItemFrame.TFrame")
            item_frame.pack(fill="x", pady=5, padx=5, expand=True)

            thumbnail_url = item_info.get("thumbnail")
            tk_img = None
            if thumbnail_url:
                try:
                    response = requests.get(thumbnail_url, timeout=5)
                    response.raise_for_status()
                    img_data = response.content
                    img = Image.open(io.BytesIO(img_data))
                    img.thumbnail((120, 67), Image.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    self.tk_thumbnail_images[item_info.get('id', i)] = tk_img
                except Exception as img_e:
                    logging.error(f"Failed to load thumbnail for {item_info.get('title', 'N/A')}: {img_e}")
            
            if tk_img:
                thumbnail_label = ttk.Label(item_frame, image=tk_img, style="ItemLabel.TLabel")
                thumbnail_label.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="n")
                thumbnail_label.image = tk_img
            else:
                fallback_label = ttk.Label(item_frame, text="No Image", style="ItemLabel.TLabel", width=15, anchor="center")
                fallback_label.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="n")

            info_button_frame = ttk.Frame(item_frame, style="ItemFrame.TFrame")
            info_button_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky="nsew")
            
            title = item_info.get("title", "Untitled Video")
            if title is None:
                title = "Untitled Video"
                logging.warning(f"Title was None for item {item_info.get('id', i)}, using fallback.")
            
            platform = item_info.get('extractor', 'Unknown')
            title_with_platform = f"[{platform.upper()}] {title}"
            
            ttk.Label(info_button_frame, text=title_with_platform, font=("Arial", 10, "bold"), style="ItemLabel.TLabel", wraplength=450, justify="left").pack(pady=(0, 2), anchor="w")
            ttk.Label(info_button_frame, text=item_info.get("duration_string", "N/A"), style="ItemLabel.TLabel", foreground="#bbb").pack(pady=(0, 5), anchor="w")

            download_url = self._get_download_url(item_info)
            if not download_url:
                logging.warning(f"No valid URL found for item {item_info.get('id', i)}, skipping download button.")
                continue
                
            download_btn = ttk.Button(info_button_frame, text="Download", style="ItemButton.TButton",
                                      command=lambda url=download_url, title=title, platform=platform: self.start_single_download(url, title, platform))
            download_btn.pack(pady=(0, 5), anchor="w")

            item_frame.grid_columnconfigure(1, weight=1)

        self.canvas.yview_moveto(0)
        self.canvas.update_idletasks()

    def start_single_download(self, media_url, title, platform="Unknown"):
        if self.download_in_progress:
            messagebox.showinfo("Please Wait", "Another download is already in progress.")
            return

        if not self.output_path.get():
            messagebox.showerror("Error", "Please choose a download location first.")
            return

        if not media_url:
            messagebox.showerror("Error", "No valid download URL available.")
            return

        self.download_in_progress = True
        self.analyze_button.config(state=tk.DISABLED)

        self.update_status(f"Starting download for: {title[:70]}...")
        self.progress['value'] = 0
        self.progress.start()

        threading.Thread(target=self._download_video_task, args=(media_url, title, platform), daemon=True).start()

    def _download_video_task(self, url, title_for_display="Unknown Title", platform="Unknown"):
        try:
            ydl_opts = self.get_common_ydl_opts()
            
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '', title_for_display) if title_for_display else f"video_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            sanitized_title = sanitized_title[:50].strip()
            ydl_opts['outtmpl'] = os.path.join(self.output_path.get(), f'{sanitized_title}_%(id)s.%(ext)s')

            # Add platform-specific options
            if 'facebook' in platform.lower():
                ydl_opts.update({
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                })

            ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')
            if os.path.exists(ffmpeg_path):
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logging.info(f"Starting download for URL: {url} from {platform}")
                ydl.download([url])
                logging.info(f"Download completed successfully: {title_for_display}")

            self.master.after(0, lambda: self.update_status(f"Download complete: {title_for_display}"))
            self.master.after(0, lambda: messagebox.showinfo("Success", f"'{title_for_display}' downloaded successfully!"))

        except yt_dlp.utils.DownloadError as e:
            self.master.after(0, lambda err=e: self.update_status(f"Download Error: {err}"))
            self.master.after(0, lambda err=e: messagebox.showerror("Download Error", f"Failed to download '{title_for_display}':\n{err}\n\nCheck URL, internet connection, or try updating yt-dlp.\n\nCheck log for more details."))
            logging.error(f"Download error for {title_for_display}: {e}")
        except Exception as e:
            self.master.after(0, lambda err=e: self.update_status(f"An error occurred: {err}"))
            self.master.after(0, lambda err=e: messagebox.showerror("Error", f"An unexpected error occurred for '{title_for_display}':\n{err}\n\nCheck log for more details."))
            logging.error(f"Unexpected error for {title_for_display}: {e}")
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
                    status_text = f"Downloading: {d.get('_percent_str', '')} of {d.get('_total_bytes_str', 'Unknown Size')} at {d.get('_speed_str', 'N/A')}"
                except ZeroDivisionError:
                    self.progress.config(mode='indeterminate')
                    status_text = f"Downloading: {d.get('_percent_str', '')} (Progress Unknown)"
            else:
                self.progress.config(mode='indeterminate')
                status_text = f"Downloading: {d.get('_percent_str', '')} (Live Stream/Unknown Size)"

            self.status_label.config(text=status_text)
            self.master.update_idletasks()

        elif d['status'] == 'finished':
            self.progress['value'] = 100
            self.status_label.config(text="Processing...")
            self.progress.stop()

    def get_common_ydl_opts(self):
        opts = {
            'progress_hooks': [self.update_progress],
            'restrictfilenames': True,
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 5,
            'postprocessors': [],
            'no_warnings': True,
            'quiet': True,
            'noplaylist': False,
            'outtmpl': '%(title)s_%(id)s.%(ext)s',
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

        quality = self.selected_quality.get()
        if quality == "audio":
            opts['format'] = "bestaudio/best"
            opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
            opts['extract_audio'] = True
            opts['postvideo'] = True
        elif quality == "worst":
            opts['format'] = "worstvideo+worstaudio/worst"
            opts['merge_output_format'] = 'mp4'
        else:  # "best"
            opts['format'] = "best[height<=1080]/bestvideo[height<=1080]+bestaudio/best"
            opts['merge_output_format'] = 'mp4'

        return opts

    def reset_download_state(self):
        self.download_in_progress = False
        self.progress.stop()
        self.progress['value'] = 0
        self.progress.config(mode='determinate')
        self.update_status("Idle")
        self.analyze_button.config(state=tk.NORMAL)

if __name__ == '__main__':
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()
