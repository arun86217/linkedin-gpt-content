import os
import requests
import logging
import re
from typing import Optional, Dict, List
from summarizer import get_api_client

# Configure logger
logger = logging.getLogger(__name__)

# Function to remove non-latin1 characters
def remove_non_latin1(text: str) -> str:
    if not isinstance(text, str):
        return text # Return as is if not a string
    # Keep ASCII and Latin-1 Supplement characters, replace others
    return text.encode('latin-1', 'ignore').decode('latin-1')

def generate_blog_post_from_conversation(conversation: List[Dict[str, str]], model: str, api_keys: Dict[str, str]) -> str:
    """
    Generate a long-form blog post from a structured conversation.

    Args:
        conversation (List[Dict[str, str]]): The conversation history, including system, user, and assistant roles.
        model (str): The model identifier to use for generation.
        api_keys (dict): Dictionary of API keys.

    Returns:
        str: The generated blog post content.

    Raises:
        Exception: If API keys are missing or API call fails.
    """
    if not api_keys:
        raise Exception("API keys are required for blog post generation")

    api_url, headers, api_key = get_api_client(model, api_keys)

    if not api_key:
        raise Exception(f"API key for the selected model ({model}) not found or provided")

    headers["Content-Type"] = "application/json"

    # Construct a prompt suitable for generating a blog post from conversation history
    # We will pass the conversation history more directly, with a preceding instruction
    # The system prompt will guide the overall generation task
    system_prompt = f"""You are an expert technical writer. Your task is to generate a comprehensive and detailed blog post based on the provided conversation history. 
    The conversation includes messages with roles 'system' (metadata), 'user' (questions/prompts), and 'assistant' (responses).
    
    Instructions:
    1.  **Synthesize the Conversation:** Weave the user questions and assistant answers into a coherent narrative or a well-structured Q&A format suitable for a blog post.
    2.  **Preserve Technical Details:** Retain ALL technical information, code snippets, examples, commands, and explanations accurately. Do not simplify or omit technical content.
    3.  **Clarity and Structure:** Organize the content logically with clear headings (using markdown #), paragraphs, and bullet points or numbered lists where appropriate.
    4.  **Introduction and Conclusion:** Add a suitable introduction that sets the context (based on the initial user prompts or metadata) and a concluding summary or closing thoughts.
    5.  **Title:** Suggest a relevant and engaging title for the blog post at the very beginning, formatted like: "Title: [Your Suggested Title]".
    6.  **Long-Form Content:** Generate a detailed, in-depth article. Do not worry about length limits; aim for completeness.
    7.  **Tone:** Maintain a professional, informative, and engaging tone suitable for a technical audience.
    8.  **No Placeholders:** Do not include placeholder text like '[Your Content Here]' or comments about the generation process.
    9.  **Direct Output:** Start the output directly with the suggested title, followed by the blog post content.

    Use the following conversation history to generate the blog post:"""

    # Prepare messages payload for the API
    messages_payload = [
        {"role": "system", "content": system_prompt}
    ]
    # Add the actual conversation history, cleaning content
    for msg in conversation:
        role = msg.get('role', 'assistant').lower()
        if role not in ['user', 'assistant', 'system']:
             logger.warning(f"Unknown role '{role}' found in conversation, treating as 'assistant'.")
             role = 'assistant'
             
        original_content = msg.get('content', '')
        # Clean content to remove problematic characters before sending
        cleaned_content = remove_non_latin1(original_content)
        
        if original_content != cleaned_content:
             logger.debug(f"Removed non-latin1 characters from message content for role '{role}'")
             
        messages_payload.append({"role": role, "content": cleaned_content})

    # Prepare the API request based on the model type
    # Aim for maximum possible tokens. Specific limits depend on the model.
    # We'll request a large number, the API will cap it if necessary.
    max_output_tokens = 4000 # A large value, check model specifics if needed
    
    if model.startswith('anthropic/'):
        # Claude models often use 'max_tokens' directly
        payload = {
            "model": model.split('/')[1], # Extract model name
            "messages": messages_payload,
            "max_tokens": max_output_tokens 
        }
        # Add other relevant parameters for Claude if known (e.g., temperature)
        # payload["temperature"] = 0.7
    else:
        # OpenAI and compatible APIs (like OpenRouter)
        payload = {
            "model": model,
            "messages": messages_payload,
            "max_tokens": max_output_tokens, # Note: OpenAI uses this to limit *completion* length
            "temperature": 0.7
        }
        # Some models might support removing the limit via None, but many require a number.
        # If the provider supports it, `"max_tokens": None` might work, otherwise use a large number.

    logger.info(f"Generating blog post using model: {model}")
    logger.debug(f"API Payload (messages excluded for brevity): {{model: {payload.get('model')}, max_tokens: {payload.get('max_tokens')}, temperature: {payload.get('temperature')}}}")
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=300 # Increase timeout for potentially long generation
        )
        response.raise_for_status()

        result = response.json()

        # Parse response based on the API format
        if model.startswith('anthropic/'):
            # Claude v3 response structure
            if result.get('type') == 'message' and result.get('content'):
                 generated_content = "".join(block.get('text', '') for block in result['content'] if block.get('type') == 'text')
                 return generated_content.strip()
            else:
                 # Older Claude structure or unexpected format
                 logger.error(f"Unexpected Anthropic response format: {result}")
                 raise ValueError("Unexpected response format from Anthropic API")
        elif 'choices' in result and result['choices']:
            # OpenAI and compatible format
            message = result['choices'][0].get('message', {})
            generated_content = message.get('content')
            # Explicitly check for empty string
            if generated_content is not None and generated_content.strip() != "":
                 return generated_content.strip()
            elif generated_content == "":
                 logger.error(f"API response contained an empty content string. Model: {model}")
                 # Check for potential refusal info if the API provides it (example)
                 finish_reason = result['choices'][0].get('finish_reason')
                 refusal_info = message.get('refusal') # Check if present
                 error_msg = f"Model ({model}) returned empty content."
                 if finish_reason:
                      error_msg += f" Finish Reason: {finish_reason}."
                 if refusal_info:
                     error_msg += f" Refusal Info: {refusal_info}."
                 error_msg += " This might be due to model limitations, safety filters, or input complexity."
                 raise ValueError(error_msg)
            else:
                 logger.error(f"No content key found in API response message: {message}")
                 raise ValueError("API response message did not contain 'content' key.")
        else:
            logger.error(f"Unexpected API response format (missing 'choices'): {result}")
            raise ValueError("Unexpected response format from API (missing 'choices')")

    except requests.exceptions.Timeout:
        logger.error(f"API request timed out after 300 seconds for model {model}")
        raise TimeoutError(f"Blog post generation timed out for model {model}.")
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else "N/A"
        response_text = e.response.text[:500] if e.response is not None else "No response body"
        logger.error(f"API Request Error: Status={status_code}, Response={response_text}, Error={str(e)}")
        raise Exception(f"Failed to generate blog post (Status: {status_code}): {str(e)}")
    except (KeyError, IndexError, TypeError) as e:
         logger.error(f"Error parsing API response: {str(e)}", exc_info=True)
         raise ValueError(f"Error processing response from API: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during blog post generation: {str(e)}", exc_info=True)
        raise Exception(f"An unexpected error occurred during blog post generation: {str(e)}")

# Removed the old generate_post function as it's no longer applicable 