import urllib.request
import urllib.parse
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def check_proxy(proxy_str):
    proxy_str = proxy_str.strip()
    if not proxy_str or proxy_str.startswith('#'):
        return None
        
    # Parse proxy string
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://{proxy_str}',
        'https': f'http://{proxy_str}'
    })
    opener = urllib.request.build_opener(proxy_handler)
    
    try:
        # Test against Instagram's login page
        # Set a common User-Agent to avoid immediate block
        req = urllib.request.Request(
            "https://www.instagram.com/accounts/login/",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}
        )
        with opener.open(req, timeout=10) as response:
            if response.status == 200:
                print(f"✅ {proxy_str} - SUCCESS")
                return proxy_str
    except Exception:
        pass
    
    return None

def main():
    proxy_file = Path("proxies.txt")
    if not proxy_file.exists():
        print("proxies.txt not found.")
        return
        
    with open(proxy_file, "r") as f:
        lines = f.readlines()
        
    print(f"Checking {len(lines)} proxies...")
    
    valid_proxies = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(check_proxy, lines))
        valid_proxies = [r for r in results if r]
        
    with open("proxies.txt", "w") as f:
        for p in valid_proxies:
            f.write(p + "\n")
            
    print(f"Done! Saved {len(valid_proxies)} working proxies to proxies.txt")

if __name__ == "__main__":
    main()
