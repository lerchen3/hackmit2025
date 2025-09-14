from faiss import IndexFlatL2
from openai import OpenAI
from apimanager import APIManager

class SolutionGraph:
    EMBED_DIM = 3072
    SEARCH_COUNT = 3
    DISTANCE_THRESHOLD = 3072
    api_manager=APIManager("test_api_key")
    def __init__(self,problem_text,subject_domain="math"):
        self.index = IndexFlatL2(EMBED_DIM)
        self.problem_text = problem_text
        self.index.add([100] * SolutionGraph.EMBED_DIM)
        self.index.add([-100] * SolutionGraph.EMBED_DIM)
        self.stepSummary=["Read the problem statement", "Full Solution."]
        self.solutions=[]
        self.solution_is_correct=[]
        self.solution_uid_to_index={}
        self.subject_domain=subject_domain
        self.step_root=[]
    def formatStepSummaryQuery(self,step):
        return [{"role":"system","content":f"You are a helpful assistant who concisely and without unnecessary details summarizes the key ideas of the following step of a solution to a {self.subject_domain} problem."},{"role":"user","content":f"The step is as follows:\n{step}"}]

    def formatVerificationQuery(self,step1,step2):
        return [{"role":"system","content":f"You are a helpful assistant who checks whether the key ideas of certain texts are the exact same. Respond with a Yes or No."},{"role":"user","content":f"Both texts are steps of a solution to a {self.subject_domain} problem. The first text is as follows:\n{step1} The second text is as follows:\n{step2} Are they functionally the same?"}]

    def getIndex(self, step):
        embed = self.api_manager.embedText(step)
        if embed is None:
            return None
        embed_vector=embed.data[0]
        distance, indices = self.index.search(embed_vector,SolutionGraph.SEARCH_COUNT)
        self.index.add(embed_vector)
        self.step_root.append(self.index.ntotal-1)
        for i in range(0,SolutionGraph.SEARCH_COUNT):
            if distance[i] < SolutionGraph.DISTANCE_THRESHOLD:
                # Manually verify that they are same with LLM query
                response=SolutionGraph.api_manager.query(self.formatVerificationQuery(step,self.stepSummary[indices[i]]))
                if response is None:
                    print("Failed to receive verification from API.")
                    continue
                if response.choices[0].message.content.strip()[0]=="Y":
                    ret = self.step_root[indices[i]]
                    self.step_root[-1] = ret
                    return ret
                    
        # No match found, generate new index + a summary of the step
        summary=self.api_manager.query(self.formatStepSummaryQuery(step));
        if summary is None:
            return None
        self.stepSummary.append(summary.choices[0].message.content.strip())
        return self.index.ntotal-1

    def addSolution(self, solution_uid,solution_text,is_correct):
        response = self.api_manager.query([{"role": "system", "content": f"You are a helpful assistant who can break down solutions to mathematics problems into smaller steps."}, 
                                    {"role": "user", "content": f"One of my students was trying to solve the following problem:\n" 
                                                                f"{self.problem_text}\n"
                                                                f"Their solution may have errors or be incomplete. "
                                                                f"Could you organize the solution into individual major steps in a way that highlights key ideas and formulas? Each step should begin with ###, followed by the step number and a short description, and include no other formatting. The solution is as follows:\n"
                                                                f"{solution_text}"}])

        if response is None:
            print("Failed to receive step breakdown from API.")
            return False
        
        steps = response.choices[0].message.content.split("###")[1:]
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
                found_prev = False, found_next= True
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
        for i in range(len(self.solutions)):
            submissions.append({
                "submission_uid": list(self.solution_uid_to_index.keys())[i],
                "submission_nodes": self.solutions[i]
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
        def __init__(self, step_text):
            self.children = [] # Child
            self.parent = None
            if step_text is not None:
                self.parent_summary = step_text
                self.parent_embed = api_manager.embedText(step_text)

    api_manager=APIManager("test_api_key")
    def __init__(self, problem_text, subject_domain="math"):
        self.problem_text = problem_text
        self.subject_domain = subject_domain
        self.root = self.Node(None)
    
    def generateTree(self):
        return self.solution_graph.generateGraph()
    
    def addSolution(self, solution_uid, solution_text, is_correct):
        cur_node = self.root
        while True:
            # Find most similar child node
            query_string="Match the following solution:\n"+solution_text+"\n\n"
            query_string += "To the following list of next steps:\n"
            for child in cur_node.children:
                query_string += child.parent_summary+"\n"

            SolutionTree.api_manager.query([{"role":"system","content":r"You are a helpful assistant who tries to find, out of a list of next steps, the one that most matches the user's solution. Respond with only the index of the most similar step."}])
            
            res = ;

            shared=""
            unshared=solution_text
            if res != "No Matches Found":
                response = SolutionTree.api_manager.query([{"role":}]) # Compute lca
                shared,unshared=response.split("#####")
            shared = shared.strip()
            unshared = unshared.strip()
            # Add new node
            if shared != "":
                cur_node.children.append(self.Node(solution_text))
                cur_node.children[-1],cur_node.children[sol_id] = cur_node.children[sol_id],cur_node.children[-1]
                sol_id = len(cur_node.children)-1
                intermediate_node = self.Node(shared)
                intermediate_node.children.append(cur_node.children[sol_id])
                intermediate_node.children.append(self.Node(unshared))
            

