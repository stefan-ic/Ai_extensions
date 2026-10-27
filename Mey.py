# main.py
import os
import json
import time
from config import BASE_SYSTEM_PROMPT
from tools import search_web, check_connection_ip
from ai import get_search_queries, compress_search_results, optimize_memory, stream_ollama_response

def print_help():
    print("\n=== Available Commands ===")
    print(" !help!          - Shows this list of commands.")
    print(" exit            - Closes the assistant.")
    print(" clear           - Wipes the current session memory and project summary.")
    print(" save <name>     - Saves the project state to a .json file.")
    print(" load <name>     - Loads a project state from a .json file.")
    print(" !tor on         - Routes all future web searches through the Tor network (Port 9050).")
    print(" !tor off        - Routes web searches through your normal internet connection.")
    print(" !read <file> [instruction] - Reads a file and analyzes it based on your instruction.")
    print("==========================\n")

if __name__ == "__main__":
    print("=== Local AI Assistant | Modular Architecture ===")
    print("Type '!help!' to see the list of available commands.\n")
    
    # State tracking initialized here instead of globally
    project_summary = ""
    conversation_history = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]
    use_tor_mode = False
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if not user_input:
            continue
            
        command = user_input.lower()
        
        if command == '!help!':
            print_help()
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

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                print("[*] File read successfully. Sending for analysis...")
                if instruction:
                    secret_prompt = f"Here is the content of the file '{filepath}':\n\n{file_content}\n\nUser instruction: {instruction}"
                else:
                    secret_prompt = f"Here is the content of the file '{filepath}':\n\n{file_content}\n\nPlease acknowledge you read it and summarize what it is."
                
                # Direct injection for file dumps (bypasses memory limits)
                stream_ollama_response([{"role": "user", "content": secret_prompt}])
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
            
        # Core Web Search & Routing Flow
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
                    time.sleep(2.5) 
        else:
            print("\n[*] Answering from memory...")
            
        # Compile Context & Manage Memory
        if web_context:
            message_content = f"Information found on the web:\n{web_context}\n\nQuestion: {user_input}"
        else:
            message_content = user_input
            
        conversation_history.append({"role": "user", "content": message_content})
        conversation_history, project_summary = optimize_memory(conversation_history, project_summary)
        
        # Execute Final Generation
        final_answer = stream_ollama_response(conversation_history)
        
        if final_answer:
            conversation_history.append({"role": "assistant", "content": final_answer})
        else:
            # Drop the failed request from history so it doesn't corrupt the prompt stack
            conversation_history.pop()