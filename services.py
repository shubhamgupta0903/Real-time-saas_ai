import requests
import os
import re
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Ensure API key is set
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the environment variables.")

def extract_jsx(response_text):
    """Extract JSX code from the AI response."""
    match = re.search(r"```jsx\n(.*?)\n```", response_text, re.DOTALL)
    return match.group(1).strip() if match else response_text.strip()

def generate_component(user_request: str):
    """Generates a React component in JSX format using Tailwind CSS."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    formatted_prompt = f"""
    You are an AI assistant that generates React components using Tailwind CSS.
    Your task is to return a **valid, complete React component in JSX format**.

    🔹 **Rules**:
    - Use **Tailwind CSS**.
    - Use **Recharts for charts**, **ShadCN for tables/cards**.
    - **No explanations, no markdown formatting**.
    - **Only return JSX inside a code block**.

    **User Request:** {user_request}
    """

    data = {
        "model": "deepseek-r1-distill-qwen-32b",
        "messages": [{"role": "user", "content": formatted_prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers)
        response.raise_for_status()
        ai_response = response.json()

        if "choices" not in ai_response or not ai_response["choices"]:
            return {"error": "Unexpected API response format", "data": ai_response}

        raw_text = ai_response["choices"][0]["message"]["content"]
        return extract_jsx(raw_text)
    
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

    except json.JSONDecodeError:
        return {"error": "Failed to parse API response as JSON."}
    
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

