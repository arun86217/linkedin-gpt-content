import requests
import logging
from typing import Dict

# Configure logger
logger = logging.getLogger(__name__)

def get_api_client(model: str, api_keys: Dict[str, str]) -> tuple:
    """
    Get the appropriate API client based on the model.
    
    Args:
        model (str): The model identifier
        api_keys (Dict[str, str]): Dictionary of API keys
        
    Returns:
        tuple: (api_url, headers, api_key)
    """
    if not model:
        raise ValueError("Model identifier is required")
        
    if model.startswith('openai/'):
        if not api_keys.get('openai'):
            raise ValueError("OpenAI API key is required for OpenAI models")
        return (
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {api_keys['openai']}"},
            api_keys['openai']
        )
    elif model.startswith('anthropic/'):
        if not api_keys.get('claude'):
            raise ValueError("Claude API key is required for Anthropic models")
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": api_keys['claude']},
            api_keys['claude']
        )
    else:
        # Handle custom OpenRouter models or default OpenRouter models
        if not api_keys.get('openrouter'):
            raise ValueError("OpenRouter API key is required")
        return (
            "https://openrouter.ai/api/v1/chat/completions",
            {
                "Authorization": f"Bearer {api_keys['openrouter']}",
                "HTTP-Referer": "https://github.com/yourusername/linkedin-chatgpt",
                "X-Title": "LinkedIn Post Generator"
            },
            api_keys['openrouter']
        )

def get_ai_response(prompt: str, model: str, api_keys: dict) -> str:
    """
    Get response from the AI model.
    
    Args:
        prompt (str): The prompt to send to the model
        model (str): The model identifier
        api_keys (dict): Dictionary of API keys
        
    Returns:
        str: The model's response
    """
    try:
        # Get API client configuration
        api_url, headers, api_key = get_api_client(model, api_keys)
        
        # Prepare the API request based on the model type
        if model.startswith('anthropic/'):
            data = {
                "model": model.replace('anthropic/', ''),
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000
            }
        else:
            # OpenAI and OpenRouter format
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
        
        # Make the API request
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse response based on the API format
        if model.startswith('anthropic/'):
            return response.json()['content'][0]['text']
        else:
            return response.json()['choices'][0]['message']['content']
            
    except requests.exceptions.RequestException as e:
        if response.status_code == 401:
            raise ValueError(f"Invalid API key for {model.split('/')[0]}")
        elif response.status_code == 429:
            raise ValueError(f"Rate limit exceeded for {model.split('/')[0]}")
        else:
            raise ValueError(f"Error calling {model.split('/')[0]} API: {str(e)}")
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected response format from {model.split('/')[0]} API")
    except Exception as e:
        raise ValueError(f"Error getting AI response: {str(e)}")

def summarize_content(content: str, model: str, api_keys: dict) -> str:
    """
    Summarize the content using the specified model.
    
    Args:
        content (str): The content to summarize
        model (str): The model identifier
        api_keys (dict): Dictionary of API keys
        
    Returns:
        str: The summarized content
    """
    try:
        # Get API client configuration
        api_url, headers, api_key = get_api_client(model, api_keys)
        
        # Prepare the prompt
        prompt = f"""Analyze the following content and provide a technical summary focusing on:
        1. Core concepts and principles
        2. Technical implementation details
        3. Problem-solution patterns
        4. Key technical specifications
        5. Implementation considerations

        Content:
        {content}

        Summary:"""
        
        # Prepare the API request based on the model type
        if model.startswith('anthropic/'):
            data = {
                "model": model.replace('anthropic/', ''),
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": None  # No token limit
            }
        else:
            # OpenAI and OpenRouter format
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": None  # No token limit
            }
        
        # Make the API request
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse response based on the API format
        if model.startswith('anthropic/'):
            return response.json()['content'][0]['text']
        else:
            return response.json()['choices'][0]['message']['content']
            
    except requests.exceptions.RequestException as e:
        if response.status_code == 401:
            raise ValueError(f"Invalid API key for {model.split('/')[0]}")
        elif response.status_code == 429:
            raise ValueError(f"Rate limit exceeded for {model.split('/')[0]}")
        else:
            raise ValueError(f"Error calling {model.split('/')[0]} API: {str(e)}")
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected response format from {model.split('/')[0]} API")
    except Exception as e:
        logger.error(f"Error in summarization: {str(e)}")
        raise 