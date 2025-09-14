from faiss import IndexFlatL2
import numpy as np
from apimanager import APIManager

class SolutionGraph:
    EMBED_DIM = 3072
    SEARCH_COUNT = 3
    DISTANCE_THRESHOLD = 3072
    api_manager=APIManager("test_api_key")
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
        return [{"role":"system","content":f"You are a helpful assistant who checks whether the key ideas of certain texts are the exact same. Respond with a Yes or No."},{"role":"user","content":f"Both texts are steps of a solution to a {self.subject_domain} problem. The first text is as follows:\n{step1} The second text is as follows:\n{step2} Are they functionally the same?"}]

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
        distance, indices = self.index.search(embed_vector,SolutionGraph.SEARCH_COUNT)
        self.index.add(embed_vector)
        self.step_root.append(self.index.ntotal-1)
        for i in range(0,SolutionGraph.SEARCH_COUNT):
            if distance[0][i] < SolutionGraph.DISTANCE_THRESHOLD:
                # Manually verify that they are same with LLM query
                response=SolutionGraph.api_manager.query(self.formatVerificationQuery(step,self.stepSummary[indices[0][i]]))
                if response is None:
                    print("Failed to receive verification from API.")
                    continue
                if response.strip().lower().startswith("y"):
                    ret = self.step_root[indices[0][i]]
                    self.step_root[-1] = ret
                    return ret
                    
        # No match found, generate new index + a summary of the step
        summary=self.api_manager.query(self.formatStepSummaryQuery(step));
        if summary is None:
            return None
        self.stepSummary.append(summary.strip())
        return self.index.ntotal-1

    def addSolution(self, solution_uid,solution_text,is_correct):
        # Solution-level dedupe first
        is_dup, dup_idx = self.is_duplicate_solution(solution_text)
        if is_dup:
            self.solution_uid_to_index[solution_uid] = dup_idx
            if is_correct and dup_idx < len(self.solution_is_correct) and not self.solution_is_correct[dup_idx]:
                self.solution_is_correct[dup_idx] = True
            return True

        response = self.api_manager.query([{"role": "system", "content": f"You are a helpful assistant who can break down solutions to mathematics problems into smaller steps."}, 
                                    {"role": "user", "content": f"One of my students was trying to solve the following problem:\n" 
                                                                f"{self.problem_text}\n"
                                                                f"Their solution may have errors or be incomplete. "
                                                                f"Could you organize the solution into individual major steps in a way that highlights key ideas and formulas? Each step should begin with ###, followed by the step number and a short description, and include no other formatting. The solution is as follows:\n"
                                                                f"{solution_text}"}])

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
        inDegree = [0 for i in range(0,len(self.stepSummary))]
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
                        step_graph.append((solution[k],solution[j]))
                        found_prev = True
                        break
                for k in range(j+1,len(solution)):
                    if scc_indices[solution[j]] != scc_indices[solution[k]]:
                        step_graph.append((solution[j],solution[k]))
                        found_next = True
                        break
                if not found_prev:
                    step_graph.append((0,solution[j]))
                if not found_next:
                    step_graph.append((solution[j],1))

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
                "submission_nodes": self.solutions[idx]
            })
        
        return {
            "graph": graph, 
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
            if step_text is not None:
                self.parent_summary = step_text

    api_manager=APIManager("test_api_key")
    def __init__(self, problem_text, subject_domain="math"):
        self.problem_text = problem_text
        self.subject_domain = subject_domain
        self.numNodes = 0
        self.root = self.Node(None, self.numNodes)  # Root gets creation_index 0
        self.numNodes += 1
        self.solution_uid_to_index={}
        self.solutions=[]
    
    def generateTree(self):
        edges = []  # List of tuples (parent_creation_index, child_creation_index)
        node_summaries = [""] * self.numNodes  # Map creation_index -> node summary text
        node_correctness = [False] * self.numNodes  # Map creation_index -> is_correct status
        
        def dfs(node):
            if hasattr(node, 'parent_summary'):
                node_summaries[node.creation_index] = node.parent_summary
            else:
                node_summaries[node.creation_index] = "Beginning of Solution"
                
            node_correctness[node.creation_index] = node.is_correct
            
            # Record edges to children
            for child in node.children:
                edges.append((node.creation_index, child.creation_index))
                dfs(child)
        
        # Start DFS from root
        dfs(self.root)
        submissions = []
        for uid, idx in self.solution_uid_to_index.items():
            submissions.append({
                "submission_uid": uid,
                "submission_nodes": self.solutions[idx]
            })
        return {
            "edges": edges,
            "node_summaries": node_summaries,
            "step_is_correct": node_correctness,
            "submissions" : submissions
        }
    
    def addSolution(self, solution_uid, solution_text, is_correct):
        self.solution_uid_to_index[solution_uid] = len(self.solutions)
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
                query_string += "Here is the list of category next steps:\n"
                for i in range(0,len(cur_node.children)):
                    query_string += "Category "+str(i+1)+": \n"+cur_node.children[i].parent_summary+"\n"

                query_string += "\n"
                query_string="Match the following solution:\n"+solution_text+"\n\n"

                response = SolutionTree.api_manager.query([{"role":"system","content":r"You are given a list of category next steps and a user's solution. Find the one that most matches the user's solution. Respond with only the index of the most similar category in the following format:\n ### [Index]"},{"role":"user","content":query_string}])
                if response is None:
                    print("Failed to receive response from API.")
                    return False
                res = response.split("###")[1].strip()
                res = int(res)            

            shared=""
            unshared1=cur_node.children[res].parent_summary
            unshared2=solution_text
            if res != -1:
                response = SolutionTree.api_manager.query([{"role":"system","content":f"You are given two possibly incomplete solutions to a {self.subject_domain} problem. Find the largest prefix of steps that the two solutions have in common, verifying equal intermediate values. If there are no shared steps, simply respond with an empty string. Respond with the shared part and the unshared parts in the following format:\n ###\n [Shared Steps] ###\n [Unshared steps from first solution] ###\n [Unshared steps from second solution]"},{"role":"user","content":f"Solution 1:\n{cur_node.children[res].parent_summary}\nSolution 2:\n{solution_text}"}])
                if response is None:
                    print("die")
                    return False
                shared,unshared1,unshared2=response.split("###")[1:]
            shared = shared.strip()
            unshared1 = unshared1.strip()
            unshared2 = unshared2.strip()
            # Add new node
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
            solution_text=unshared2
            if solution_text == "":
                break
        node_list.append(cur_node)
        if cur_node.is_correct:
            cur_node.is_correct=True
            for node in reversed(nodeList):
                node.pull_correctness()
        self.solutions.append(nodeList)
        return True
