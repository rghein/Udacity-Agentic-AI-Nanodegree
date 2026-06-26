# Test script for DirectPromptAgent class

from workflow_agents.base_agents import DirectPromptAgent
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

prompt = "What is the Capital of France?"
print(f'\nPrompt: {prompt}')

direct_agent = DirectPromptAgent(openai_api_key)
direct_agent_response = direct_agent.respond(prompt)

# Print the response from the agent
print(f'\nAgent Response: {direct_agent_response}')

print("\nKnowledge source: The agent used the selected LLM model's general " \
      "pretrained knowledge, with no external knowledge base or retrieval source.\n")
