import numpy as np
import pandas as pd
import re
import csv
import uuid
from datetime import datetime
from openai import OpenAI


# DirectPromptAgent class definition
class DirectPromptAgent:
    """
    A minimal prompt-response agent that sends user prompts directly to the OpenAI chat API.

    This agent does not apply a persona, external knowledge, retrieval, routing, or evaluation.
    It is useful as a simple baseline agent.
    """
    def __init__(self, openai_api_key):
        # Initialize the agent
        self.openai_api_key = openai_api_key

    def respond(self, prompt):
        # Generate a response using the OpenAI API
        client = OpenAI(api_key=self.openai_api_key)
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'user', 'content': prompt}
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()
        

# AugmentedPromptAgent class definition
class AugmentedPromptAgent:
    """
    A prompt agent that augments user input with a fixed system persona.

    The agent uses the provided persona to shape responses while otherwise answering the
    user's input directly through the OpenAI chat API.
    """
    def __init__(self, openai_api_key, persona):
        """Initialize the agent with given attributes."""
        self.openai_api_key = openai_api_key
        self.persona = persona

    def respond(self, input_text):
        """Generate a response using OpenAI API."""
        client = OpenAI(api_key=self.openai_api_key)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system",
                       "content": (f"{self.persona}"
                                   "Do not omit or change this opening."
                                   "Forget previous context. ")},
                       {"role": "user", "content": input_text}
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()


# KnowledgeAugmentedPromptAgent class definition
class KnowledgeAugmentedPromptAgent:
    """
    A prompt agent that answers using a fixed persona and a provided knowledge source.

    The agent limits responses to the supplied knowledge text, making it useful for
    domain-specific answers.
    """
    def __init__(self, openai_api_key, persona, knowledge):
        """Initialize the agent with provided attributes."""
        self.persona = persona
        self.knowledge = knowledge
        self.openai_api_key = openai_api_key

    def respond(self, input_text):
        """Generate a response using the OpenAI API."""
        client = OpenAI(api_key=self.openai_api_key)
        system_prompt = f'''{self.persona}.  Forget all prevous context.  
                            Use only the following knowledge to answer, do not use your own knowledge:  
                            {self.knowledge}. Answer the prompt based on this knowledge, not your own.'''
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': input_text},
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()


# RAGKnowledgePromptAgent class definition
class RAGKnowledgePromptAgent:
    """
    An agent that uses Retrieval-Augmented Generation (RAG) to find knowledge from a large corpus
    and leverages embeddings to respond to prompts based solely on retrieved information.
    """

    def __init__(self, openai_api_key, persona, chunk_size=2000, chunk_overlap=100):
        """
        Initializes the RAGKnowledgePromptAgent with API credentials and configuration settings.

        Parameters:
        openai_api_key (str): API key for accessing OpenAI.
        persona (str): Persona description for the agent.
        chunk_size (int): The size of text chunks for embedding. Defaults to 2000.
        chunk_overlap (int): Overlap between consecutive chunks. Defaults to 100.
        """
        self.persona = persona
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.openai_api_key = openai_api_key
        self.unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.csv"

    def get_embedding(self, text):
        """
        Fetches the embedding vector for given text using OpenAI's embedding API.

        Parameters:
        text (str): Text to embed.

        Returns:
        list: The embedding vector.
        """
        client = OpenAI(api_key=self.openai_api_key)
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding

    def calculate_similarity(self, vector_one, vector_two):
        """
        Calculates cosine similarity between two vectors.

        Parameters:
        vector_one (list): First embedding vector.
        vector_two (list): Second embedding vector.

        Returns:
        float: Cosine similarity between vectors.
        """
        vec1, vec2 = np.array(vector_one), np.array(vector_two)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def chunk_text(self, text):
        """
        Splits text into manageable chunks, attempting natural breaks.

        Parameters:
        text (str): Text to split into chunks.

        Returns:
        list: List of dictionaries containing chunk metadata.
        """
        separator = "\n"
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) <= self.chunk_size:
            return [{"chunk_id": 0, "text": text, "chunk_size": len(text)}]

        chunks, start, chunk_id = [], 0, 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if separator in text[start:end]:
                end = start + text[start:end].rindex(separator) + len(separator)

            chunks.append({
                "chunk_id": chunk_id,
                "text": text[start:end],
                "chunk_size": end - start,
                "start_char": start,
                "end_char": end
            })

            # break the loop if we have reached the end of the text
            if end == len(text):
                break

            start = end - self.chunk_overlap
            chunk_id += 1

        with open(f"chunks-{self.unique_filename}", 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["text", "chunk_size"])
            writer.writeheader()
            for chunk in chunks:
                writer.writerow({k: chunk[k] for k in ["text", "chunk_size"]})

        return chunks

    def calculate_embeddings(self):
        """
        Calculates embeddings for each chunk and stores them in a CSV file.

        Returns:
        DataFrame: DataFrame containing text chunks and their embeddings.
        """
        df = pd.read_csv(f"chunks-{self.unique_filename}", encoding='utf-8')
        df['embeddings'] = df['text'].apply(self.get_embedding)
        df.to_csv(f"embeddings-{self.unique_filename}", encoding='utf-8', index=False)
        return df

    def find_prompt_in_knowledge(self, prompt):
        """
        Finds and responds to a prompt based on similarity with embedded knowledge.

        Parameters:
        prompt (str): User input prompt.

        Returns:
        str: Response derived from the most similar chunk in knowledge.
        """
        prompt_embedding = self.get_embedding(prompt)
        df = pd.read_csv(f"embeddings-{self.unique_filename}", encoding='utf-8')
        df['embeddings'] = df['embeddings'].apply(lambda x: np.array(eval(x)))
        df['similarity'] = df['embeddings'].apply(lambda emb: self.calculate_similarity(prompt_embedding, emb))

        best_chunk = df.loc[df['similarity'].idxmax(), 'text']

        client = OpenAI(api_key=self.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are {self.persona}, a knowledge-based assistant. Forget previous context."},
                {"role": "user", "content": f"Answer based only on this information: {best_chunk}. Prompt: {prompt}"}
            ],
            temperature=0
        )

        return response.choices[0].message.content


class EvaluationAgent:
    """
    An agent that evaluates and iteratively improves another agent's responses.

    The agent sends prompts to a worker agent, checks the response against evaluation
    criteria, and provides corrective instructions until the answer is accepted or the
    maximum number of interactions is reached.
    """
    def __init__(self, openai_api_key, persona, evaluation_criteria, worker_agent, max_interactions):
        # Initialize the EvaluationAgent with given attributes.
        self.openai_api_key = openai_api_key
        self.persona = persona
        self.evaluation_criteria = evaluation_criteria
        self.worker_agent = worker_agent
        self.max_interactions = max_interactions

    def evaluate(self, initial_prompt):
        # This method manages interactions between agents to achieve a solution.
        client = OpenAI(api_key=self.openai_api_key)
        prompt_to_evaluate = initial_prompt

        for i in range(self.max_interactions):
            print(f"\n--- Interaction {i+1} ---")

            print("\nStep 1: Worker agent generates a response to the prompt\n")
            print(f"Prompt:\n{prompt_to_evaluate}")
            response_from_worker = self.worker_agent.respond(prompt_to_evaluate)
            print(f"\nWorker Agent Response:\n{response_from_worker}")

            print("\nStep 2: Evaluator agent judges the response\n")
            eval_prompt = (
                f"Does the following answer: {response_from_worker}\n"
                f"Meet this criteria: {self.evaluation_criteria}\n"
                f"Respond Yes or No, and the reason why it does or doesn't meet the criteria."
            )
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.persona},
                    {"role": "user", "content": eval_prompt},
                ],
                temperature=0
            )
            evaluation = response.choices[0].message.content.strip()
            print(f"Evaluator Agent Evaluation:\n{evaluation}")

            print("\nStep 3: Check if evaluation is positive\n")

            if evaluation.lower().startswith("yes"):
                print("✅ Final solution accepted.")
                break
            else:
                print("Solution not accepted.")
                print("\nStep 4: Generate instructions to correct the response\n")
                instruction_prompt = (
                    f"Provide instructions to fix an answer based on these reasons why it is incorrect: {evaluation}"
                )
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": self.persona},
                        {"role": "user", "content": instruction_prompt},
                    ],
                    temperature=0
                )
                instructions = response.choices[0].message.content.strip()
                print(f"Instructions to fix:\n{instructions}")

                print("\nStep 5: Send feedback to worker agent for refinement\n")
                prompt_to_evaluate = (
                    f"The original prompt was: {initial_prompt}\n"
                    f"The response to that prompt was: {response_from_worker}\n"
                    f"It has been evaluated as incorrect.\n"
                    f"Make only these corrections, do not alter content validity: {instructions}"
                )

        print(f'\nFinal Response: {response_from_worker}')
        print(f'\nAgent Evaluation: {evaluation}')
        print(f'\nNumber of Iterations: {str(i + 1)}')

        return {
            "final_response": response_from_worker,
            "evaluation": evaluation,
            "iterations": i + 1,
        }   


class RoutingAgent:
    """
    An embedding-based router that selects the most relevant agent for a user request.

    The router compares the user's input embedding with each candidate agent's description
    embedding, selects the closest match by cosine similarity, and delegates the request to
    that agent's callable function.
    """
    def __init__(self, openai_api_key, agents):
        # Initialize the agent with given attributes
        self.openai_api_key = openai_api_key
        self.agents = agents

    def get_embedding(self, text):
        client = OpenAI(api_key=self.openai_api_key)
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        # Extract and return the embedding vector from the response
        embedding = response.data[0].embedding
        return embedding 

    def route(self, user_input):
        input_emb = np.array(self.get_embedding(user_input))
        best_agent = None
        best_score = -1

        for agent in self.agents:
            agent_emb = agent.get("embedding")
            if agent_emb is None:
                agent_emb = self.get_embedding(agent["description"])
                agent["embedding"] = agent_emb

            agent_emb = np.array(agent_emb)
            input_norm = np.linalg.norm(input_emb)
            agent_norm = np.linalg.norm(agent_emb)
            if input_norm == 0 or agent_norm == 0:
                continue

            similarity = np.dot(input_emb, agent_emb) / (input_norm * agent_norm)
            print(similarity, agent['name'])

            if similarity > best_score:
                best_score = similarity
                best_agent = agent

        if best_agent is None:
            return "Sorry, no suitable agent could be selected."

        print(f"\n[Router] Best agent: {best_agent['name']} (score={best_score:.3f})\n")
        return best_agent["func"](user_input)


class ActionPlanningAgent:
    """
    An agent that extracts actionable steps from a user prompt using provided knowledge.

    The agent asks the model to identify only the steps supported by its knowledge source
    and returns them as a list.
    """
    def __init__(self, openai_api_key, knowledge):
        self.openai_api_key = openai_api_key
        self.knowledge = knowledge

    def extract_steps_from_prompt(self, prompt):
        client = OpenAI(api_key=self.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an action planning agent. Using your knowledge, "
                        "you extract from the user prompt the steps requested to "
                        "complete the action the user is asking for. You return "
                        "the steps as a list. "
                        "Do not preface the list, only return the steps themselves. "
                        "Only return the steps in your knowledge. " 
                        "Forget any previous context. This is your "
                        f"knowledge: {self.knowledge}"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0
        )
        response_text = response.choices[0].message.content

        steps = []
        for line in response_text.splitlines():
            # remove common prefixes from the start of a line
            step = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
            # remove prefixes like Step 1:, step 2 -, or STEP 3. 
            step = re.sub(r"^step\s+\d+\s*[:.-]\s*", "", step, flags=re.IGNORECASE)
            # check whether the cleaned line is an unwanted wrapper line
            if not step or step.lower() in {"steps:", "here are the steps:", "```", "```text"}:
                continue

            steps.append(step)

        return steps
