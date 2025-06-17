
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = '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'

# Check if the API key is available
if not api_key:
    raise ValueError("No OPENAI_API_KEY found in environment variables. Please create a .env file and add it.")

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

# Define the prompt
prompt = "test"

# Create the chat completion request
try:
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    # Print the response
    print(response.choices[0].message.content)

except Exception as e:
    print(f"An error occurred: {e}")

