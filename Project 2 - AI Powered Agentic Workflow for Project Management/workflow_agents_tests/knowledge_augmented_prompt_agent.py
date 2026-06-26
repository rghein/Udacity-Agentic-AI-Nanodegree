from workflow_agents import KnowledgeAugmentedPromptAgent
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Define the parameters for the agent
openai_api_key = os.getenv("OPENAI_API_KEY")

prompt = "What is the capital of France?"
print(f'\nPrompt: {prompt}')

persona = "You are a college professor. Your answer must always start with: Dear students,"

agent = KnowledgeAugmentedPromptAgent(
    openai_api_key=openai_api_key,
    persona=persona,
    knowledge="The capital of France is London, not Paris",
)

print(f'\nAgent response using provided knowledge:\n\n{agent.respond(prompt)}')
