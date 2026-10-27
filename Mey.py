import requests
import json
import os
import time 
from ddgs import DDGS

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "richardyoung/llama-3.1-8b-instruct-abliterated"

# Memory settings
MESSAGE_LIMIT = 10  
MAX_SENTENCES = 12  

BASE_SYSTEM_PROMPT = """You are an AI assistant and my friend. You help me build projects. 
CRITICAL RULE: Use the conversation history and technical changelog to maintain context. However, if the user asks about a new topic that is NOT in the history, simply answer the question directly. DO NOT pretend or invent that we discussed it before.
If internet search results are provided, use them as supplementary knowledge."""

project_summary = ""
conversation_history = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]

# Network state flag
use_tor_mode = False

def get_search_queries(user_message):
    """Asks the AI to break down the prompt into multiple specific search queries."""
    decision_prompt = f"""Analyze this user message: "{user_message}"
Does it require looking up facts, documentation, or internet data to answer correctly?
- If NO, reply STRICTLY with the exact word 'NO'.
- If YES, break the request down into as many highly specific search queries as you need to fully cover the topic.

CRITICAL FORMAT RULES:
1. Output each query on a new line.
2. Every single line MUST start with '- '.
3. Generate exactly as many queries as needed (whether it's 1, 5, or 10 or more).

Example of a single query line:
- [Main Concept] [Specific Property]
"""
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a strict backend data-routing API. You output ONLY the word 'NO' or a bulleted list of raw search queries. No conversational text is permitted."},
            {"role": "user", "content": decision_prompt}
        ],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=data,timeout=300)
        response.raise_for_status()
        answer = response.json().get('message', {}).get('content', '').strip()
        
        if answer.upper() == "NO" or "NO" in answer.upper()[:10]:
            return []
            
        queries = []
        for line in answer.split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                queries.append(line[2:].strip().strip('"').strip("'"))
                
        return queries
    except Exception as e:
        print(f"[!] Routing error: {e}")
        return []

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
                for res in ddgs.text(query, max_results=max_results):
                    context += f"- {res['title']}: {res['body']}\n"
                    
        return context
    except Exception as e:
        print(f"[!] Error searching the web. Details: {e}")
        return ""

def check_connection_ip(use_tor=False):
    print("[*] Checking current public IP...")
    try:
        # Define the exact same proxy we use for DuckDuckGo
        proxies = {}
        if use_tor:
            proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
        
        # Ping a simple IP-checking API
        response = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=10)
        response.raise_for_status()
        current_ip = response.json().get('ip')
        
        network = "Tor Network" if use_tor else "Surface Web"
        print(f"[*] Success! Routed through {network}. Visible IP: {current_ip}\n")
    except Exception as e:
        print(f"[!] IP check failed. Tor mode active: {use_tor}. Error: {e}\n")

def generate_summary(old_messages, old_summary):
    print("\n[!] Memory is filling up. Updating technical changelog...")
    messages_text = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
    
    summary_prompt = f"""Update the existing project state with the new conversation. 
DO NOT write a narrative story. Write a strict technical state.
You MUST retain:
1. Exact names of variables, code functions, or libraries discussed.
2. Specific hardware details (pin numbers, dimensions, components, materials).
3. The exact problem we are currently trying to solve.
4. ANY specific preferences, instructions, or facts the user explicitly asked you to remember.
Keep the summary STRICTLY under {MAX_SENTENCES} sentences total.

Existing State: {old_summary if old_summary else "None yet."}

New Conversation to integrate:
{messages_text}"""
    
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": summary_prompt}],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=300)
        response.raise_for_status()
        return response.json().get('message', {}).get('content', '')
    except Exception:
        print("[!] Error generating summary. Keeping the old version.")
        return old_summary

def optimize_memory(history):
    global project_summary
    
    if len(history) > MESSAGE_LIMIT + 1:
        messages_to_delete = history[1:5]
        project_summary = generate_summary(messages_to_delete, project_summary)
        history[0]['content'] = f"{BASE_SYSTEM_PROMPT}\n\nCurrent Technical State (Changelog):\n{project_summary}"
        history = [history[0]] + history[5:]
        print("[!] Context updated successfully.\n")
        
    return history

def compress_search_results(query, raw_text):
    """Uses the AI to extract only the facts relevant to the query, shrinking the text footprint."""
    if not raw_text.strip():
        return ""
        
    prompt = f"""You are a data extraction tool. Analyze this raw web text for the query: '{query}'.
Extract ONLY the hard facts, numbers, and technical details relevant to the query. 
Write a highly dense, concise summary. Do NOT include conversational filler, disclaimers, or introductory text.

Raw Text:
{raw_text}"""
    
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=data,timeout=300)
        response.raise_for_status()
        return response.json().get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"[!] Compression error: {e}. Falling back to raw text slice.")
        return raw_text[:1000] # Safe fallback if the AI stumbles

def ask_ollama(user_message, web_context=""):
    global conversation_history
    
    if web_context:
        message_content = f"Information found on the web:\n{web_context}\n\nQuestion: {user_message}"
    else:
        message_content = user_message
        
    conversation_history.append({"role": "user", "content": message_content})
    conversation_history = optimize_memory(conversation_history)
    
    data = {
        "model": MODEL,
        "messages": conversation_history,
        "stream": True
    }

    print("[*] AI is generating the response...\n")
    try:
        response = requests.post(OLLAMA_URL, json=data, stream=True, timeout=300)
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                decoded_line = json.loads(line.decode('utf-8'))
                chunk = decoded_line.get('message', {}).get('content', '')
                full_response += chunk
                print(chunk, end='', flush=True)
        print("\n")
        
        conversation_history.append({"role": "assistant", "content": full_response})
        
    except requests.exceptions.RequestException as e:
        print(f"\n[!] Network or Timeout Error with Ollama: {e}")
        conversation_history.pop()

if __name__ == "__main__":
    print("=== Local AI Assistant | Rolling Memory & Auto-Routing ===")
    print("Type '!help!' to see the list of available commands.\n")
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if not user_input:
            continue
            
        command = user_input.lower()
        
        if command == '!help!':
            print("\n=== Available Commands ===")
            print(" !help!          - Shows this list of commands.")
            print(" exit            - Closes the assistant.")
            print(" clear           - Wipes the current session memory and project summary.")
            print(" save <name>     - Saves the project state to a .json file.")
            print(" load <name>     - Loads a project state from a .json file.")
            print(" !tor on         - Routes all future web searches through the Tor network (Port 9050).")
            print(" !tor off        - Routes web searches through your normal internet connection.")
            print(" !read <file> [instruction] - Reads a file and analyzes it based on your instruction.")
            print("                   (Use quotes for paths with spaces: !read \"C:\\file.txt\" check logic)")
            print("==========================\n")
            continue
            
        elif command == 'exit':
            break
            
        elif command == '!tor on':
            use_tor_mode = True
            print("[*] Tor mode ENABLED. Web searches will now be anonymized.")
            continue
        
        elif command == '!ip':
            check_connection_ip(use_tor=use_tor_mode)
            continue
            
        elif command == '!tor off':
            use_tor_mode = False
            print("[*] Tor mode DISABLED. Web searches are back to normal.")
            continue

        elif command.startswith('!read '):
            remainder = user_input[6:].strip()
            
            # Separate the file path from the instruction
            if remainder.startswith('"'):
                end_quote = remainder.find('"', 1)
                filepath = remainder[1:end_quote]
                instruction = remainder[end_quote+1:].strip()
            else:
                parts = remainder.split(' ', 1)
                filepath = parts[0]
                instruction = parts[1] if len(parts) > 1 else ""
            
            if not os.path.exists(filepath):
                print(f"[!] File '{filepath}' not found.")
                continue

            # Read the file and build the dynamic prompt (No size or extension limits)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                print("[*] File read successfully. Sending for analysis (hope you have enough VRAM)...")
                
                if instruction:
                    secret_prompt = f"Here is the content of the file '{filepath}':\n\n{file_content}\n\nUser instruction: {instruction}"
                else:
                    secret_prompt = f"Here is the content of the file '{filepath}':\n\n{file_content}\n\nPlease acknowledge you read it and summarize what it is."
                
                ask_ollama(secret_prompt, web_context="")
            except UnicodeDecodeError:
                print("[!] Error: File is not valid UTF-8 text (it's likely a binary or unsupported format).")
            except Exception as e:
                print(f"[!] Error reading file: {e}")
            continue

        elif command == 'clear':
            project_summary = ""
            conversation_history = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]
            print("[*] Session and summary completely cleared.")
            continue
            
        elif command.startswith('save '):
            file_name = user_input[5:].strip() + ".json"
            save_data = {
                "summary": project_summary,
                "history": conversation_history
            }
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4, ensure_ascii=False)
            print(f"[*] Project saved to '{file_name}'.")
            continue
            
        elif command.startswith('load '):
            file_name = user_input[5:].strip() + ".json"
            if os.path.exists(file_name):
                with open(file_name, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)
                
                project_summary = save_data.get("summary", "")
                conversation_history = save_data.get("history", [{"role": "system", "content": BASE_SYSTEM_PROMPT}])
                print(f"[*] Project loaded from '{file_name}'.")
            else:
                print(f"[!] Could not find save file '{file_name}'.")
            continue
            
       # Normal flow: The AI evaluates if it needs the internet and generates multiple queries
        web_context = ""
        queries_to_run = get_search_queries(user_input)
        
        if queries_to_run:
            network_type = "Tor Network" if use_tor_mode else "Surface Web"
            print(f"\n[*] AI decomposed the request into {len(queries_to_run)} targeted searches.")
            print(f"[*] Executing searches through the {network_type}...")
            
            for q in queries_to_run:
                raw_chunk = search_web(q, max_results=5, use_tor=use_tor_mode)
                if raw_chunk:
                    print(f"[*] Filtering and compressing data for: '{q}'...")
                    compressed_chunk = compress_search_results(q, raw_chunk)
                    web_context += f"--- Facts for: {q} ---\n{compressed_chunk}\n\n"
                    # Sleep for 2.5 seconds before the next search to prevent DDG rate limits
                    time.sleep(2.5)
                    
        else:
            print("\n[*] Answering from memory...")
            
        ask_ollama(user_input, web_context)