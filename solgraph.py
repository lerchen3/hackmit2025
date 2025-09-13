from faiss import IndexFlatL2
from openai import OpenAI
from apimanager import APIManager

class SolutionGraph:
    EMBED_DIM = 3072
    api_manager=APIManager()
    def __init__(self,problem_text):
        self.index = IndexFlatL2(EMBED_DIM)
        self.problem_text = problem_text

    def addSolution(self, solution_text):
        response = api_manager.query([{"role": "system", "content": "You are a helpful assistant that can break down solutions into smaller steps and return them in a list."}, 
                            {"role": "user", "content": f"I was unable to solve the following problem:\n" 
                                                        f"{problem_text}\n"
                                                        f"I came across a potentially incomplete solution to the problem online, but I am unable to understand it."
                                                        f"Could you break down the solution into individual steps? The solution is as follows:\n"
                                                        f"{solution_text}"}])
        if response is None:
            print("Failed to receive step breakdown from API.")
            return False

        


    def chat_with_o1_mini(self, message, system_prompt=None):
        """
        Simple ChatGPT request to o1-mini model
        """
        try:
            client = OpenAI(api_key=self.api_manager.api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="o1-mini",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error making request: {str(e)}"


    def search(self, query, k=10):
        return self.index.search(query, k)