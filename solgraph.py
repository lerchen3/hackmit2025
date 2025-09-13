from faiss import IndexFlatL2
from openai import OpenAI
from apimanager import APIManager

class SolutionGraph:
    EMBED_DIM = 128
    SEARCH_COUNT = 3
    DISTANCE_THRESHOLD = 1536
    api_manager=APIManager("test_api_key")
    def __init__(self,problem_text,subject_domain="math"):
        self.index = IndexFlatL2(EMBED_DIM)
        self.problem_text = problem_text
        self.stepSummary=[]
        self.solutions=[]
        self.solution_uid_to_index={}
        self.subject_domain=subject_domain
    def formatStepSummaryQuery(self,step):
        return [{"role":"system","content":f"You are a helpful assistant who concisely and without unnecessary details summarizes the key ideas of the following step of a solution to a {self.subject_domain} problem."},{"role":"user","content":f"The step is as follows:\n{step}"}]

    def formatVerificationQuery(self,step1,step2):
        return [{"role":"system","content":f"You are a helpful assistant who checks whether the key ideas of certain texts are the exact same."},{"role":"user","content":f"Both texts are steps of a solution to a {self.subject_domain} problem. The first text is as follows:\n{step1} The second text is as follows:\n{step2} Please answer with a Yes or No."}]

    def getIndex(self, step):
        embed = self.api_manager.embedText(step)
        if embed is None:
            return None
        embed_vector=embed.data[0]
        distance, indices = self.index.search(embed_vector,SolutionGraph.SEARCH_COUNT)
        for i in range(0,SolutionGraph.SEARCH_COUNT):
            if distance[i] < SolutionGraph.DISTANCE_THRESHOLD:
                # Manually verify that they are same with LLM query
                response=SolutionGraph.api_manager.query(self.formatVerificationQuery(step,self.stepSummary[indices[i]]))
                if response.choices[0].message.content.strip()[0]=="Y":
                    return indices[i]
                    
        # No match found, generate new index + a summary of the step
        summary=self.api_manager.query(self.formatStepSummaryQuery(step));
        if summary is None:
            return None
        self.index.add(embed_vector)
        self.stepSummary.append(summary.choices[0].message.content.strip())
        return self.index.ntotal-1

    def addSolution(self, solution_uid,solution_text):
        response = SolutionGraph.api_manager.query([{"role": "system", "content": "You are a helpful assistant that can break down solutions into smaller steps and return them in a list."}, 
                            {"role": "user", "content": f"I was unable to solve the following problem:\n" 
                                                        f"{problem_text}\n"
                                                        f"I came across a potentially incomplete solution to the problem online, but I am unable to understand it."
                                                        f"Could you break down the solution into individual steps in a way that highlights key ideas and formulas instead of simplification and computation? Adding concise comments and titles for each step would be helpful. The solution is as follows:\n"
                                                        f"{solution_text}"}])
        if response is None:
            print("Failed to receive step breakdown from API.")
            return False
        
        steps = response.split("###").pop(0)
        stepIndices=[]
        for step in steps:
            step = step.strip()
            if step:
                ind = getIndex(step)
                if ind is None:
                    print(f"Failed to embed step: {step}. Will skip adding this solution.")
                else:
                    stepIndices.append(ind)

        self.solutions.append(stepIndices)
        self.solution_uid_to_index[solution_uid]=len(self.solutions)-1
        return False
    
    '''
    Generates a graph of the solution
    Return dictionary
    {
        "graph" : list of edges,
        "step_summary" : list of step summaries,
        "submissions" : [
            {
                "submission_uid:" : string,
                "submission_nodes:" : list of nodes
            }
        ]
    }

    '''
    def generateGraph(self):
        graph = []
        step_summary = []
        submissions = []
        n = len(self.stepSummary)
        for i in range(0,len(self.solutions)):
            for j in self.solutions[i]:
                
                