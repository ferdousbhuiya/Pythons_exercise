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

class VideoDownloader:
    def __init__(self, master):
        self.master = master
        self.master.title("Ferdous Video Downloader")
        self.master.geometry("800x700") # Adjusted size for better playlist display
        self.master.resizable(True, True) # Allow resizing for better playlist view
        self.master.configure(bg="#2E2E2E")

        self.url = tk.StringVar()
        self.download_in_progress = False
        self.output_path = tk.StringVar(value=os.getcwd())
        self.selected_quality = tk.StringVar(value="best")

        self.tk_thumbnail_images = {} # Dictionary to store thumbnail images for multiple items
        self.media_info_list = [] # To store all extracted info for playlist items

        self.create_widgets()

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure general styles
        style.configure("TLabel", background="#2E2E2E", foreground="white", font=("Arial", 10))
        style.configure("TButton", background="#4CAF50", foreground="white", font=("Arial", 10, "bold"), borderwidth=0)
        style.map("TButton", background=[('active', '#45a049')])
        style.configure("TEntry", fieldbackground="#3E3E3E", foreground="white", insertbackground="white", font=("Arial", 10), borderwidth=1, relief="flat")
        style.configure("TCombobox", fieldbackground="#3E3E3E", foreground="white", font=("Arial", 10))
        style.map('TCombobox', fieldbackground=[('readonly', '#3E3E3E')], selectbackground=[('readonly', '#3E3E3E')])
        style.configure("TProgressbar", troughcolor="#3E3E3E", background="#4CAF50", thickness=15)
        # Style for item containers in the scrollable area
        style.configure("ItemFrame.TFrame", background="#3E3E3E", borderwidth=1, relief="solid")
        style.configure("ItemLabel.TLabel", background="#3E3E3E", foreground="white", font=("Arial", 9))
        style.configure("ItemButton.TButton", background="#2e86de", foreground="white", font=("Arial", 9, "bold"), borderwidth=0)
        style.map("ItemButton.TButton", background=[('active', '#256fb2')])

        # Input Frame
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

        # Action Buttons Frame
        action_buttons_frame = ttk.Frame(self.master, style="TLabel")
        action_buttons_frame.pack(pady=5, padx=20, fill="x")

        self.analyze_button = ttk.Button(action_buttons_frame, text="Analyze URL", command=self.start_analyze)
        self.analyze_button.pack(side="left", expand=True, fill="x", padx=5)

        # Progress and Status
        self.progress = ttk.Progressbar(self.master, length=500, mode='determinate')
        self.progress.pack(pady=(15, 5), padx=20, fill="x")

        self.status_label = ttk.Label(self.master, text="Idle", foreground="#888888")
        self.status_label.pack(pady=5)
        
        # --- Scrollable Preview Area ---
        self.preview_canvas_frame = ttk.Frame(self.master, style="TLabel")
        self.preview_canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = Canvas(self.preview_canvas_frame, bg="#fdf6ec", highlightthickness=0)
        self.scrollbar = Scrollbar(self.preview_canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = Frame(self.canvas, bg="#fdf6ec") # Inner frame for content

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind mouse wheel for scrolling
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

    # Re-adding the update_status method here
    def update_status(self, message):
        """Thread-safe update for status label."""
        self.master.after(0, lambda: self.status_label.config(text=message))

    def start_analyze(self):
        """Starts the analysis in a separate thread."""
        url = self.url.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a video or playlist URL.")
            return
        
        if self.download_in_progress:
            messagebox.showinfo("Please Wait", "A download is in progress, please wait.")
            return

        # Clear previous results and prepare UI for analysis
        for widget in self.scrollable_content.winfo_children():
            widget.destroy()
        self.tk_thumbnail_images.clear() # Clear stored image references

        self.update_status("Analyzing URL...")
        self.progress['value'] = 0
        self.progress.stop()

        self.analyze_button.config(state=tk.DISABLED)

        threading.Thread(target=self._extract_info_task, args=(url,), daemon=True).start()

    def _extract_info_task(self, url):
        """Threaded task for extracting video/playlist info."""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True, # Faster for info extraction
            'force_generic_extractor': False,
            'skip_download': True,
            'simulate': True,
            'getthumbnail': True,
            'ignoreerrors': True, # Don't stop on errors, try to get available info
            'dump_single_json': True, # Return info as a single JSON object (important for playlists)
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info and info['entries']:
                    # It's a playlist, filter out potential None entries
                    self.media_info_list = [entry for entry in info['entries'] if entry and entry.get('url')]
                    self.master.after(0, lambda: self.update_status(f"Found {len(self.media_info_list)} items in playlist."))
                else:
                    # It's a single video, wrap it in a list
                    if info and info.get('url'):
                        self.media_info_list = [info]
                        self.master.after(0, lambda: self.update_status(f"Found single video: {info.get('title', 'Untitled')}"))
                    else:
                        self.media_info_list = [] # No valid info found
                        self.master.after(0, lambda: self.update_status("Error: No valid media found at URL."))

            self.master.after(0, self._display_media_items)

        except Exception as e:
            self.master.after(0, lambda: self.update_status(f"Error analyzing: {e}"))
            self.master.after(0, lambda: messagebox.showerror("Analysis Error", f"Failed to analyze URL:\n{e}\n\nPossible reasons:\n- Invalid URL\n- Geoblocking\n- Private/Login required\n- Site layout changed (try updating yt-dlp).\n\nCheck console for more details."))
        finally:
            self.master.after(0, lambda: self.analyze_button.config(state=tk.NORMAL))

    def _display_media_items(self):
        """Displays all found media items in the scrollable area."""
        if not self.media_info_list:
            messagebox.showinfo("Info", "No media found for the given URL.")
            self.update_status("Idle")
            return

        for i, item_info in enumerate(self.media_info_list):
            item_frame = ttk.Frame(self.scrollable_content, style="ItemFrame.TFrame")
            item_frame.pack(fill="x", pady=5, padx=5, expand=True) # Use pack for item frames within scrollable_content

            # Thumbnail
            thumbnail_url = item_info.get("thumbnail")
            tk_img = None
            if thumbnail_url:
                try:
                    response = requests.get(thumbnail_url, timeout=5)
                    response.raise_for_status()
                    img_data = response.content
                    img = Image.open(io.BytesIO(img_data))
                    img.thumbnail((120, 67), Image.LANCZOS) # Standard 16:9 ratio, smaller size
                    tk_img = ImageTk.PhotoImage(img)
                    self.tk_thumbnail_images[item_info.get('id', i)] = tk_img # Store reference
                except Exception as img_e:
                    print(f"Failed to load thumbnail for {item_info.get('title', 'N/A')}: {img_e}")
            
            if tk_img:
                thumbnail_label = ttk.Label(item_frame, image=tk_img, style="ItemLabel.TLabel")
                thumbnail_label.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="n")
                thumbnail_label.image = tk_img # Keep reference
            else:
                fallback_label = ttk.Label(item_frame, text="No Image", style="ItemLabel.TLabel", width=15, anchor="center")
                fallback_label.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="n")

            # Info and Button Frame
            info_button_frame = ttk.Frame(item_frame, style="ItemFrame.TFrame")
            info_button_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky="nsew")
            
            title = item_info.get("title", "Untitled Video")
            ttk.Label(info_button_frame, text=title, font=("Arial", 10, "bold"), style="ItemLabel.TLabel", wraplength=450, justify="left").pack(pady=(0, 2), anchor="w")
            ttk.Label(info_button_frame, text=item_info.get("duration_string", "N/A"), style="ItemLabel.TLabel", foreground="#bbb").pack(pady=(0, 5), anchor="w")

            # Individual Download Button
            download_btn = ttk.Button(info_button_frame, text="Download", style="ItemButton.TButton",
                                      command=lambda url=item_info.get('url'), title=title: self.start_single_download(url, title))
            download_btn.pack(pady=(0, 5), anchor="w")

            item_frame.grid_columnconfigure(1, weight=1) # Make info_button_frame expand

        self.canvas.yview_moveto(0) # Scroll to top after loading all items
        self.canvas.update_idletasks() # Ensure scroll region is updated

    def start_single_download(self, media_url, title):
        """Initiates download for a single media item."""
        if self.download_in_progress:
            messagebox.showinfo("Please Wait", "Another download is already in progress.")
            return

        if not self.output_path.get():
            messagebox.showerror("Error", "Please choose a download location first.")
            return

        self.download_in_progress = True
        self.analyze_button.config(state=tk.DISABLED)

        self.update_status(f"Starting download for: {title[:70]}...")
        self.progress['value'] = 0
        self.progress.start()

        threading.Thread(target=self._download_video_task, args=(media_url, title), daemon=True).start()

    def _download_video_task(self, url, title_for_display="Unknown Title"):
        """Threaded task for downloading video, taking a single URL."""
        try:
            ydl_opts = self.get_common_ydl_opts()
            
            # Sanitize title for filename here, as it's for a single item download
            sanitized_title = re.sub(r'[\\/:*?"<>|]', '', title_for_display)
            sanitized_title = sanitized_title[:100].strip() # Truncate and strip whitespace
            if not sanitized_title: # Fallback if title becomes empty after sanitization
                sanitized_title = f"video_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

            ydl_opts['outtmpl'] = os.path.join(self.output_path.get(), f'{sanitized_title}.%(ext)s')

            # Ensure 'quiet' is False during development for console output
            ydl_opts['quiet'] = False 
            ydl_opts['no_warnings'] = False 

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.master.after(0, lambda: self.update_status(f"Download complete: {title_for_display}"))
            self.master.after(0, lambda: messagebox.showinfo("Success", f"'{title_for_display}' downloaded successfully!"))

        except yt_dlp.utils.DownloadError as e:
            self.master.after(0, lambda: self.update_status(f"Download Error: {e}"))
            self.master.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download '{title_for_display}':\n{e}\n\nCheck URL, internet connection, or try updating yt-dlp.\n\nCheck console for more details."))
        except Exception as e:
            self.master.after(0, lambda: self.update_status(f"An error occurred: {e}"))
            self.master.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred for '{title_for_display}':\n{e}\n\nCheck console for more details."))
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
            'ffmpeg_location': 'ffmpeg',
            'retries': 5,
            'fragment_retries': 5,
            'extractor_retries': 3,
            'postprocessors': [],
            'cookiefile': None,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            },
            'no_warnings': True,
            'quiet': True,
            'noplaylist': True, # Important: Set to True when downloading a single item from a playlist list
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
        else: # "best"
            opts['format'] = "bestvideo+bestaudio/best"
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