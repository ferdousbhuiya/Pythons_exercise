# cookie_extractor.py
import browser_cookie3
import http.cookiejar
import os
import sys

def extract_facebook_cookies():
    """Extract Facebook cookies from browser"""
    print("Attempting to extract Facebook cookies from your browser...")
    
    # Try different browsers in order of preference
    browsers = [
        ('Chrome', browser_cookie3.chrome),
        ('Firefox', browser_cookie3.firefox),
        ('Edge', browser_cookie3.edge),
        ('Safari', browser_cookie3.safari),
        ('Opera', browser_cookie3.opera),
        ('Brave', browser_cookie3.brave)
    ]
    
    cookies = None
    browser_name = None
    
    for name, browser_func in browsers:
        try:
            print(f"Trying {name}...")
            cookies = browser_func(domain_name='.facebook.com')
            browser_name = name
            print(f"Successfully found cookies from {name}!")
            break
        except Exception as e:
            print(f"  {name}: {str(e)}")
            continue
    
    if not cookies:
        print("\n❌ Could not extract cookies from any browser.")
        print("\nPossible reasons:")
        print("1. You're not logged into Facebook in any browser")
        print("2. Browser cookies are encrypted or protected")
        print("3. Browser is not installed or accessible")
        print("\nAlternative methods:")
        print("1. Use browser extension 'Cookie Editor'")
        print("2. Manually copy cookies from browser developer tools")
        return False
    
    # Create cookies.txt file
    cookie_file = 'cookies.txt'
    
    try:
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# https://curl.se/rfc/cookie_spec.html\n")
            f.write(f"# Generated from {browser_name} browser\n")
            f.write("# This file contains Facebook cookies for video downloading\n\n")
            
            cookie_count = 0
            for cookie in cookies:
                # Format: domain, domain_specified, path, secure, expires, name, value
                f.write(f"{cookie.domain}\t")
                f.write("TRUE\t")
                f.write(f"{cookie.path}\t")
                f.write("TRUE\t")
                f.write(f"{int(cookie.expires) if cookie.expires else 0}\t")
                f.write(f"{cookie.name}\t")
                f.write(f"{cookie.value}\n")
                cookie_count += 1
        
        print(f"\n✅ Successfully extracted {cookie_count} Facebook cookies!")
        print(f"📁 Cookie file saved as: {os.path.abspath(cookie_file)}")
        
        # Verify important cookies
        important_cookies = ['c_user', 'xs', 'datr', 'sb', 'fr']
        found_cookies = [cookie.name for cookie in cookies]
        
        print("\n🔍 Checking for important cookies:")
        for cookie_name in important_cookies:
            if cookie_name in found_cookies:
                print(f"  ✅ {cookie_name}")
            else:
                print(f"  ⚠️  {cookie_name} (not found)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error saving cookie file: {str(e)}")
        return False

def verify_cookie_file():
    """Verify that the cookie file exists and has content"""
    cookie_file = 'cookies.txt'
    
    if not os.path.exists(cookie_file):
        print(f"❌ Cookie file '{cookie_file}' not found!")
        return False
    
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            print(f"❌ Cookie file '{cookie_file}' is empty!")
            return False
        
        lines = content.strip().split('\n')
        cookie_lines = [line for line in lines if line and not line.startswith('#')]
        
        print(f"✅ Cookie file verified: {len(cookie_lines)} cookies found")
        return True
        
    except Exception as e:
        print(f"❌ Error reading cookie file: {str(e)}")
        return False

def main():
    print("🍪 Facebook Cookie Extractor")
    print("=" * 40)
    
    # Check if browser-cookie3 is installed
    try:
        import browser_cookie3
    except ImportError:
        print("❌ Required package 'browser-cookie3' not found!")
        print("\nTo install it, run:")
        print("pip install browser-cookie3")
        return
    
    # Extract cookies
    if extract_facebook_cookies():
        print("\n🎉 Cookie extraction completed successfully!")
        
        # Verify the file
        print("\n🔍 Verifying cookie file...")
        if verify_cookie_file():
            print("\n✅ You can now use the video downloader with Facebook private content!")
            print("\n📝 Next steps:")
            print("1. Run your SecondGen.py video downloader")
            print("2. Try downloading a Facebook video/reel")
            print("3. The downloader will automatically use the cookies.txt file")
        else:
            print("\n⚠️  Cookie file verification failed!")
    else:
        print("\n❌ Cookie extraction failed!")
        print("\n📋 Manual cookie extraction instructions:")
        print("1. Install 'Cookie Editor' browser extension")
        print("2. Go to Facebook.com and log in")
        print("3. Click Cookie Editor extension icon")
        print("4. Export as 'Netscape HTTP Cookie File'")
        print("5. Save as 'cookies.txt' in your script directory")

if __name__ == "__main__":
    main()