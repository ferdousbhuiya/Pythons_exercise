import yt_dlp
import tkinter as tk
from tkinter import filedialog, messagebox, Canvas, Scrollbar, Frame, ttk
from PIL import Image, ImageTk
import requests
import io
import threading
import os
import datetime

class MediaDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Media Downloader by Ferdous")
        self.root.configure(bg="#e0d7ca")
        self.root.geometry("1080x800")
        self.media_results = []
        self.save_path = ""

        # --- Input Frame ---
        input_frame = Frame(root, bg="#d9eb76")
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="🔗 Media URL:", font=("Segoe UI", 11, "bold"), bg="#d9eb76").grid(row=0, column=0, padx=5)
        self.url_entry = tk.Entry(input_frame, width=80, font=("Segoe UI", 10))
        self.url_entry.grid(row=0, column=1, padx=5)

        tk.Label(input_frame, text="🎞 Format:", font=("Segoe UI", 10), bg="#d9eb76").grid(row=1, column=0, sticky="w", padx=5)
        self.format_combo = ttk.Combobox(input_frame, values=["Best", "MP4", "MP3"], state="readonly", width=10)
        self.format_combo.current(0)
        self.format_combo.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.folder_label = tk.Label(input_frame, text="No folder selected", bg="#d9eb76", fg="#555")
        self.folder_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=5)

        tk.Button(input_frame, text="📁 Browse Folder", font=("Segoe UI", 10), bg="#f28c8c", fg="white",
                  command=self.choose_folder).grid(row=3, column=0, padx=5, pady=5, sticky="w")
        tk.Button(input_frame, text="🔍 Fetch Media", font=("Segoe UI", 10, "bold"), bg="#4CAF50", fg="white",
                  command=self.fetch_media).grid(row=3, column=1, padx=5, pady=5, sticky="e")

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
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

        # --- Progress Bar ---
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        # --- Download History ---
        history_frame = Frame(root, bg="#e0d7ca")
        history_frame.pack(fill="both", expand=False)
        tk.Label(history_frame, text="📜 Download History", font=("Segoe UI", 10, "bold"), bg="#e0d7ca").pack(anchor="w", padx=10, pady=(5,0))
        self.history_list = tk.Listbox(history_frame, height=5, font=("Segoe UI", 10))
        self.history_list.pack(fill="x", padx=10, pady=(0,10))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        direction = -1 if event.num == 4 else 1
        self.canvas.yview_scroll(direction, "units")

    def choose_folder(self):
        self.save_path = filedialog.askdirectory()
        self.folder_label.config(text=self.save_path if self.save_path else "No folder selected")

    def fetch_media(self):
        link = self.url_entry.get().strip()
        if not link or not self.save_path:
            messagebox.showerror("Error", "Please enter a link and select a folder.")
            return

        for widget in self.scrollable_content.winfo_children():
            widget.destroy()

        try:
            self.media_results = self.get_media_thumbnails(link)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch media: {e}")
            return

        if self.media_results:
            self.show_thumbnails()
        else:
            messagebox.showinfo("Info", "No media found.")

    def get_media_thumbnails(self, url):
        ydl_opts = {'quiet': True, 'extract_flat': True, 'force_generic_extractor': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get('entries', [])
            return [{'title': entry.get('title'), 'url': entry.get('url'), 'thumbnail': entry.get('thumbnail')} for entry in entries]

    def show_thumbnails(self):
        for result in self.media_results:
            container = Frame(self.scrollable_content, bg="white", bd=1, relief="solid")
            container.pack(fill="x", pady=10, padx=10)

            try:
                response = requests.get(result['thumbnail'], timeout=5)
                img_data = response.content
                img = Image.open(io.BytesIO(img_data)).resize((200, 112))
                tk_img = ImageTk.PhotoImage(img)
                thumbnail = tk.Label(container, image=tk_img, bg="white")
                thumbnail.image = tk_img
                thumbnail.pack(side="left", padx=10)
            except:
                tk.Label(container, text="No Image", bg="white", width=25).pack(side="left", padx=10)

            info_frame = Frame(container, bg="white")
            info_frame.pack(side="left", fill="x", expand=True)

            tk.Label(info_frame, text=result['title'], font=("Segoe UI", 10), bg="white", anchor="w", justify="left", wraplength=600).pack(fill="x", pady=(10, 5))
            
            def make_download_callback(url=result['url'], title=result['title']):
                return lambda: threading.Thread(target=self.download_media, args=(url, title)).start()

            tk.Button(info_frame, text="⬇️ Download", font=("Segoe UI", 10, "bold"), bg="#2e86de", fg="white",
                      command=make_download_callback()).pack(anchor="w", padx=10, pady=(0, 10))

    def download_media(self, media_url, title):
        format_choice = self.format_combo.get()
        subfolder = os.path.join(self.save_path, format_choice)
        os.makedirs(subfolder, exist_ok=True)

        ydl_opts = {
            'outtmpl': f'{subfolder}/%(title)s.%(ext)s',
            'quiet': False,
            'progress_hooks': [self.update_progress]
        }

        if format_choice == "MP3":
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
        elif format_choice == "MP4":
            ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4'})
        else:
            ydl_opts.update({'format': 'best'})

        try:
            self.progress.start()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([media_url])
            self.progress.stop()
            self.progress["value"] = 0

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history_list.insert(0, f"{timestamp} - {title}")
            messagebox.showinfo("✅ Download Complete", f"{title} has been downloaded.")
        except Exception as e:
            self.progress.stop()
            self.progress["value"] = 0
            messagebox.showerror("Download Error", str(e))

    def update_progress(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '').strip('%') or "0"
            try:
                self.progress["value"] = float(percent)
                self.root.update_idletasks()
            except:
                pass

# --- Launch App ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MediaDownloaderApp(root)
    root.mainloop()