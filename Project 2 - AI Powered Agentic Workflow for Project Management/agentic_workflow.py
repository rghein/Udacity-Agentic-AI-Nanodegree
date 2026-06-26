# agentic_workflow.py

from workflow_agents.base_agents import (
    ActionPlanningAgent,
    EvaluationAgent,
    KnowledgeAugmentedPromptAgent,
    RoutingAgent,
)

import os
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# load the product spec
with open("Product-Spec-Email-Router.txt", "r", encoding="utf-8") as file:
    product_spec = file.read()

# Instantiate all the agents

# Action Planning Agent
knowledge_action_planning = (
    "Stories are defined from a product spec by identifying a "
    "persona, an action, and a desired outcome for each story. "
    "Each story represents a specific functionality of the product "
    "described in the specification. \n"
    "Features are defined by grouping related user stories. \n"
    "Tasks are defined for each story and represent the engineering "
    "work required to develop the product. \n"
    "A development Plan for a product contains all these components"
)
action_planning_agent = ActionPlanningAgent(openai_api_key, knowledge_action_planning)

# Product Manager - Knowledge Augmented Prompt Agent
persona_product_manager = "You are a Product Manager, you are responsible for defining the user stories for a product."
knowledge_product_manager = (
    "Stories are defined by writing sentences with a persona, an action, and a desired outcome. "
    "The sentences always start with: As a "
    "Write several stories for the product spec below, where the personas are the different users of the product. "
    f'{product_spec}'
)
product_manager_knowledge_agent = KnowledgeAugmentedPromptAgent(openai_api_key, persona_product_manager, knowledge_product_manager)

# Product Manager - Evaluation Agent
persona_product_manager_eval = "You are an evaluation agent that checks the answers of other worker agents."
evaluation_criteria_product_manager = (
    "The answer must be stories that follow the following structure: \n"
    "As a [type of user], I want [an action or feature] so that [benefit/value]."
)
product_manager_evaluation_agent = EvaluationAgent(
    openai_api_key,
    persona_product_manager_eval,
    evaluation_criteria_product_manager,
    product_manager_knowledge_agent,
    max_interactions=10,
)

# Program Manager - Knowledge Augmented Prompt Agent
persona_program_manager = "You are a Program Manager, you are responsible for defining the features for a product."
knowledge_program_manager = "Features of a product are defined by organizing similar user stories into cohesive groups."
program_manager_knowledge_agent = KnowledgeAugmentedPromptAgent(
    openai_api_key,
    persona_program_manager,
    knowledge_program_manager,
)

# Program Manager - Evaluation Agent
persona_program_manager_eval = "You are an evaluation agent that checks the answers of other worker agents."
evaluation_criteria_program_manager = (
    "The answer must be product features that follow the following structure: \n"
    "Feature Name: A clear, concise title that identifies the capability\n"
    "Description: A brief explanation of what the feature does and its purpose\n"
    "Key Functionality: The specific capabilities or actions the feature provides\n"
    "User Benefit: How this feature creates value for the user"
)
program_manager_evaluation_agent = EvaluationAgent(
    openai_api_key,
    persona_program_manager_eval,
    evaluation_criteria_program_manager,
    program_manager_knowledge_agent,
    max_interactions=10,
)

# Development Engineer - Knowledge Augmented Prompt Agent
persona_dev_engineer = "You are a Development Engineer, you are responsible for defining the development tasks for a product."
knowledge_dev_engineer = "Development tasks are defined by identifying what needs to be built to implement each user story."
development_engineer_knowledge_agent = KnowledgeAugmentedPromptAgent(
    openai_api_key,
    persona_dev_engineer,
    knowledge_dev_engineer,
)

# Development Engineer - Evaluation Agent
persona_dev_engineer_eval = "You are an evaluation agent that checks the answers of other worker agents."
evaluation_criteria_dev_engineer = (
    "The answer must be tasks following this exact structure: \n"
    "Task ID: A unique identifier for tracking purposes\n"
    "Task Title: Brief description of the specific development work\n"
    "Related User Story: Reference to the parent user story\n"
    "Description: Detailed explanation of the technical work required\n"
    "Acceptance Criteria: Specific requirements that must be met for completion\n"
    "Estimated Effort: Time or complexity estimation\n"
    "Dependencies: Any tasks that must be completed first"
)
development_engineer_evaluation_agent = EvaluationAgent(
    openai_api_key,
    persona_dev_engineer_eval,
    evaluation_criteria_dev_engineer,
    development_engineer_knowledge_agent,
    max_interactions=10,
)

# Routing Agent

# instantiate routing agent
routing_agent = RoutingAgent(openai_api_key, [])

# add agents to routing_agent
routing_agent.agents = [
    {
        "name": "Product Manager",
        "description": "Responsible for defining product personas and user stories only. Does not define features or development tasks.",
        "func": lambda query: product_manager_support_function(query),
    },
    {
        "name": "Program Manager",
        "description": "Responsible for organizing user stories into product features only. Does not define user stories or development tasks.",
        "func": lambda query: program_manager_support_function(query),
    },
    {
        "name": "Development Engineer",
        "description": "Responsible for defining engineering implementation tasks only. Does not define user stories or group stories into features.",
        "func": lambda query: development_engineer_support_function(query),
    },
]

# Job function persona support functions
def evaluation_agent_response(query, knowledge_agent, evaluation_agent):
    query_with_criteria = (
        f"{query}\n\n"
        "Your answer must satisfy these criteria:\n"
        f"{evaluation_agent.evaluation_criteria}"
    )
    evaluation_result = evaluation_agent.evaluate(query_with_criteria)
    return evaluation_result["final_response"]

def product_manager_support_function(query):
    query = (
        f"{query}\n\n"
        "Return only user stories. "
        "Each user story must follow the required user story format.\n"
        f"{evaluation_criteria_product_manager}"
    )
    return evaluation_agent_response(
        query,
        product_manager_knowledge_agent,
        product_manager_evaluation_agent,
    )

def program_manager_support_function(query):
    query = (
        f"{query}\n\n"
        "Return only product features. "
        "Each feature must follow the required product feature format.\n"
        f"{evaluation_criteria_program_manager}"
    )
    return evaluation_agent_response(
        query,
        program_manager_knowledge_agent,
        program_manager_evaluation_agent,
    )

def development_engineer_support_function(query):
    query = (
        f"{query}\n\n"
        "Return only development tasks. "
        "Each task must follow the required development task format.\n"
        f"{evaluation_criteria_dev_engineer}"
    )
    return evaluation_agent_response(
        query,
        development_engineer_knowledge_agent,
        development_engineer_evaluation_agent,
    )


# Run the workflow

print("\n*** Workflow execution started ***\n")

# Workflow Prompt
workflow_prompt = """
Create a development plan for the product specification.

Return only the actionable workflow steps needed to complete that plan.

Each step must be routed to one workflow agent:
- Create user stories from the product specification.
- Group related user stories into product features.
- Create development tasks from the user stories and features.

Do not include output format labels, examples, descriptions, headings, or final-output instructions as steps.
"""

print(f"\nTasks to complete in this workflow, workflow prompt = {workflow_prompt}")

# Workflow steps
print("\nDefining workflow steps from the workflow prompt")
workflow_steps = action_planning_agent.extract_steps_from_prompt(workflow_prompt)
print('\nWorkflow Steps: \n')
for step in workflow_steps:
    print(step)

completed_steps = []

for i, step in enumerate(workflow_steps):
    print(f"\nExecuting workflow step {i+1}: {step}\n")
    result = routing_agent.route(step)
    completed_steps.append(result)
    print(f"\nResult of workflow step {i+1}:\n{result}")

if completed_steps:
    print(f"\nFinal output of the workflow:\n\n{completed_steps[-1]}")
