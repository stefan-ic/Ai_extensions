# tools.py
import requests
from ddgs import DDGS

def search_web(query, max_results=5, use_tor=False):
    network_name = "Tor Network" if use_tor else "Surface Web"
    print(f"\n[*] Searching the {network_name} for: '{query}'...")
    
    try:
        context = ""
        if use_tor:
            tor_proxy = "socks5h://127.0.0.1:9050"
            with DDGS(proxy=tor_proxy) as ddgs:
                for res in ddgs.text(query, max_results=max_results):
                    context += f"- {res['title']}: {res['body']}\n"
        else:
            with DDGS() as ddgs:
                for res in ddgs.text(query, max_results=max_results, backend="html"):
                    context += f"- {res['title']}: {res['body']}\n"
                    
        return context
    except Exception as e:
        print(f"[!] Error searching the web. Details: {e}")
        return ""

def check_connection_ip(use_tor=False):
    print("[*] Checking current public IP...")
    try:
        proxies = {}
        if use_tor:
            proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
        
        response = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=10)
        response.raise_for_status()
        current_ip = response.json().get('ip')
        
        network = "Tor Network" if use_tor else "Surface Web"
        print(f"[*] Success! Routed through {network}. Visible IP: {current_ip}\n")
    except Exception as e:
        print(f"[!] IP check failed. Tor mode active: {use_tor}. Error: {e}\n")