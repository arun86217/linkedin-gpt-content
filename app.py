import streamlit as st
import time
from dotenv import load_dotenv
from extractor import extract_chat_content
from postgen import generate_blog_post_from_conversation
import pyperclip
import platform
import logging

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="ChatGPT to Blog Post Generator",
    page_icon="🚀",
    layout="centered"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stTextInput>div>div>input {
        background-color: white;
    }
    .stTextInput>div>div>input[type="password"] {
        -webkit-text-security: disc;
    }
    .credentials-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 1.5rem;
    }
    .session-timer {
        position: fixed;
        bottom: 10px;
        right: 10px;
        background-color: #f8f9fa;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.8em;
        color: #666;
    }
    .api-key-box {
        background-color: #e9f7fe;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #b3e0ff;
        margin-bottom: 1.5rem;
    }
    .stSelectbox {
        margin-bottom: 1rem;
    }
    .custom-model-input {
        margin-top: 1rem;
    }
    
    /* Cooler Refresh Button Style */
    div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-of-type(2) .stButton>button {
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        background-image: linear-gradient(to right, #4CAF50, #8BC34A); /* Green gradient */
        color: white;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-of-type(2) .stButton>button:hover {
        background-image: linear-gradient(to right, #45a049, #7CB342); /* Darker gradient */
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-of-type(2) .stButton>button:active {
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'api_keys' not in st.session_state:
    st.session_state.api_keys = {
        'openai': '',
        'anthropic': '',
        'openrouter': '',
        'custom_model_name': ''
    }
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = 'openai/gpt-4'
if 'custom_model' not in st.session_state:
    st.session_state.custom_model = ''
if 'last_post_time' not in st.session_state:
    st.session_state.last_post_time = 0
if 'session_start' not in st.session_state:
    st.session_state.session_start = time.time()

# Constants
RATE_LIMIT_SECONDS = 60  # Minimum time between generations

# Available models
OPENROUTER_MODELS = {
    'OpenAI': [
        'openai/gpt-4',
        'openai/gpt-4-turbo',
        'openai/gpt-3.5-turbo'
    ],
    'Anthropic': [
        'anthropic/claude-3-opus',
        'anthropic/claude-3-sonnet',
        'anthropic/claude-2.1'
    ],
    'Mistral': [
        'mistralai/mixtral-8x7b-instruct',
        'mistralai/mistral-7b-instruct'
    ]
}

def check_session_timeout():
    """Check if session has timed out"""
    elapsed_minutes = (time.time() - st.session_state.session_start) / 60
    if elapsed_minutes > 2:
        clear_credentials()
        st.session_state.session_start = time.time()
        st.warning("Session timed out. Please re-enter your credentials.")
        return True
    return False

def check_rate_limit():
    """Check if enough time has passed since the last post attempt"""
    elapsed_time = time.time() - st.session_state.last_post_time
    if elapsed_time < RATE_LIMIT_SECONDS:
        st.warning(f"Please wait {int(RATE_LIMIT_SECONDS - elapsed_time)} more seconds before generating again.")
        return True
    return False

def clear_credentials():
    """Clear all API keys and credentials from session state"""
    st.session_state.api_keys = {'openai': '', 'anthropic': '', 'openrouter': '', 'custom_model_name': ''}
    st.session_state.custom_model = ''
    st.session_state.selected_model = 'openai/gpt-4' # Reset model
    st.session_state.chat_url = "" # Clear URL too
    st.session_state.post_content = None # Clear generated content

def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        logger.info("Text copied to clipboard.")
        return True
    except Exception as e:
        logger.error(f"Failed to copy to clipboard: {e}")
        # Fallback for environments without clipboard access (like some Streamlit Cloud setups)
        st.warning("Could not automatically copy. Please copy the text manually.") 
        return False

def clear_chat_url():
    st.session_state.chat_url = ""

def clear_post_content():
     st.session_state.post_content = None

def refresh_session():
    """Refresh the session without clearing data"""
    st.session_state.session_start = time.time()
    st.success("Session refreshed!")

def main():
    # Initialize session state variables needed in main
    if 'post_content' not in st.session_state:
        st.session_state.post_content = None
    if 'chat_url' not in st.session_state:
        st.session_state.chat_url = ""

    # Display refresh button using Streamlit columns for better control
    _, col2 = st.columns([0.85, 0.15]) # Adjust ratio as needed
    with col2:
        if st.button("🔄 Refresh Session", help="Click to refresh your session without losing data"):
            refresh_session()

    st.title("🚀 ChatGPT Conversation to Blog Post Generator")
    st.markdown("Transform your ChatGPT conversations into detailed blog posts!")
    
    # Check session timeout
    if check_session_timeout():
        return
    
    # API Keys section
    st.header("🔑 API Keys & Model Selection")
    with st.expander("Configure API Settings", expanded=True):
        with st.container():
            st.markdown('<div class="api-key-box">', unsafe_allow_html=True)
            
            # API Key Inputs
            st.session_state.api_keys['openai'] = st.text_input("OpenAI API Key", value=st.session_state.api_keys.get('openai', ''), type="password", help="Enter your OpenAI API key (e.g., sk-...)")
            st.session_state.api_keys['anthropic'] = st.text_input("Anthropic API Key", value=st.session_state.api_keys.get('anthropic', ''), type="password", help="Enter your Anthropic API key")
            st.session_state.api_keys['openrouter'] = st.text_input("OpenRouter API Key", value=st.session_state.api_keys.get('openrouter', ''), type="password", help="Enter your OpenRouter API key (enables more models)")
            
            st.markdown("[Get API Keys](https://github.com/your-repo/blob/main/API_KEYS.md)", unsafe_allow_html=True) # Update link if needed
            st.markdown('</div>', unsafe_allow_html=True)

        # Model Selection Logic - Corrected
        model_options = []
        # Populate options based on available keys
        if st.session_state.api_keys.get('openai'):
            model_options.extend(OPENROUTER_MODELS['OpenAI'])
        if st.session_state.api_keys.get('anthropic'):
            model_options.extend(OPENROUTER_MODELS['Anthropic'])
        if st.session_state.api_keys.get('openrouter'):
            # Add all known OpenRouter models
            for provider_models in OPENROUTER_MODELS.values():
                model_options.extend(provider_models)
        
        # Remove duplicates and sort
        model_options = sorted(list(set(model_options)))
        
        # Placeholder for custom input
        custom_model_placeholder = "Enter Custom OpenRouter Model..."
        custom_model_entry_prefix = "Custom: "
        
        # Add custom option if OpenRouter key exists
        if st.session_state.api_keys.get('openrouter'):
             if custom_model_placeholder not in model_options:
                 model_options.append(custom_model_placeholder)

        # Determine current selection state
        current_selection = st.session_state.get('selected_model', model_options[0] if model_options else None)
        current_custom_value = st.session_state.get('custom_model', '')
        display_selection = current_selection # What to show in the dropdown

        # If a custom model is currently active and has a value, create the display string
        if current_custom_value and current_selection == current_custom_value:
            display_selection = f"{custom_model_entry_prefix}{current_custom_value}"
            # Add this specific custom entry to options if not already there (for display)
            if display_selection not in model_options:
                model_options.append(display_selection)
                model_options.sort()

        # If no valid options, display warning
        if not model_options:
             st.warning("Please enter at least one API key to select a model.")
             st.session_state.selected_model = None # Ensure no model is selected
        else:
            # Find index for the selectbox, default to 0 if not found
            try:
                current_index = model_options.index(display_selection) if display_selection in model_options else 0
            except ValueError:
                 current_index = 0
                 # Update state if current selection became invalid
                 if display_selection not in model_options:
                     st.session_state.selected_model = model_options[current_index] if model_options else None

            selected_display = st.selectbox(
                "Select AI Model for Generation:",
                options=model_options,
                index=current_index,
                key="model_selector",
                help="Choose model. OpenRouter key enables more options & custom input."
            )

            # Logic to handle selection changes
            show_custom_input_field = False
            if selected_display == custom_model_placeholder:
                # User selected the placeholder to enter a new custom model
                show_custom_input_field = True
                # Don't immediately change selected_model yet, wait for input
                # Keep custom_model value as is for the input field default
            elif selected_display.startswith(custom_model_entry_prefix):
                # User selected an existing custom model entry
                show_custom_input_field = True
                selected_custom_model_name = selected_display.replace(custom_model_entry_prefix, "")
                st.session_state.selected_model = selected_custom_model_name
                st.session_state.custom_model = selected_custom_model_name
            else:
                # User selected a standard model
                st.session_state.selected_model = selected_display
                st.session_state.custom_model = '' # Clear custom model value
                show_custom_input_field = False

            # Display the custom model text input if required
            if show_custom_input_field and st.session_state.api_keys.get('openrouter'):
                custom_model_input = st.text_input(
                    "Enter Custom OpenRouter Model Identifier:", 
                    value=st.session_state.get('custom_model', ''), # Use current custom value
                    key="custom_model_input_field",
                    help="e.g., google/gemini-pro, mistralai/mixtral-8x7b. Find on OpenRouter.ai"
                )
                # If the text input changes, update the state
                if custom_model_input != st.session_state.get('custom_model', ''):
                    clean_custom_model = custom_model_input.strip()
                    st.session_state.custom_model = clean_custom_model
                    # Set the actual selected model to the new custom one if it's not empty
                    if clean_custom_model:
                        st.session_state.selected_model = clean_custom_model
                        # Rerun to update the selectbox display immediately
                        st.rerun()
                    else:
                        # If input cleared, revert selection to placeholder
                        st.session_state.selected_model = custom_model_placeholder 
                        st.rerun() # Rerun to update selectbox state
            elif not show_custom_input_field:
                 # Ensure custom model value is cleared if not showing input (e.g., switched back to standard)
                 st.session_state.custom_model = ''

    # Input URL section
    st.header("🔗 ChatGPT URL Input")
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        chat_url = st.text_input(
            "Enter ChatGPT Share URL:",
            value=st.session_state.chat_url,
            placeholder="https://chatgpt.com/share/... or https://chat.openai.com/g/...",
            key="chat_url_input"
        )
        st.session_state.chat_url = chat_url # Update session state on input
    with col2:
        st.button("🗑️", key="clear_url", help="Clear URL", on_click=clear_chat_url)
    
    # Clear credentials button (now mainly for API keys)
    if st.button("Clear All API Keys & Input", type="secondary"):
        clear_credentials()
        st.success("API keys and URL cleared!")
        st.rerun() # Rerun to reflect cleared state
    
    # Generate button
    st.markdown("--- pilote ") # Separator
    if st.button("✨ Generate Blog Post", type="primary", help="Extract conversation and generate a blog post"):
        if not chat_url:
            st.error("Please enter a valid ChatGPT URL")
            return
            
        if not st.session_state.selected_model or st.session_state.selected_model == "Enter Custom OpenRouter Model":
             st.error("Please select a valid AI model or enter a custom one.")
             return
             
        # Check rate limit
        if check_rate_limit():
            return
            
        try:
            with st.spinner("Extracting conversation and generating blog post..."): # Updated spinner text
                # Extract structured content
                conversation_data = extract_chat_content(chat_url)
                logger.info(f"Extracted {len(conversation_data)} messages.")
                
                # Generate blog post from conversation
                logger.info(f"Generating blog post with model: {st.session_state.selected_model}")
                blog_post = generate_blog_post_from_conversation(
                    conversation_data, # Pass structured data
                    model=st.session_state.selected_model,
                    api_keys=st.session_state.api_keys
                )
                
                # Store post in session state
                st.session_state.post_content = blog_post
                st.session_state.last_post_time = time.time() # Update rate limit timer
                logger.info("Blog post generated successfully.")
                
        except Exception as e:
            logger.error(f"Error during generation: {str(e)}", exc_info=True)
            st.error(f"An error occurred: {str(e)}")
            st.session_state.post_content = None # Clear content on error

    # Display the generated blog post
    if st.session_state.post_content:
        st.markdown("### Generated Blog Post") # Updated header
        
        # Add clear button for the post
        col1, col2 = st.columns([0.9, 0.1])
        with col2:
            st.button("🗑️", key="clear_post", help="Clear Generated Post", on_click=clear_post_content)
        
        # Display the full blog post in a large text area
        full_post_content = st.session_state.post_content
        st.text_area(
             "Blog Post Content", 
             value=full_post_content, 
             height=600, # Increased height
             key="blog_post_content_area", 
             disabled=True, # Keep disabled for display
             help="Generated blog post content. Use buttons below to copy or download."
         )
        
        # Copy button
        if st.button("📋 Copy Post to Clipboard", key="copy_blog_post"):
            if copy_to_clipboard(full_post_content):
                st.success("Blog post copied to clipboard!")
            # Error/warning handled within copy_to_clipboard
        
        # Download button
        st.download_button(
            label="📥 Download Blog Post",
            data=full_post_content,
            file_name="generated_blog_post.md", # Suggest markdown extension
            mime="text/markdown", # Use markdown mime type
            key="download_blog_post"
        )

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    main() 