import yt_dlp
import tkinter as tk
from tkinter import filedialog, messagebox, Canvas, Scrollbar, Frame, ttk
from PIL import Image, ImageTk
import requests
import io
import threading
import os
import datetime
import re # Import regex for sanitizing filenames

class MediaDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Media Downloader by Ferdous")
        self.root.configure(bg="#e0d7ca")
        self.root.geometry("1080x800")
        self.media_results = []
        self.save_path = ""
        self.download_in_progress = False # Flag to prevent multiple concurrent downloads

        # --- Input Frame ---
        input_frame = Frame(root, bg="#d9eb76", padx=10, pady=10)
        input_frame.pack(pady=10, fill="x")

        tk.Label(input_frame, text="🔗 Media URL:", font=("Segoe UI", 11, "bold"), bg="#d9eb76").grid(row=0, column=0, padx=5, sticky="w")
        self.url_entry = tk.Entry(input_frame, width=80, font=("Segoe UI", 10))
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(input_frame, text="🎞 Format:", font=("Segoe UI", 10), bg="#d9eb76").grid(row=1, column=0, sticky="w", padx=5)
        self.format_combo = ttk.Combobox(input_frame, values=["Best", "MP4", "MP3"], state="readonly", width=10)
        self.format_combo.current(0)
        self.format_combo.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.folder_label = tk.Label(input_frame, text="No folder selected", bg="#d9eb76", fg="#555", anchor="w")
        self.folder_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))

        tk.Button(input_frame, text="📁 Browse Folder", font=("Segoe UI", 10), bg="#f28c8c", fg="white",
                  command=self.choose_folder).grid(row=3, column=0, padx=5, pady=5, sticky="w")
        tk.Button(input_frame, text="🔍 Fetch Media", font=("Segoe UI", 10, "bold"), bg="#4CAF50", fg="white",
                  command=self.fetch_media_thread).grid(row=3, column=1, padx=5, pady=5, sticky="e")

        # Configure column weights for input_frame
        input_frame.grid_columnconfigure(1, weight=1)

        # --- Preview Frame ---
        self.preview_frame = Frame(root)
        self.preview_frame.pack(fill="both", expand=True)

        self.canvas = Canvas(self.preview_frame, bg="#fdf6ec")
        self.scrollbar = Scrollbar(self.preview_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = Frame(self.canvas, bg="#fdf6ec")

        self.scrollable_content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux) # For Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux) # For Linux scroll down

        # --- Progress Bar ---
        self.progress_frame = Frame(root, bg="#e0d7ca")
        self.progress_frame.pack(pady=(0,10), fill="x", padx=10) # Added padx
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(fill="x", expand=True)
        self.progress_label = tk.Label(self.progress_frame, text="Ready", bg="#e0d7ca", fg="#555")
        self.progress_label.pack(pady=5)

        # --- Download History ---
        history_frame = Frame(root, bg="#e0d7ca")
        history_frame.pack(fill="both", expand=False)
        tk.Label(history_frame, text="📜 Download History", font=("Segoe UI", 10, "bold"), bg="#e0d7ca").pack(anchor="w", padx=10, pady=(5,0))
        self.history_list = tk.Listbox(history_frame, height=5, font=("Segoe UI", 10), relief="groove", bd=2) # Added relief and bd
        self.history_list.pack(fill="x", padx=10, pady=(0,10))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        direction = -1 if event.num == 4 else 1
        self.canvas.yview_scroll(direction, "units")

    def choose_folder(self):
        chosen_path = filedialog.askdirectory()
        if chosen_path:
            self.save_path = chosen_path
            self.folder_label.config(text=f"Save to: {self.save_path}")
        else:
            self.folder_label.config(text="No folder selected")

    def fetch_media_thread(self):
        """Starts fetching media in a separate thread to keep GUI responsive."""
        link = self.url_entry.get().strip()
        if not link or not self.save_path:
            messagebox.showerror("Error", "Please enter a link and select a folder.")
            return

        for widget in self.scrollable_content.winfo_children():
            widget.destroy() # Clear previous results

        self.progress_label.config(text="Fetching media info...")
        self.progress.start()
        threading.Thread(target=self._fetch_media_task, args=(link,)).start()

    def _fetch_media_task(self, link):
        """Task to be run in a separate thread for fetching media info."""
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True, # Only extract basic info, don't go deep into formats
                # Removed 'force_generic_extractor': Let yt-dlp use specific extractors like Facebook's
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                # For single videos, info itself is the entry. For playlists, it has 'entries'.
                if 'entries' in info:
                    self.media_results = [{'title': entry.get('title'), 'url': entry.get('url'), 'thumbnail': entry.get('thumbnail')} for entry in info.get('entries', [])]
                else:
                    self.media_results = [{'title': info.get('title'), 'url': info.get('original_url', info.get('url')), 'thumbnail': info.get('thumbnail')}]

            self.root.after(0, self.show_thumbnails_gui) # Update GUI on main thread
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch media: {e}\nCheck URL or your internet connection."))
            self.root.after(0, self.reset_progress)
        finally:
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.progress["value"] == 0) # Reset progress bar value

    def show_thumbnails_gui(self):
        """Updates the GUI with thumbnails on the main thread."""
        self.progress_label.config(text="Ready")
        if self.media_results:
            for result in self.media_results:
                container = Frame(self.scrollable_content, bg="white", bd=1, relief="solid")
                container.pack(fill="x", pady=5, padx=10) # Reduced pady for closer packing

                # Handle potential missing thumbnail or errors
                tk_img = None
                if result.get('thumbnail'):
                    try:
                        response = requests.get(result['thumbnail'], timeout=5)
                        img_data = response.content
                        img = Image.open(io.BytesIO(img_data)).resize((160, 90), Image.LANCZOS) # Smaller size for better performance
                        tk_img = ImageTk.PhotoImage(img)
                    except Exception as img_e:
                        print(f"Failed to load thumbnail for {result.get('title')}: {img_e}")
                        # Fallback to no image label if thumbnail fails
                
                if tk_img:
                    thumbnail = tk.Label(container, image=tk_img, bg="white")
                    thumbnail.image = tk_img # Keep a reference
                    thumbnail.pack(side="left", padx=10, pady=5)
                else:
                    tk.Label(container, text="No Image", bg="white", width=20, height=5, relief="groove").pack(side="left", padx=10, pady=5)


                info_frame = Frame(container, bg="white")
                info_frame.pack(side="left", fill="x", expand=True)

                tk.Label(info_frame, text=result.get('title', 'Untitled Media'), font=("Segoe UI", 10, "bold"), bg="white", anchor="w", justify="left", wraplength=700).pack(fill="x", pady=(5, 2))
                tk.Label(info_frame, text=result.get('url', 'No URL available'), font=("Segoe UI", 8), bg="white", fg="#777", anchor="w", justify="left", wraplength=700).pack(fill="x", pady=(0, 5))
                
                def make_download_callback(url=result['url'], title=result['title']):
                    return lambda: threading.Thread(target=self.download_media, args=(url, title)).start()

                tk.Button(info_frame, text="⬇️ Download", font=("Segoe UI", 10, "bold"), bg="#2e86de", fg="white",
                          command=make_download_callback()).pack(anchor="w", padx=10, pady=(0, 5))
            self.canvas.yview_moveto(0) # Scroll to top after loading thumbnails
        else:
            messagebox.showinfo("Info", "No media found for the given URL.")
        
        self.canvas.update_idletasks() # Update canvas scroll region after adding content

    def download_media(self, media_url, title):
        if self.download_in_progress:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait.")
            return
        
        self.download_in_progress = True
        self.progress_label.config(text=f"Downloading: {title[:50]}...")
        self.progress.start()
        
        format_choice = self.format_combo.get()
        
        # Sanitize title for filename
        sanitized_title = re.sub(r'[\\/:*?"<>|]', '', title) # Remove illegal characters
        sanitized_title = sanitized_title[:100] # Truncate to avoid extremely long filenames
        
        subfolder = os.path.join(self.save_path, format_choice)
        os.makedirs(subfolder, exist_ok=True)

        ydl_opts = {
            'outtmpl': f'{subfolder}/{sanitized_title}.%(ext)s',
            'quiet': False, # Keep False for debugging output in the console
            'progress_hooks': [self.update_progress],
            'retries': 5, # Retry failed connections
            'fragment_retries': 5, # Retry failed fragments
            'extractor_retries': 5, # Retry extractor errors
            'writeinfojson': False, # Don't write .json info file by default
            'writedescription': False, # Don't write description by default
            'writethumbnail': False, # Not downloading thumbnail with main video by default
            'updatetime': False, # Don't update file modification time
        }

        # Specific options for different formats
        if format_choice == "MP3":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': ['-metadata', f'title={sanitized_title}', '-metadata', f'artist=yt-dlp']
            })
        elif format_choice == "MP4":
            # Select best video and best audio, then merge them into mp4
            ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4'})
        else: # "Best" option
            # Downloads best video and best audio separately, then merges into a single file
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4' # Ensure merging to MP4
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([media_url])
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.root.after(0, lambda: self.history_list.insert(0, f"{timestamp} - {title[:100]}"))
            self.root.after(0, lambda: messagebox.showinfo("✅ Download Complete", f"{title} has been downloaded to {subfolder}"))

        except yt_dlp.utils.DownloadError as de:
            self.root.after(0, lambda: messagebox.showerror("Download Error", f"yt-dlp Download Error: {de}\n\nCommon causes for Facebook:\n1. Private video/Login required.\n2. Geoblocking.\n3. Facebook changed layout (try updating yt-dlp).\n4. FFmpeg missing (for MP3/some MP4s)."))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Unexpected Error", f"An unexpected error occurred: {str(e)}"))
        finally:
            self.root.after(0, self.reset_progress)
            self.download_in_progress = False # Reset flag

    def update_progress(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes:
                percent = (downloaded_bytes / total_bytes) * 100
                self.root.after(0, lambda: self.progress.config(value=percent))
                # Update progress label with more detail
                speed = d.get('speed_str', 'N/A')
                eta = d.get('eta_str', 'N/A')
                self.root.after(0, lambda: self.progress_label.config(text=f"Downloading: {d.get('filename', 'Unknown')} {d.get('_percent_str', '')} at {speed} ETA {eta}"))
            else:
                # Fallback if total_bytes is not immediately available (e.g., live streams)
                self.root.after(0, lambda: self.progress.config(mode="indeterminate")) # Switch to indeterminate mode
                self.root.after(0, lambda: self.progress_label.config(text=f"Downloading: {d.get('filename', 'Unknown')} {d.get('_percent_str', '')}"))
        elif d['status'] == 'finished':
            self.root.after(0, self.reset_progress) # Reset when finished
        
        self.root.after(0, self.root.update_idletasks) # Update GUI elements

    def reset_progress(self):
        self.progress.stop()
        self.progress["value"] = 0
        self.progress.config(mode="determinate") # Reset to determinate mode
        self.progress_label.config(text="Ready")

# --- Launch App ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MediaDownloaderApp(root)
    root.mainloop()