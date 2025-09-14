"""
GraphManager class to handle SolutionGraph and SolutionTree instances per assignment.
This class manages the graph generation and solution processing for each assignment.
"""

import os
import PyPDF2
from solgraph import SolutionGraph, SolutionTree
from apimanager import APIManager

class GraphManager:
    def __init__(self):
        # Dictionary to store graph instances per assignment
        self.assignment_graphs = {}
        self.assignment_trees = {}
        
    def get_or_create_graph(self, assignment_id, problem_text, subject_domain="math"):
        """Get or create a SolutionGraph instance for the given assignment."""
        if assignment_id not in self.assignment_graphs:
            self.assignment_graphs[assignment_id] = SolutionGraph(problem_text, subject_domain)
        return self.assignment_graphs[assignment_id]
    
    def get_or_create_tree(self, assignment_id, problem_text, subject_domain="math"):
        """Get or create a SolutionTree instance for the given assignment."""
        if assignment_id not in self.assignment_trees:
            self.assignment_trees[assignment_id] = SolutionTree(problem_text, subject_domain)
        return self.assignment_trees[assignment_id]
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from a PDF file."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            print(f"Error extracting text from PDF {file_path}: {e}")
            return ""
    
    def process_solution(self, assignment_id, solution_uid, solution_text, solution_file_path, final_answer, correct_answer, problem_text=""):
        """Process a student solution and add it to both graph and tree."""
        # Determine if the solution is correct
        is_correct = final_answer and correct_answer and final_answer.strip().lower() == correct_answer.strip().lower()
        
        # Combine text solution and PDF text if available
        full_solution_text = solution_text or ""
        if solution_file_path and os.path.exists(solution_file_path):
            pdf_text = self.extract_text_from_pdf(solution_file_path)
            if pdf_text:
                full_solution_text += "\n\n" + pdf_text if full_solution_text else pdf_text
        
        if not full_solution_text.strip():
            return False
        
        # Add to graph
        graph = self.get_or_create_graph(assignment_id, problem_text)
        graph_success = graph.addSolution(solution_uid, full_solution_text, is_correct)
        
        # Add to tree
        tree = self.get_or_create_tree(assignment_id, problem_text)
        tree_success = tree.addSolution(solution_uid, full_solution_text, is_correct)
        
        return graph_success and tree_success
    
    def generate_graph(self, assignment_id):
        """Generate graph data for the given assignment."""
        if assignment_id not in self.assignment_graphs:
            return None
        return self.assignment_graphs[assignment_id].generateGraph()
    
    def generate_tree(self, assignment_id):
        """Generate tree data for the given assignment."""
        if assignment_id not in self.assignment_trees:
            return None
        return self.assignment_trees[assignment_id].generateTree()

# Global instance
graph_manager = GraphManager()
