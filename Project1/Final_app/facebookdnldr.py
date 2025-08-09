# Simple test script to check what works
import yt_dlp

def test_youtube():
    print("Testing YouTube...")
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'skip_download': True,
        'simulate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"✅ YouTube works! Found: {info.get('title', 'Unknown')}")
            return True
    except Exception as e:
        print(f"❌ YouTube failed: {e}")
        return False

def test_facebook():
    print("\nTesting Facebook...")
    url = "https://www.facebook.com/watch?v=1090311585792060"
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'skip_download': True,
        'simulate': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"✅ Facebook works! Found: {info.get('title', 'Unknown')}")
            return True
    except Exception as e:
        print(f"❌ Facebook failed: {e}")
        return False

if __name__ == "__main__":
    import os
    test_youtube()
    test_facebook()