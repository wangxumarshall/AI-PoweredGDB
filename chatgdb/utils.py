import json
import sys # Added
from posixpath import dirname
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from os.path import abspath, dirname
from inspect import getfile, currentframe


def get_key():
    """Gets api key from secret file

    Returns: (str) api key
    Raises: FileNotFoundError: If the secret file is not found.
    """
    key = []
    secret = ""
    # gets path of this script - OS independent
    path = dirname(abspath(getfile(currentframe()))) + "/.secret.txt"
    try:
        # get appropriate api key
        with open(path) as f:
            key = [line.strip() for line in f]
        for k in key:
            if k.startswith("OPENAI_KEY"):
                secret = k.split('"')[1::2]
        if not secret: # Check if secret was actually found
            raise FileNotFoundError(f"OPENAI_KEY not found in {path}")
    except FileNotFoundError:
        # Re-raise to be caught by the caller, or let it propagate
        # Adding a more specific print here might be redundant if caller handles it well.
        raise FileNotFoundError(
            f"Could not find api key file at {path}. "
            f"Please make sure you've run the CLI tool and set up your API key."
        )

    return secret[0]


def get_model():
    """Gets model from model file

    Returns: (str) model
    Raises: FileNotFoundError: If the model file is not found.
    """
    model = []
    model_name = ""
    # gets path of this script - OS independent
    path = dirname(abspath(getfile(currentframe()))) + "/.model.txt"
    try:
        # get appropriate api key
        with open(path) as f:
            model = [line.strip() for line in f]
        for m in model:
            if m.startswith("MODEL"):
                model_name = m.split('"')[1::2]
        if not model_name: # Check if model_name was actually found
            raise FileNotFoundError(f"MODEL not found in {path}")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Could not find model file at {path}. "
            f"Please make sure you've run the CLI tool and set up your model."
        )

    return model_name[0]

def get_url():
    """Gets api url from url file

    Returns: (str) url
    Raises: FileNotFoundError: If the url file is not found.
    """
    url = []
    url_name = ""
    # gets path of this script - OS independent
    path = dirname(abspath(getfile(currentframe()))) + "/.url.txt"
    try:
        # get appropriate api url
        with open(path) as f:
            url = [line.strip() for line in f]
        for u in url:
            if u.startswith("URL"):
                url_name = u.split('"')[1::2]
        if not url_name: # Check if url_name was actually found
            raise FileNotFoundError(f"URL not found in {path}")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Could not find url file at {path}. "
            f"Please make sure you've run the CLI tool and set up your URL."
        )
    return url_name[0]



def make_request(url, headers=None, data=None):
    """Makes API request

    Params:
    url (str): url to make request to
    headers (dict, optional): headers to send with request. Defaults to None.
    data (bytes, optional): data to send with request. Defaults to None.
    """
    request = Request(url, headers=headers or {}, data=data)
    try:
        with urlopen(request, timeout=10) as response:
            return response.read(), response
    except HTTPError as error:
        print(error.status, error.reason)
        quit("Exiting...")
    except URLError as error:
        print(error.reason)
        quit("Exiting...")
    except TimeoutError:
        print("Request timed out")
        quit("Exiting...")


def chat_help():
    """Prints help message for all available commands"""
    print(
        "ChatGDB is a python script that defines some extra helpful GDB and "
        "LLDB commands. Before use, be sure to set up your api key using the "
        "CLI tool. The commands are as follows:\n\n"
        "chat: This command is used to generate GDB/LLDB commands based on plain "
        "English input. For example, 'chat stop my code at line 7' will "
        "generate the GDB command 'break 7'. Remember that in LLDB, many "
        "commands require filename information as well.\n\n"
        "explain: This command is used to generate explanations for either "
        "the previous command or a user query. 'explain' with "
        "no arguments will generate an explanation for the previous command "
        "but typing a query after will generate an answer for it.\n\n")


# It's crucial to handle potential FileNotFoundError when initializing these global variables.
# This might require restructuring how these are loaded, perhaps lazily or within a try-except block
# in the functions that use them, or ensuring CLI setup always creates these files.

# Option 1: Lazy loading within functions that use HEADERS/URL (more robust)
# Option 2: Global try-except (simplest for now, but exits if config missing at import time)

try:
    HEADERS = {
        "Authorization": "Bearer " + get_key(),
        "Content-Type": "application/json"
    }
    URL = get_url()
except FileNotFoundError as e:
    # This print will occur when utils.py is imported and config files are missing.
    # For CLI, this is okay. For GDB/LLDB scripts, this might be too early or disruptive.
    # Consider moving initialization into a function called by GDB/LLDB after setup.
    print(f"Error initializing ChatGDB: {e}", file=sys.stderr)
    # Depending on the desired behavior, you might re-raise, or set HEADERS/URL to None,
    # and let functions like explain_helper/chat_helper handle it.
    # For now, let's allow the import but subsequent calls will fail if HEADERS/URL are not set.
    HEADERS = None
    URL = None


def explain_helper(prev_command, current_user_query, explanation_prompt_prefix, print_callback):
    """Generates explanation for either the previous command or a user query with streaming."""
    question = explanation_prompt_prefix + prev_command if current_user_query == "" else current_user_query
    data = {
        "model": get_model(),
        "messages": [{"role": "user", "content": question}],
        "stream": True
    }
    # Errors are handled by make_streaming_request, which prints to stderr and callback
    make_streaming_request(URL, HEADERS, data, print_callback)


def chat_helper(command, prompt, print_callback):
    data = {
        "model": get_model(), # Assumes get_model() is defined
        "messages": [{"role": "user", "content": prompt + command}],
        "stream": True 
    }
    
    # URL, HEADERS are assumed to be defined globally in utils.py
    full_command = make_streaming_request(URL, HEADERS, data, print_callback) 
    
    if full_command.startswith("ERROR:"):
        # Error message already printed by make_streaming_request or callback
        return "", "" 

    # The first element of the tuple was previously the printed command,
    # but now printing is handled by the callback.
    # The second element is the fully assembled command for execution.
    return full_command, full_command 

# Ensure Request, urlopen, HTTPError, URLError, json, sys are imported
# Ensure URL, HEADERS, get_model are available
def make_streaming_request(api_url, headers_dict, request_data_dict, stream_print_callback):
    full_response_content = ""
    try:
        request_data_bytes = bytes(json.dumps(request_data_dict), encoding="utf-8")
        req = Request(api_url, headers=headers_dict, data=request_data_bytes, method="POST")
        
        with urlopen(req, timeout=60) as response:
            for line_bytes in response:
                line = line_bytes.decode('utf-8').strip()
                if line.startswith('data: '):
                    chunk_json_str = line[len('data: '):]
                    if chunk_json_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(chunk_json_str)
                        if chunk_data.get('choices') and len(chunk_data['choices']) > 0:
                            delta = chunk_data['choices'][0].get('delta', {})
                            content_chunk = delta.get('content')
                            if content_chunk:
                                full_response_content += content_chunk
                                if stream_print_callback:
                                    stream_print_callback(content_chunk)
                    except json.JSONDecodeError:
                        # In case of malformed JSON in a chunk, skip it and continue
                        sys.stderr.write(f"Warning: Malformed JSON chunk skipped: {chunk_json_str}\n")
                        continue 
    except HTTPError as error:
        err_msg = f"HTTP Error: {error.status} {error.reason}"
        sys.stderr.write(f"{err_msg}\n")
        if stream_print_callback: stream_print_callback(f"\nLLM API Error: {err_msg}\n")
        return f"ERROR: {err_msg}"
    except URLError as error:
        err_msg = f"URL Error: {error.reason}"
        sys.stderr.write(f"{err_msg}\n")
        if stream_print_callback: stream_print_callback(f"\nLLM API Error: {err_msg}\n")
        return f"ERROR: {err_msg}"
    except TimeoutError:
        err_msg = "LLM Request timed out"
        sys.stderr.write(f"{err_msg}\n")
        if stream_print_callback: stream_print_callback(f"\nLLM API Error: {err_msg}\n")
        return f"ERROR: {err_msg}"
    except Exception as e:
        err_msg = f"General streaming request error: {str(e)}"
        sys.stderr.write(f"{err_msg}\n")
        if stream_print_callback: stream_print_callback(f"\nLLM API Error: {err_msg}\n")
        return f"ERROR: {err_msg}"
    
    return full_response_content.strip()

def get_llm_response(full_prompt_string, stream_print_callback=None):
    data = {
        "model": get_model(), # Assumes get_model() is defined
        "messages": [{"role": "user", "content": full_prompt_string}],
        "stream": True # Always stream for this function now
    }
    # make_streaming_request will handle printing chunks to stream_print_callback
    # and will return the full assembled string or an "ERROR:" string.
    full_response = make_streaming_request(URL, HEADERS, data, stream_print_callback)
    return full_response
