from faiss import IndexFlatL2
import numpy as np
from apimanager import APIManager

class SolutionGraph:
    EMBED_DIM = 3072
    SEARCH_COUNT = 3
    DISTANCE_THRESHOLD = 3072
    api_manager=APIManager("bnxe")
    def __init__(self,problem_text,subject_domain="math"):
        self.index = IndexFlatL2(SolutionGraph.EMBED_DIM)
        self.solution_index = IndexFlatL2(SolutionGraph.EMBED_DIM)
        self.problem_text = problem_text
        self.index.add(np.array([
            [100.0] * SolutionGraph.EMBED_DIM,
            [-100.0] * SolutionGraph.EMBED_DIM
        ], dtype="float32"))
        self.stepSummary=["Read the problem statement", "Full Solution."]
        self.solutions=[]
        self.solution_is_correct=[]
        self.solution_uid_to_index={}
        self.solution_texts=[]
        self.subject_domain=subject_domain
        self.step_root=[0,1]
    def formatStepSummaryQuery(self,step):
        return [{"role":"system","content":f"You are a helpful assistant who concisely and without unnecessary details summarizes the key ideas of the following step of a solution to a {self.subject_domain} problem."},{"role":"user","content":f"The step is as follows:\n{step}"}]

    def formatVerificationQuery(self,step1,step2):
        return [
            {
                "role": "system",
                "content": f"""Fundamentally, are these two steps of two different solutions to a {self.subject_domain} problem the same? They need to use the all of the exact same ideas, the same technique, and the same means of execution.

Don't overthink it! It should be obvious whether or not they're doing the same thing or not: Okay reasons are, say, \"Solution 1 uses length XY while solution 2 does not; no.\"

Return one word: \"yes\" or \"no\", nothing else. I forbid you from thinking too much or analyzing the solutions too much."""
            },
            {
                "role": "user",
                "content": f"Solution 1:\n{step1}\n\nSolution 2:\n{step2}\n\nAnswer with yes or no only."
            }
        ]

    def formatSolutionDedupeQuery(self, sol1, sol2):
        return [
            {
                "role": "system",
                "content": """Fundamentally, are these two solutions the same? They need to use the all of the exact same ideas, the same technique, and the same means of execution.

Don't overthink it! It should be obvious whether or not they're doing the same thing or not: Okay reasons are, say, \"Solution 1 uses length XY while solution 2 does not; no.\"

Return one word: \"yes\" or \"no\", nothing else. I forbid you from thinking too much or analyzing the solutions too much."""
            },
            {
                "role": "user",
                "content": f"Solution 1:\n{sol1}\n\nSolution 2:\n{sol2}\n\nAnswer with yes or no only."
            }
        ]

    def is_duplicate_solution(self, new_solution_text):
        if self.solution_index.ntotal == 0:
            return (False, None)

        emb = self.api_manager.embedText(new_solution_text)
        if emb is None:
            return (False, None)

        q = np.array([emb], dtype="float32")
        k = min(SolutionGraph.SEARCH_COUNT, self.solution_index.ntotal)
        D, I = self.solution_index.search(q, k)
        for cand_idx in I[0]:
            cand_text = self.solution_texts[cand_idx]
            resp = SolutionGraph.api_manager.query(self.formatSolutionDedupeQuery(new_solution_text, cand_text))
            if resp is None:
                continue
            ans = resp.strip().lower()
            if "yes" in ans:
                return (True, cand_idx)
        return (False, None)

    def getIndex(self, step):
        embed = self.api_manager.embedText(step)
        if embed is None:
            return None
        embed_vector = np.array([embed], dtype="float32")
        distance, indices = self.index.search(embed_vector,min(self.index.ntotal,SolutionGraph.SEARCH_COUNT))
        self.index.add(embed_vector)
        curi = int(self.index.ntotal-1)  # Convert numpy int64 to Python int
        self.step_root.append(curi)
        
        # Convert indices to step_root references (FAISS returns 2D arrays)
        for i in range(0, len(indices[0])):
            if indices[0][i] < len(self.step_root):
                indices[0][i] = self.step_root[indices[0][i]]
        
        for i in range(0, len(indices[0])):
            if i < len(distance[0]) and distance[0][i] < SolutionGraph.DISTANCE_THRESHOLD:
                # Manually verify that they are same with LLM query
                if indices[0][i] < len(self.stepSummary):
                    response=SolutionGraph.api_manager.query(self.formatVerificationQuery(step,self.stepSummary[indices[0][i]]))
                    if response is None:
                        print("Failed to receive verification from API.")
                        continue
                    if response.strip().lower().startswith("y"):
                        ret = int(indices[0][i])  # Convert numpy int64 to Python int
                        self.step_root[curi] = ret
                        return ret
                    
        # No match found, generate new index + a summary of the step
        summary=self.api_manager.query(self.formatStepSummaryQuery(step));
        if summary is None:
            return None
        self.stepSummary.append(summary.strip())
        return int(len(self.stepSummary)-1)  # Convert to Python int

    def addSolution(self, solution_uid,solution_text,is_correct):
        # Solution-level dedupe first
        is_dup, dup_idx = self.is_duplicate_solution(solution_text)
        if is_dup:
            self.solution_uid_to_index[solution_uid] = dup_idx
            if is_correct and dup_idx < len(self.solution_is_correct) and not self.solution_is_correct[dup_idx]:
                self.solution_is_correct[dup_idx] = True
            return True

        response = self.api_manager.query([
    {"role": "system", "content": 
r'''You are a solution explainer.

Your task is to take a complete solution and reformat it into large, structured steps. Steps should be split before statements that change the course of the solution or require deep insight and a new idea.
Do not add new reasoning or solve the problem yourself — just restructure what is already there.  

For each step:  
- Give a short **title** (what technique/formula/idea is applied).  
- If applicable, show the **general formula or theorem**.  
- Summarize the **reasoning/work** for that step.  
- Do not create extra steps for trivial algebra, computation, or obvious logical steps.  
- Use inline LaTeX only. Do not use block LaTeX.

At the end, include the **final result**.

Format it like this:

### Step 1. [Technique / Formula Name]
Formula: ...  
Reasoning: ...

### Step 2. [Technique / Formula Name]
Formula: ...  
Reasoning: ...

...
'''}, {"role": "user", "content": solution_text}])

        if response is None:
            print("Failed to receive step breakdown from API.")
            return False
        
        steps = response.split("###")[1:]
        stepIndices=[]
        for step in steps:
            step = step.strip()
            if step:
                ind = self.getIndex(step)
                if ind is None:
                    print(f"Failed to embed step: {step}. Solution will not be added.")
                    return False
                else:
                    stepIndices.append(ind)

        self.solutions.append(stepIndices)
        self.solution_uid_to_index[solution_uid]=len(self.solutions)-1
        self.solution_is_correct.append(is_correct)
        
        # Index this solution text for future dedupe
        emb = self.api_manager.embedText(solution_text)
        if emb is not None:
            self.solution_index.add(np.array([emb], dtype="float32"))
            self.solution_texts.append(solution_text)
        return True
    
    '''
    Generates a graph of the solution
    Return dictionary
    {
        "graph" : list of edges,
        "step_summary" : list of step summaries,
        "step_is_correct" : list of boolean values,
        "submissions" : [
            {
                "submission_uid:" : string,
                "submission_nodes:" : list of nodes
            }
        ]
    }

    '''
    def generateGraph(self):
        graph = [[] for i in range(0,len(self.stepSummary))]
        inDegree = [0] * len(self.stepSummary)
        submissions = []
        n = len(self.stepSummary)
        
        # Build the graph from solutions
        for i in range(0,len(self.solutions)):
            for j in range(0,len(self.solutions[i])-1):
                graph[self.solutions[i][j]].append(self.solutions[i][j+1])
                inDegree[self.solutions[i][j+1]] += 1
        
        # Extract strongly connected components using Kosaraju's algorithm
        sccs = self.kosaraju_scc(graph, n)
        scc_indices = [0 for i in range(0,n)]
        for scc_id in range(0,len(sccs)):
            for node in sccs[scc_id]:
                scc_indices[node] = scc_id

        # Build the step summary graph
        step_graph=[]
        for solution in self.solutions:
            for j in range(0,len(solution)):
                found_prev = False
                found_next = False
                for k in range(j-1,-1,-1):
                    if scc_indices[solution[j]] != scc_indices[solution[k]]:
                        step_graph.append((int(solution[k]),int(solution[j])))  # Convert to Python int
                        found_prev = True
                        break
                for k in range(j+1,len(solution)):
                    if scc_indices[solution[j]] != scc_indices[solution[k]]:
                        step_graph.append((int(solution[j]),int(solution[k])))  # Convert to Python int
                        found_next = True
                        break
                if not found_prev:
                    step_graph.append((0,int(solution[j])))  # Convert to Python int
                if not found_next:
                    step_graph.append((int(solution[j]),n-1))  # Convert to Python int

        # Perform error marking
        step_is_correct = [False for i in range(0,n)]
        for i in range(0,len(self.solutions)):
            if self.solution_is_correct[i] is True:
                for j in self.solutions[i]:
                    step_is_correct[j]=True

        # Prepare submissions data
        for uid, idx in self.solution_uid_to_index.items():
            submissions.append({
                "submission_uid": uid,
                "submission_nodes": [0] + [int(x) for x in self.solutions[idx]] + [n-1]  # Ensure all values are Python int
            })
        
        return {
            "graph": step_graph, 
            "step_summary": self.stepSummary, 
            "step_is_correct": step_is_correct,
            "submissions": submissions
        }
    
    def kosaraju_scc(self, graph, n):
        """
        Kosaraju's algorithm to find strongly connected components
        Returns a list of SCCs, where each SCC is a list of node indices
        """
        # Step 1: Create transpose graph
        transpose_graph = [[] for _ in range(n)]
        for u in range(n):
            for v in graph[u]:
                transpose_graph[v].append(u)
        
        # Step 2: First DFS to get finish times (topological order)
        visited = [False] * n
        stack = []
        
        def dfs1(node):
            visited[node] = True
            for neighbor in graph[node]:
                if not visited[neighbor]:
                    dfs1(neighbor)
            stack.append(node)
        
        # Perform DFS on all unvisited nodes
        for i in range(n):
            if not visited[i]:
                dfs1(i)
        
        # Step 3: Second DFS on transpose graph in reverse order
        visited = [False] * n
        sccs = []
        
        def dfs2(node, scc):
            visited[node] = True
            scc.append(node)
            for neighbor in transpose_graph[node]:
                if not visited[neighbor]:
                    dfs2(neighbor, scc)
        
        # Process nodes in reverse order of finish times
        while stack:
            node = stack.pop()
            if not visited[node]:
                scc = []
                dfs2(node, scc)
                sccs.append(scc)
        
        return sccs
                
class SolutionTree:
    class Node:
        def pull_correctness(self):
            self.is_correct=any(child.is_correct for child in self.children)

        def __init__(self, step_text, creation_index):
            self.children = [] # Child
            self.parent = None
            self.is_correct = False
            self.creation_index = creation_index
            self.terminal=[]
            if step_text is not None:
                self.parent_summary = step_text

    api_manager=APIManager("bnxe")
    def __init__(self, problem_text, subject_domain="math"):
        self.problem_text = problem_text
        self.subject_domain = subject_domain
        self.numNodes = 0
        self.root = self.Node("Read the problem", self.numNodes)  # Root gets creation_index 0
        self.numNodes += 1
        self.solution_uid_to_index={}
        self.sol_count=0
    
    def generateTree(self):
        edges = []  # List of tuples (parent_creation_index, child_creation_index)
        node_summaries = [""] * self.numNodes  # Map creation_index -> node summary text
        node_correctness = [False] * self.numNodes  # Map creation_index -> is_correct status
        submissions = [{} for i in range(self.sol_count)]
        stack=[]
        def dfs(node):
            stack.append(node.creation_index)
            if hasattr(node, 'parent_summary'):
                node_summaries[node.creation_index] = node.parent_summary
            else:
                node_summaries[node.creation_index] = "Beginning of Solution"
                
            node_correctness[node.creation_index] = node.is_correct

            # Record terminal nodes for this path
            if hasattr(node, 'terminal') and node.terminal:
                for sol_idx in node.terminal:
                    submissions[sol_idx]["submission_nodes"] = stack.copy()

            # Record edges to children
            for child in node.children:
                edges.append((node.creation_index, child.creation_index))
                dfs(child)
            stack.pop()
        
        # Start DFS from root
        dfs(self.root)
        for uid, idx in self.solution_uid_to_index.items():
            submissions[idx]["submission_uid"]=uid
        return {
            "graph": edges,
            "step_summaries": node_summaries,
            "step_is_correct": node_correctness,
            "submissions" : submissions
        }
    
    def addSolution(self, solution_uid, solution_text, is_correct):
        cur_node = self.root
        nodeList=[]
        while True:
            nodeList.append(cur_node)
            # Find most similar child node
            res = -1
            if len(cur_node.children) == 0:
                cur_node.children.append(self.Node(solution_text,self.numNodes))
                self.numNodes += 1
                break
            if len(cur_node.children) > 0:
                query_string = "Here is the numbered list of possible first steps:\n"
                for i in range(0,len(cur_node.children)):
                    query_string += "Category "+str(i+1)+": \n"+cur_node.children[i].parent_summary+"\n"

                query_string += "\n"
                query_string += "Match the following solution to one of the first steps:\n"+solution_text+"\n\n"

                response = SolutionTree.api_manager.query([{"role":"system","content":r"You will be provided 1) A numbered list of possible first steps to a math problem and 2) A solution to that math problem. Task: Find the first step that best matches the user's solution. Do not think too hard. Respond with only the number of the best match in the following format:\n ### [Index]"},{"role":"user","content":query_string}])
                if response is None:
                    print("Failed to receive response from API.")
                    return False
                try:
                    parts = response.split("###")
                    if len(parts) < 2:
                        print("Invalid response format from API.")
                        return False
                    res = int(parts[1].strip()) - 1  # Convert to 0-based indexing
                    if res < 0 or res >= len(cur_node.children):
                        print(f"Invalid index {res+1} from API response. Must be between 1 and {len(cur_node.children)}.")
                        return False
                except (ValueError, IndexError) as e:
                    print(f"Error parsing API response: {e}")
                    return False

            shared=""
            unshared1=cur_node.children[res].parent_summary
            unshared2=solution_text
            if res != -1:
                shared=self.api_manager.query([{"role":"system","content":f"You will be given two solutions to a math problem. Task: Find the largest prefix of steps shared by both solutions, verifying equal intermediate values. Respond with only the shared prefix."},
{"role":"user","content":f"Solution 1:\n{cur_node.children[res].parent_summary}\nSolution 2:\n{solution_text}"}])
                if shared is None:
                    print("die")
                    return False
                unshared1=self.api_manager.query([{"role":"system","content":f"You will be given a solution to a math problem, as well as an incomplete prefix of that solution. Task: Find the part of the complete solution not included in the incomplete prefix. Respond with only the unshared part. If no part exists, respond with an empty string."},
{"role":"user","content":f"Full Solution:\n{cur_node.children[res].parent_summary}\nIncomplete Prefix:\n{shared}"}])
                if unshared1 is None:
                    print("die")
                    return False
                unshared2=self.api_manager.query([{"role":"system","content":f"You will be given a solution to a math problem, as well as an incomplete prefix of that solution. Task: Find the part of the complete solution not included in the incomplete prefix. Respond with only the unshared part. If no part exists, respond with an empty string."},
{"role":"user","content":f"Full Solution:\n{solution_text}\nIncomplete Prefix:\n{shared}"}])
                if unshared2 is None:
                    print("die")
                    return False
            shared = shared.strip()
            unshared1 = unshared1.strip()
            unshared2 = unshared2.strip()
            # Add new node
            if unshared1 != "":
                if shared != "":
                    cur_node.children.append(self.Node(shared,self.numNodes))
                    self.numNodes += 1
                    cur_node.children[-1].children.append(cur_node.children[res])
                    cur_node.children[res].parent_summary=unshared1
                    cur_node.children[-1],cur_node.children[res] = cur_node.children[res],cur_node.children[-1]
                    cur_node.children.pop()
                    cur_node=cur_node.children[res]
                cur_node.children.append(self.Node(unshared2,self.numNodes))
                self.numNodes += 1
                cur_node=cur_node.children[-1]
                break
            else:
                solution_text=unshared2
                cur_node=cur_node.children[res]
            if solution_text == "":
                break
        nodeList.append(cur_node)
        cur_node.terminal.append(self.sol_count)
        self.solution_uid_to_index[solution_uid] = self.sol_count
        if is_correct:
            cur_node.is_correct=True
            for node in reversed(nodeList):
                node.pull_correctness()
        self.sol_count+=1
        return True