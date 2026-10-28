# tools.py
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

def scrape_url(url, use_tor=False):
    """Visits a URL and extracts the actual readable text from the webpage."""
    try:
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'} if use_tor else None
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:3000]
    except Exception:
        return ""

def search_web(query, max_results=2, use_tor=False):
    network_name = "Tor Network" if use_tor else "Surface Web"
    print(f"\n[*] Searching the {network_name} for: '{query}'...")
    
    try:
        context = ""
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, backend="html"))
            
            for res in results:
                url = res.get('href')
                print(f"    -> Reading website: {url}")
                
                page_text = scrape_url(url, use_tor)
                
                if page_text:
                    context += f"--- Source: {url} ---\n{page_text}\n\n"
                else:
                    context += f"--- Source (Snippet): {url} ---\n{res.get('body', '')}\n\n"
                    
        return context
    except Exception as e:
        print(f"[!] Error searching the web. Details: {e}")
        return ""

def check_connection_ip(use_tor=False):
    print("[*] Checking current public IP...")
    try:
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'} if use_tor else None
        response = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=10)
        response.raise_for_status()
        current_ip = response.json().get('ip')
        
        network = "Tor Network" if use_tor else "Surface Web"
        print(f"[*] Success! Routed through {network}. Visible IP: {current_ip}\n")
    except Exception as e:
        print(f"[!] IP check failed. Tor mode active: {use_tor}. Error: {e}\n")