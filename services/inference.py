import json
import requests
import os
import hashlib
import logging
from services.dotenv_loader import load_environment
from requests.exceptions import HTTPError, RequestException

# Initialize the logger
log = logging.getLogger(__name__)

def call_openai_api(prompt, api_key):
    """
    Calls the OpenAI API with the provided prompt and returns the response.

    Args:
        prompt (list): A list of dictionaries representing the conversation prompt.
        api_key (str): The API key for authenticating the OpenAI API request.

    Returns:
        dict: The JSON response from the OpenAI API.
    """
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    data = {
        'messages': prompt,
        'max_tokens': 512,
        'model': 'gpt-4o-mini',
        'temperature': 0
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        log.info(f"API call successful. Status Code: {response.status_code}")
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        log.error(f"HTTP error occurred: {http_err}")
        return f"Error: {response.status_code}, {response.text}"
    except requests.exceptions.RequestException as req_err:
        log.error(f"Request error occurred: {req_err}")
        return f"Error: Network error occurred"

def get_api_key():
    """
    Retrieves the OpenAI API key from the environment variables.

    Returns:
        str: The OpenAI API key.

    Raises:
        EnvironmentError: If the API key is not set in the environment variables.
    """
    load_environment()  # Load environment variables from the .env file
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        log.error("OPENAI_API_KEY is not set in the environment variables.")
        raise EnvironmentError("OPENAI_API_KEY is not set in the environment variables.")
    return api_key

def get_prompt(prompt_content, system_message):
    """
    Constructs the prompt for the OpenAI API request.

    Args:
        prompt_content (str): The user's input message.
        system_message (str): The system message providing context or instructions.

    Returns:
        list: A list of dictionaries representing the conversation prompt.
    """
    prompt = [
        {'role': 'user', 'content': prompt_content},
        {'role': 'system', 'content': system_message}
    ]
    log.info(f"Prompt created: {prompt}")
    return prompt

def write_response_to_cache(prompt_hash, response):
    """
    Writes the API response to a cache file.

    Args:
        prompt_hash (str): The hashed value of the prompt content.
        response (dict): The API response to be cached.
    """
    try:
        cache_dir = 'utilities/cache'
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f'{prompt_hash}.json')
        with open(cache_path, 'w') as outfile:
            json.dump(response, outfile)
        log.info(f"Response cached at {cache_path}")
    except IOError as e:
        log.error(f"Failed to write response to cache: {e}")

def read_response_from_cache(prompt_hash):
    """
    Reads the API response from the cache if it exists.

    Args:
        prompt_hash (str): The hashed value of the prompt content.

    Returns:
        dict or None: The cached API response, or None if no cache exists.
    """
    cache_path = os.path.join('utilities/cache', f'{prompt_hash}.json')
    if os.path.exists(cache_path):
        try:
            with open(cache_path) as json_file:
                log.info(f"Cache hit for {prompt_hash}")
                return json.load(json_file)
        except (json.JSONDecodeError, IOError) as e:
            log.error(f"Failed to read response from cache: {e}")
    log.info(f"Cache miss for {prompt_hash}")
    return None

def hash_prompt(prompt_content):
    """
    Generates an MD5 hash of the prompt content.

    Args:
        prompt_content (str): The user's input message.

    Returns:
        str: The MD5 hash of the prompt content.
    """
    prompt_hash = hashlib.md5(prompt_content.encode()).hexdigest()
    log.info(f"Generated prompt hash: {prompt_hash}")
    return prompt_hash

def get_message_content(data):
    """
    Extracts the message content from the API response.

    Args:
        data (dict): The JSON response from the OpenAI API.

    Returns:
        str: The content of the message returned by the API.
    """
    try:
        message_content = data['choices'][0]['message']['content']
        log.info("Message content extracted from API response.")
        return message_content
    except (KeyError, IndexError) as e:
        log.error(f"Failed to extract message content: {e}")
        return "Error: Could not retrieve message content."

def openai_api(prompt_content, system_message):
    """
    Handles the full OpenAI API interaction including caching.

    Args:
        prompt_content (str): The user's input message.
        system_message (str): The system message providing context or instructions.

    Returns:
        str: The content of the message returned by the API.
    """
    api_key = get_api_key()
    prompt = get_prompt(prompt_content, system_message)
    prompt_hash = hash_prompt(prompt_content)
    
    # Check cache first
    cached_response = read_response_from_cache(prompt_hash)
    if cached_response:
        log.info("Returning cached response.")
        data = cached_response
    else:
        log.info("Calling OpenAI API.")
        result = call_openai_api(prompt, api_key)
        if isinstance(result, dict):
            write_response_to_cache(prompt_hash, result)
        data = result

    return get_message_content(data)

import requests
from requests.exceptions import HTTPError, RequestException

def query_huggingface_endpoint(payload, api_url, token):
    """
    Calls a Hugging Face Inference Endpoint with the given payload.

    Parameters:
    - payload (dict): The JSON payload to be sent to the Hugging Face API.
    - api_url (str): The full URL of the Hugging Face Inference Endpoint.
    - token (str): The Bearer token for authenticating the request.

    Returns:
    - dict: The JSON response from the Hugging Face API if successful.
    - None: If the request fails due to an HTTP or network-related error.
    
    Raises:
    - ValueError: If any of the required parameters are missing or invalid.
    """

    # Input validation
    if not payload or not api_url or not token:
        raise ValueError("Payload, API URL, and token must be provided")

    # Prepare the headers for the request
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        # Make the POST request to the Hugging Face endpoint
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Raise an exception for HTTP errors (4xx and 5xx)
        response.raise_for_status()
        
        # Return the JSON response from the API
        return response.json()
    
    except HTTPError as http_err:
        # Handle HTTP errors
        print(f"HTTP error occurred: {http_err}")
    
    except RequestException as req_err:
        # Handle network-related errors
        print(f"Request error occurred: {req_err}")
    
    except Exception as err:
        # Handle any other errors
        print(f"An error occurred: {err}")
    
    # If any error occurs, return None
    return None


def inference_huggingface(prompt_content, system_message):
    """
    Runs the inference process by interacting with the Hugging Face API.

    Args:
        prompt_content (str): The user's input message.
        system_message (str): The system message providing context or instructions.

    Returns:
        str: The content of the message returned by the API.
    """
    API_URL = "https://aizvierx2xbiac7h.us-east-1.aws.endpoints.huggingface.cloud"
    text = f"Prompt: {prompt_content}\nSystem: {system_message}"
    payload = {
        "inputs": text,
        "parameters": {}
    }
    load_environment() 
    API_TOKEN = os.getenv('HUGGINGFACEHUB_API_TOKEN')
    # Call the function and print the result
    result = query_huggingface_endpoint(payload, API_URL, API_TOKEN)
    print(result)

    log.info(f"Running inference with prompt: {text}")
    message_content = result[0].get('generated_text')
    log.info(f"Inference result: {message_content}")
    return message_content
   
def run_inference(prompt_content, system_message):
    """
    Runs the inference process by interacting with the OpenAI API.

    Args:
        prompt_content (str): The user's input message.
        system_message (str): The system message providing context or instructions.

    Returns:
        str: The content of the message returned by the API.
    """
    log.info(f"Running inference with prompt: {prompt_content}")
    # message_content = inference_huggingface(prompt_content, system_message)

    message_content = openai_api(prompt_content, system_message)
    log.info(f"Inference result: {message_content}")
    return message_content
