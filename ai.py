# ai.py
import requests
import json
from config import OLLAMA_URL, MODEL, MAX_SENTENCES, BASE_SYSTEM_PROMPT, MESSAGE_LIMIT

def get_search_queries(user_message):
    decision_prompt = f"""Analyze this user message: "{user_message}"

STEP 1: THINKING PROCESS
Evaluate the request. Do you already know the answer from general knowledge? Does it require real-time data or specific documentation?
Write your reasoning on a single line starting with "THINKING: ".

STEP 2: DECISION
If you already know the answer, reply EXACTLY with the word 'NO' on the next line and stop.
If you MUST search, output the highly specific search queries needed to fully cover the topic.

CRITICAL FORMAT RULES:
1. You must output the THINKING line first.
2. Queries must be on new lines.
3. Every query MUST start with '- '.
4. Generate only as many queries as strictly necessary. Do not bloat the search.

Example of a single query line:
- [Main Concept] [Specific Property]
""" 
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a strict data-routing API. Follow the formatting rules exactly. No conversational filler."},
            {"role": "user", "content": decision_prompt}
        ],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=300)
        response.raise_for_status()
        answer = response.json().get('message', {}).get('content', '').strip()
        
        lines = answer.split('\n')
        
        # If the AI decides no search is needed based on its thinking
        if any(line.strip().upper() == "NO" for line in lines):
            return []
            
        queries = []
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                queries.append(line[2:].strip().strip('"').strip("'"))
                
        return queries
    except Exception as e:
        print(f"[!] Routing error: {e}")
        return []

def compress_search_results(query, raw_text):
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
        response = requests.post(OLLAMA_URL, json=data, timeout=300)
        response.raise_for_status()
        return response.json().get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"[!] Compression error: {e}. Falling back to raw text slice.")
        return raw_text[:1000]

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

def optimize_memory(history, summary):
    if len(history) > MESSAGE_LIMIT + 1:
        messages_to_delete = history[1:5]
        summary = generate_summary(messages_to_delete, summary)
        history[0]['content'] = f"{BASE_SYSTEM_PROMPT}\n\nCurrent Technical State (Changelog):\n{summary}"
        history = [history[0]] + history[5:]
        print("[!] Context updated successfully.\n")
    return history, summary

def stream_ollama_response(messages):
    data = {
        "model": MODEL,
        "messages": messages,
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
        return full_response
    except requests.exceptions.RequestException as e:
        print(f"\n[!] Network or Timeout Error with Ollama: {e}")
        return None