from workflow_agents.base_agents import AugmentedPromptAgent
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve OpenAI API key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")

prompt = "What is the capital of France?"
print(f'\nPrompt: {prompt}')

persona = "You are a college professor; your answers always start with: 'Dear students,'"
augmented_agent = AugmentedPromptAgent(openai_api_key, persona)
augmented_agent_response = augmented_agent.respond(prompt)

# Print the agent's response
print(f'\nAgent Response: {augmented_agent_response}')

knowledge_source = 'The agent likely used its general world knowledge to identify ' \
                   'Paris as the capital of France. The persona prompt shaped the ' \
                   'response style by instructing the agent to answer like a college ' \
                   'professor and begin with "Dear students," while leaving the ' \
                   'factual content of the answer unchanged.\n'

print(f'\nKnowledge Source: {knowledge_source}')
