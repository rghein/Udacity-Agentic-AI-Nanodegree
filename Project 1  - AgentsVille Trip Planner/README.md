
# AgentsVille Trip Planner

## The "AgentsVille Trip Planner" is a Jupyter Notebook-based application that interacts with an LLM to perform several functions:

    1. Define Vacation Details
        - Specify the trip duration, interests, and constraints.
        - Use Pydantic to structure and verify this information in a class called VacationInfo.

    2. Review Weather and Activity schedules
        - Simulate API calls to gather weather data and available activities in bulk
        - Review the data manually to understand the available options

    3. The ItineraryAgent
        - Implement an agent that generates a day-by-day itinerary based on the vacation details
        - The system prompt will guide the agent's reasoning through a step-by-step planning process to take travel preference   (e.g. destination, dates, interests) and generate a detailed day-by-day itinerary
        - Craft the components of the prompt (including the role, task/instructions, output format, examples, and context)     to elicit the best possible itinerary in one LLM cal

    4. Evaluating the Itinerary
        - Evaluate the itinerary using a set of criteria to ensure a high-quality travel plan
            - For instance, does the itinerary match the city and the dates requested?
            - Or, is the total cost calulation accurate and is it within budget?
            - Or, does the agent hallucinate any activities that are not available?
            - Or, does the agent suggest activities that are not suitable for the weather? This specific evaluation function  will require the use of an LLM to compare the event description against the weather data.

    5. Defining the Tools

        - We will define four tools to assist the agent
            - calculator_tool: to accurately calculate costs
            - get_activities_by_date_tool: to retrieve activities for a specific date
            - run_evals_tool: to evaluate the itinerary against the criteria
            - final_answer_tool: to provide the final answer in a structured format

    6. The ItineraryRevisionAgent
        - We will implement a second agent that revises the itinerary based on feedback using the ReAct THOUGHT → ACTION → OBSERVATION cycle.
            - The LLM will first generated a THOUGHT / ACTION message, which contains reasoning steps and a tool call invocation.
            - The Python code will parse the tool call and execute it, returning the result as a string to the LLM in an OBSERVATION message.
            - After this cycle repeats n number of times, the LLM will invoke the final_answer_tool to signal to the Python code to end the loop and return the final answer.

        - This agent will also incorporate feedback on the initial itinerary from the travelers to ensure the final plan has at least 2 activities per day. A new evaluation function using a powerful LLM will be created to check this user feedback.
        
        - The agent will use the tools above to refine the plan iteratively, checking the weather and available activities, and ensuring the itinerary meets all constraints.

    7. Something just for fun!
        - To wrap things up we'll create a fun, narrative summary of the trip, highlighting the best activities and experiences!


## Core Tasks & Project Specification

### You will be provided with a starter Jupyter Notebook (project_starter.ipynb) and a Python library (project_lib.py) containing helper functions and classes. Your primary responsibilities will be to complete the TODO sections in the starter notebook marked with **********, which involve:

    1. Configuring your OpenAI API Key.

    2. Create and read from a Pydantic model for the travelers' vacation information
        - Completing the VacationInfo Pydantic model
        - Gathering the weather and activity data for AgentsVille for the dates specified in VacationInfo

    3. Crafting the ITINERARY_AGENT_SYSTEM_PROMPT ItineraryAgent
        - This system prompt must instruct the LLM to act as an expert travel planner.
        - It must clearly define the task: to generate a comprehensive travel itinerary based on user preferences.
        - It must specify the output format, which must include a JSON object conforming to the TravelPlan Pydantic model structure that is provided in the notebook.
        - It must provided the necessary context needed to complete the task, e.g. the VacationInfo object and others.
        - It should encourage detailed, well-thought-out daily plans, using a Chain-of-Thought process. This process may be guided explicitly using instructions, examples, and/or by specifying the output format.

    4. Crafting the ACTIVITY_AND_WEATHER_ARE_COMPATIBLE_SYSTEM_PROMPT for the LLM-powered evaluation function
        - The prompt must provide a role, a task, output format, and examples.

    5. Define the docstring for the get_activities_by_date_tool evaluation function
        - The docstring must contain the expected input parameter names and data types

    6. Crafting ITINERARY_REVISION_AGENT_SYSTEM_PROMPT for the ItineraryRevisionAgent:
        - This system prompt must include a role
        - It specify the task, which involves refining the the itinerary using feedback from the tools.
            - In addition to running the run_evals_tool tool to get the initial feedback, it must also run the tool again before invoking the final_answer_tool
        - You must dynamically include the list of available_tools in this prompt, clearly describing each tool's name, purpose, and parameters.
        - It must clearly explain the THINK-ACT-OBSERVE cycle the LLM should follow.
            It must specify the exact format for tool call in the ACTION, which is {"tool_name": "[tool_name]", "arguments": {"arg1": "value1", ...}}
        - It must exit the ReAct loop by calling the final_answer_tool

## General Success Criteria

### You will have successfully completed the project when:

    - Your ITINERARY_AGENT_SYSTEM_PROMPT consistently guides the LLM to produce JSON output that successfully validates against the TravelPlan Pydantic model and reflects the user's preferences.

    - Your ITINERARY_REVISION_AGENT_SYSTEM_PROMPT enables the LLM to:
        - Always return a single message with both a THOUGHT and ACTION present
        - Contain reasoning steps within the THOUGHT section that allow the LLM to choose the tools it needs at the right time
        - Generate valid tool calls in the specified JSON format.
        - Call the final_answer_tool when after the evaluation criteria have passed
        - The final itinerary returned by the LLM does, in fact, pass the evaluation criteria

    - The overall "AgentsVille Trip Planner" can generate a reasonable final itinerary, taking into account interests, weather, and other constraints as well as incorporates the initial feedback from the travelers.
