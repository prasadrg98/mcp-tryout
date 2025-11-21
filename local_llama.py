import requests
import json
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Ollama library not installed. Install with: pip install ollama")

def query_local_llama(prompt):
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": "llama3.2:1b",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(url, json=payload)
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def query_local_llama_streaming(prompt):
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": "llama3.2:1b",
        "prompt": prompt,
        "stream": True
    }

    response = requests.post(url, json=payload, stream=True)

    if response.status_code == 200:
        full_response = ""
        print("Streaming response:")
        
        for line in response.iter_lines():
            if line:
                try:
                    # Each line is a JSON object
                    chunk = json.loads(line.decode('utf-8'))

                    # Get the response part from this chunk
                    if 'response' in chunk:
                        chunk_text = chunk['response']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)

                    # Check if this is the final chunk
                    if chunk.get('done', False):
                        print("\n\nStreaming complete!")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        return full_response
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def query_local_llama_ollama(prompt, stream=False):
    """
    Query local Llama using the ollama library
    This is the simplest and most pythonic way to interact with Ollama
    """
    if not OLLAMA_AVAILABLE:
        print("Ollama library is not available. Please install it with: pip install ollama")
        return None
    
    ollama.Client()

    try:
        if stream:
            print("Ollama library streaming response:")
            full_response = ""
            
            # Use ollama library's streaming capability
            stream_response = ollama.generate(
                model='llama3.2:1b',
                prompt=prompt,
                stream=True
            )
            
            for chunk in stream_response:
                if 'response' in chunk:
                    chunk_text = chunk['response']
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)
                
                if chunk.get('done', False):
                    print("\n\nOllama streaming complete!")
                    break
            
            return full_response
        else:
            # Non-streaming response using ollama library
            response = ollama.generate(
                model='llama3.2:1b',
                prompt=prompt
            )
            return response['response']
            
    except Exception as e:
        print(f"Error using ollama library: {e}")
        return None

# # Test the non-streaming function
# print("=== Non-streaming response ===")
# result = query_local_llama("Hello, world!")
# if result:
#     print("Response:", result.get('response', 'No response field found'))
#     print()

# # Test the streaming function
# print("=== Streaming response (requests) ===")
# streaming_result = query_local_llama_streaming("Tell me a short joke about programming.")
# if streaming_result:
#     print(f"\nComplete response: {streaming_result}")

# print("\n" + "="*50 + "\n")

# Test the ollama library function (non-streaming)
print("=== Ollama library (non-streaming) ===")
ollama_result = query_local_llama_ollama("What is Python?")
if ollama_result:
    print(f"Response: {ollama_result}")

print("\n" + "="*50 + "\n")

# Test the ollama library function (streaming)
print("=== Ollama library (streaming) ===")
ollama_streaming_result = query_local_llama_ollama("Explain what machine learning is in simple terms.", stream=True)
if ollama_streaming_result:
    print(f"\nComplete response: {ollama_streaming_result}")