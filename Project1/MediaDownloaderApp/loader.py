import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

def update_progress(current, max_value):
    progress_var.set(current)
    if current < max_value:
        splash.after(50, update_progress, current + 5, max_value)
    else:
        splash.destroy()
        root.deiconify()

# Main App Window (hidden initially)
root = tk.Tk()
root.withdraw()

# Splash Screen
splash = tk.Toplevel()
splash.overrideredirect(True)
splash.geometry("400x300+600+300")
splash.configure(bg="#2C3E50")

# Image or Logo (optional)
img = Image.open("MediaDownloaderApp/LOGO.png")  # Replace with actual image file
img = img.resize((100, 100))
photo = ImageTk.PhotoImage(img)
logo = tk.Label(splash, image=photo, bg="#2C3E50")
logo.pack(pady=10)

# Welcome Label
welcome = tk.Label(splash, text="Loading Your App...",
                   font=("Segoe UI", 16), fg="white", bg="#2C3E50")
welcome.pack(pady=10)

# Progress Bar
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(splash, variable=progress_var,
                               maximum=100, length=250, mode='determinate')
progress_bar.pack(pady=20)

# Start Loading
update_progress(0, 100)

# Main Window Setup
root.title("Main Application")
root.geometry("600x400")
main_label = tk.Label(root, text="Hello Ferdous! 🎉 Your app is ready.",
                      font=("Segoe UI", 14))
main_label.pack(pady=50)

root.mainloop()

