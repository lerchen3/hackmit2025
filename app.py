from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import json
from dotenv import load_dotenv
import csv
import time
from graph_manager import graph_manager
from apimanager import APIManager

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assignment_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directories
os.makedirs('uploads/assignments', exist_ok=True)
os.makedirs('uploads/solutions', exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize API manager for LLM operations
try:
    api_manager = APIManager("bnxe")
except Exception as e:
    print(f"Warning: Could not initialize API manager: {e}")
    api_manager = None

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=True)  # None for students
    is_teacher = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_assignments = db.relationship('Assignment', backref='creator', lazy='select')
    solutions = db.relationship('Solution', backref='student', lazy='select')
    feedback_given = db.relationship('Feedback', foreign_keys='Feedback.teacher_id', backref='teacher', lazy='select')
    feedback_received = db.relationship('Feedback', foreign_keys='Feedback.student_id', backref='student_feedback', lazy='select')

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description_text = db.Column(db.Text, nullable=True)
    description_image = db.Column(db.String(200), nullable=True)
    correct_answer = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    solutions = db.relationship('Solution', backref='assignment', lazy='select')
    feedbacks = db.relationship('Feedback', backref='assignment', lazy='select')

class Solution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    solution_text = db.Column(db.Text, nullable=True)
    solution_file = db.Column(db.String(200), nullable=True)
    final_answer = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Note: feedback relationship is handled manually in routes for better performance

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_teacher:
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.is_teacher:
            if user.password_hash and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('teacher_dashboard'))
            else:
                flash('Invalid password', 'error')
        elif user and not user.is_teacher:
            # Student login (no password required)
            login_user(user)
            return redirect(url_for('student_dashboard'))
        else:
            flash('User not found', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        is_teacher = 'is_teacher' in request.form
        password = request.form.get('password', '')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        password_hash = None
        if is_teacher and password:
            password_hash = generate_password_hash(password)
        
        user = User(username=username, password_hash=password_hash, is_teacher=is_teacher)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if not current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    
    assignments = Assignment.query.filter_by(created_by=current_user.id).all()
    students = User.query.filter_by(is_teacher=False).all()
    
    # Calculate total solutions for all assignments
    total_solutions = sum(len(assignment.solutions) for assignment in assignments)
    
    return render_template('teacher_dashboard.html', assignments=assignments, students=students, total_solutions=total_solutions)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    assignments = Assignment.query.all()
    solutions = Solution.query.filter_by(student_id=current_user.id).all()
    feedbacks = Feedback.query.filter_by(student_id=current_user.id).all()
    
    # Load assignment information for each solution and feedback
    for solution in solutions:
        solution.assignment = Assignment.query.get(solution.assignment_id)
    
    for feedback in feedbacks:
        feedback.assignment = Assignment.query.get(feedback.assignment_id)
    
    return render_template('student_dashboard.html', assignments=assignments, solutions=solutions, feedbacks=feedbacks)

@app.route('/teacher/assignment/create', methods=['GET', 'POST'])
@login_required
def create_assignment():
    if not current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        description_text = request.form.get('description_text', '')
        correct_answer = request.form['correct_answer']
        description_image = None
        
        if 'description_image' in request.files:
            file = request.files['description_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'assignments', filename)
                file.save(file_path)
                description_image = filename
        
        assignment = Assignment(
            title=title,
            description_text=description_text,
            correct_answer=correct_answer,
            description_image=description_image,
            created_by=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('create_assignment.html')

@app.route('/teacher/students/create', methods=['GET', 'POST'])
@login_required
def create_student():
    if not current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form.get('password', '')  # Optional password for students
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'error')
            return render_template('create_student.html')
        
        # Create new student account
        new_student = User(
            username=username,
            password_hash=generate_password_hash(password) if password else None,
            is_teacher=False
        )
        
        try:
            db.session.add(new_student)
            db.session.commit()
            flash(f'Student account "{username}" created successfully!', 'success')
            return redirect(url_for('teacher_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating student account', 'error')
            return render_template('create_student.html')
    
    return render_template('create_student.html')

@app.route('/student/assignment/<int:assignment_id>')
@login_required
def view_assignment(assignment_id):
    if current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    solution = Solution.query.filter_by(assignment_id=assignment_id, student_id=current_user.id).first()
    feedback = Feedback.query.filter_by(assignment_id=assignment_id, student_id=current_user.id).first()
    
    return render_template('view_assignment.html', assignment=assignment, solution=solution, feedback=feedback)

@app.route('/student/assignment/<int:assignment_id>/submit', methods=['POST'])
@login_required
def submit_solution(assignment_id):
    if current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    solution_text = request.form.get('solution_text', '')
    final_answer = request.form.get('final_answer', '')
    solution_file = None
    
    if 'solution_file' in request.files:
        file = request.files['solution_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'solutions', filename)
            file.save(file_path)
            solution_file = filename
    
    # Update existing solution or create new one
    solution = Solution.query.filter_by(assignment_id=assignment_id, student_id=current_user.id).first()
    if solution:
        solution.solution_text = solution_text
        solution.solution_file = solution_file
        solution.final_answer = final_answer
        solution.submitted_at = datetime.utcnow()
    else:
        solution = Solution(
            assignment_id=assignment_id,
            student_id=current_user.id,
            solution_text=solution_text,
            solution_file=solution_file,
            final_answer=final_answer
        )
        db.session.add(solution)
    
    db.session.commit()
    
    # Process solution with graph manager
    try:
        assignment = Assignment.query.get(assignment_id)
        if assignment:
            solution_file_path = None
            if solution_file:
                solution_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'solutions', solution_file)
            
            solution_uid = f"{current_user.username}_{solution.id}"
            problem_text = assignment.description_text or ""
            graph_manager.process_solution(
                assignment_id=assignment_id,
                solution_uid=solution_uid,
                solution_text=solution_text,
                solution_file_path=solution_file_path,
                final_answer=final_answer,
                correct_answer=assignment.correct_answer,
                problem_text=problem_text
            )
    except Exception as e:
        print(f"Error processing solution with graph manager: {e}")
        # Don't fail the submission if graph processing fails
    
    flash('Solution submitted successfully!', 'success')
    return redirect(url_for('view_assignment', assignment_id=assignment_id))

@app.route('/teacher/assignment/<int:assignment_id>/solutions')
@login_required
def view_solutions(assignment_id):
    if not current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    solutions = Solution.query.filter_by(assignment_id=assignment_id).all()
    students = User.query.filter_by(is_teacher=False).all()
    
    # Load student information for each solution
    for solution in solutions:
        solution.student = User.query.get(solution.student_id)
        solution.feedback = Feedback.query.filter_by(assignment_id=solution.assignment_id, student_id=solution.student_id).first()
    
    return render_template('view_solutions.html', assignment=assignment, solutions=solutions, students=students)

@app.route('/teacher/solution/<int:solution_id>')
@login_required
def view_solution_detail(solution_id):
    if not current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    
    solution = Solution.query.get_or_404(solution_id)
    assignment = Assignment.query.get(solution.assignment_id)
    student = User.query.get(solution.student_id)
    feedback = Feedback.query.filter_by(assignment_id=solution.assignment_id, student_id=solution.student_id).first()
    
    return render_template('solution_detail.html', solution=solution, assignment=assignment, student=student, feedback=feedback)

@app.route('/teacher/feedback/<int:assignment_id>/<int:student_id>', methods=['POST'])
@login_required
def submit_feedback(assignment_id, student_id):
    if not current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    
    feedback_text = request.form['feedback_text']
    
    # Update existing feedback or create new one
    feedback = Feedback.query.filter_by(assignment_id=assignment_id, student_id=student_id).first()
    if feedback:
        feedback.feedback_text = feedback_text
        feedback.teacher_id = current_user.id
    else:
        feedback = Feedback(
            assignment_id=assignment_id,
            student_id=student_id,
            teacher_id=current_user.id,
            feedback_text=feedback_text
        )
        db.session.add(feedback)
    
    db.session.commit()
    flash('Feedback submitted successfully!', 'success')
    return redirect(url_for('view_solution_detail', solution_id=request.form.get('solution_id')))

@app.route('/teacher/feedback/bulk', methods=['POST'])
@login_required
def submit_bulk_feedback():
    if not current_user.is_teacher:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    student_ids = data.get('student_ids', [])
    feedback_text = data.get('feedback_text', '')
    
    if not assignment_id or not student_ids or not feedback_text:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        for student_id in student_ids:
            # Update existing feedback or create new one
            feedback = Feedback.query.filter_by(assignment_id=assignment_id, student_id=student_id).first()
            if feedback:
                feedback.feedback_text = feedback_text
                feedback.teacher_id = current_user.id
            else:
                feedback = Feedback(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    teacher_id=current_user.id,
                    feedback_text=feedback_text
                )
                db.session.add(feedback)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Feedback submitted to {len(student_ids)} student(s)'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to submit feedback'}), 500

@app.route('/api/generate-personalized-feedback', methods=['POST'])
@login_required
def generate_personalized_feedback():
    if not current_user.is_teacher:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    student_ids = data.get('student_ids', [])
    base_feedback = data.get('base_feedback', '')
    
    if not assignment_id or not student_ids or not base_feedback:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Get assignment details
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Get solutions for selected students
        solutions = Solution.query.filter(
            Solution.assignment_id == assignment_id,
            Solution.student_id.in_(student_ids)
        ).all()
        
        if not solutions:
            return jsonify({'error': 'No solutions found for selected students'}), 404
        
        # Generate personalized feedback for each student
        personalized_feedbacks = {}
        
        for solution in solutions:
            student = User.query.get(solution.student_id)
            if not student:
                continue
                
            # Prepare context for LLM
            context = {
                "assignment_title": assignment.title,
                "assignment_description": assignment.description_text or "",
                "correct_answer": assignment.correct_answer,
                "student_username": student.username,
                "student_solution": solution.solution_text or "",
                "student_final_answer": solution.final_answer or "",
                "base_feedback": base_feedback
            }
            
            # Create prompt for personalized feedback
            prompt = f"""You are an experienced teacher providing personalized feedback to students. Based on the following information, generate specific, constructive feedback for the student.

Assignment: {context['assignment_title']}
Description: {context['assignment_description']}
Correct Answer: {context['correct_answer']}

Student: {context['student_username']}
Student's Solution: {context['student_solution']}
Student's Final Answer: {context['student_final_answer']}

Base Feedback from Teacher: {context['base_feedback']}

Please generate personalized feedback that:
1. Acknowledges the student's specific approach and work
2. Points out what they did well
3. Identifies specific areas for improvement
4. Provides constructive suggestions
5. Maintains an encouraging and supportive tone
6. Is specific to their solution, not generic

Keep the feedback concise but meaningful (2-3 paragraphs). Focus on being helpful and encouraging while providing actionable guidance."""

            # Generate personalized feedback using LLM
            llm_response = None
            if api_manager:
                llm_response = api_manager.query({
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.7
                })
            
            if llm_response:
                personalized_feedbacks[solution.student_id] = {
                    "student_name": student.username,
                    "personalized_feedback": llm_response.strip()
                }
            else:
                # Fallback to base feedback if LLM fails
                personalized_feedbacks[solution.student_id] = {
                    "student_name": student.username,
                    "personalized_feedback": base_feedback
                }
        
        return jsonify({
            'success': True,
            'personalized_feedbacks': personalized_feedbacks
        })
        
    except Exception as e:
        print(f"Error generating personalized feedback: {e}")
        return jsonify({'error': 'Failed to generate personalized feedback'}), 500

@app.route('/teacher/assignment/<int:assignment_id>/submit-solutions', methods=['GET', 'POST'])
@login_required
def submit_solutions_for_students(assignment_id):
    if not current_user.is_teacher:
        flash('Access denied', 'error')
        return redirect(url_for('student_dashboard'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    students = User.query.filter_by(is_teacher=False).all()
    
    if request.method == 'POST':
        try:
            created_solutions = []

            # CSV upload path
            csv_file = request.files.get('solutions_csv')
            if csv_file and csv_file.filename:
                # Optional explicit student_ids mapping; supports JSON list or comma-separated
                raw_student_ids = request.form.get('student_ids')
                mapped_students = []
                if raw_student_ids:
                    try:
                        if raw_student_ids.strip().startswith('['):
                            ids = json.loads(raw_student_ids)
                        else:
                            ids = [int(x) for x in raw_student_ids.split(',') if x.strip()]
                        # Fetch students preserving provided order
                        id_to_student = {u.id: u for u in User.query.filter(User.id.in_(ids)).all()}
                        mapped_students = [id_to_student.get(i) for i in ids if i in id_to_student]
                    except Exception:
                        mapped_students = []
                if not mapped_students:
                    # Default: all non-teacher students sorted by username
                    mapped_students = User.query.filter_by(is_teacher=False).order_by(User.username.asc()).all()

                # Parse CSV
                content = csv_file.read().decode('utf-8', errors='ignore')
                reader = csv.DictReader(content.splitlines())
                rows = list(reader)
                if not rows:
                    flash('CSV appears empty.', 'error')
                    return redirect(url_for('submit_solutions_for_students', assignment_id=assignment_id))
                missing_cols = [c for c in ["Solution", "Final_Answer"] if c not in reader.fieldnames]
                if missing_cols:
                    flash(f"CSV missing required columns: {', '.join(missing_cols)}", 'error')
                    return redirect(url_for('submit_solutions_for_students', assignment_id=assignment_id))

                limit = min(len(rows), len(mapped_students))
                if len(rows) != len(mapped_students):
                    flash(f"Note: pairing first {limit} row(s) to {limit} student(s) by order.", 'warning')

                for idx in range(limit):
                    row = rows[idx]
                    student = mapped_students[idx]
                    if not student:
                        continue
                    solution_text = (row.get('Solution') or '').strip()
                    final_answer = (row.get('Final_Answer') or '').strip()
                    if not solution_text and not final_answer:
                        continue

                    existing_solution = Solution.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=student.id
                    ).first()

                    if existing_solution:
                        existing_solution.solution_text = solution_text
                        existing_solution.final_answer = final_answer
                        existing_solution.submitted_at = datetime.utcnow()
                        db.session.commit()
                        created_solutions.append(existing_solution)
                    else:
                        solution = Solution(
                            assignment_id=assignment_id,
                            student_id=student.id,
                            solution_text=solution_text,
                            final_answer=final_answer
                        )
                        db.session.add(solution)
                        db.session.commit()
                        created_solutions.append(solution)

                    # 10ms delay between rows
                    time.sleep(0.01)

            else:
                # JSON form field path (existing behavior)
                solutions_data = request.form.get('solutions_data')
                if not solutions_data:
                    flash('No solution data provided', 'error')
                    return redirect(url_for('submit_solutions_for_students', assignment_id=assignment_id))

                solutions = json.loads(solutions_data)

                for solution_data in solutions:
                    student_id = solution_data.get('student_id')
                    solution_text = solution_data.get('solution_text', '')
                    final_answer = solution_data.get('final_answer', '')

                    if not student_id or (not solution_text and not final_answer):
                        continue

                    existing_solution = Solution.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=student_id
                    ).first()

                    if existing_solution:
                        existing_solution.solution_text = solution_text
                        existing_solution.final_answer = final_answer
                        existing_solution.submitted_at = datetime.utcnow()
                        db.session.commit()
                        created_solutions.append(existing_solution)
                    else:
                        solution = Solution(
                            assignment_id=assignment_id,
                            student_id=student_id,
                            solution_text=solution_text,
                            final_answer=final_answer
                        )
                        db.session.add(solution)
                        db.session.commit()
                        created_solutions.append(solution)
            
            # Process solutions with graph manager
            for solution in created_solutions:
                try:
                    # Ensure relationship for username
                    if not getattr(solution, 'student', None):
                        solution.student = User.query.get(solution.student_id)
                    solution_uid = f"{solution.student.username}_{solution.id}"
                    problem_text = assignment.description_text or ""
                    graph_manager.process_solution(
                        assignment_id=assignment_id,
                        solution_uid=solution_uid,
                        solution_text=solution.solution_text,
                        solution_file_path=None,
                        final_answer=solution.final_answer,
                        correct_answer=assignment.correct_answer,
                        problem_text=problem_text
                    )
                except Exception as e:
                    print(f"Error processing solution with graph manager: {e}")
                    # Don't fail the submission if graph processing fails

            flash(f'Successfully submitted {len(created_solutions)} solution(s) for students!', 'success')
            return redirect(url_for('view_solutions', assignment_id=assignment_id))
        except Exception as e:
            db.session.rollback()
            flash('Error submitting solutions. Please try again.', 'error')
            return redirect(url_for('submit_solutions_for_students', assignment_id=assignment_id))
    
    return render_template('submit_solutions_for_students.html', assignment=assignment, students=students)


@app.route('/uploads/assignments/<filename>')
def uploaded_assignment_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], 'assignments', filename))

@app.route('/uploads/solutions/<filename>')
def uploaded_solution_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], 'solutions', filename))

@app.route('/api/solution-graph/<int:assignment_id>')
@login_required
def get_solution_graph(assignment_id):
    if not current_user.is_teacher:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get graph data from graph manager
        graph_data = graph_manager.generate_graph(assignment_id)
        
        if graph_data is None:
            print(f"No graph data found for assignment {assignment_id}")
            # Check if there are any solutions for this assignment
            solutions = Solution.query.filter_by(assignment_id=assignment_id).all()
            print(f"Found {len(solutions)} solutions for assignment {assignment_id}")
            
            # No solutions processed yet, return empty graph
            return jsonify({
                'graph': [],
                'step_summary': ['Start', 'End'],
                'step_is_correct': [True, True],
                'submissions': []
            })
        
        print(f"Generated graph data for assignment {assignment_id}: {len(graph_data.get('submissions', []))} submissions")
        return jsonify(graph_data)
    except Exception as e:
        print(f"Error generating solution graph: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to generate graph'}), 500

@app.route('/api/solution-graph-tree/<int:assignment_id>')
@login_required
def get_solution_graph_tree(assignment_id):
    if not current_user.is_teacher:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get tree data from graph manager
        tree_data = graph_manager.generate_tree(assignment_id)
        
        if tree_data is None:
            # No solutions processed yet, return empty tree
            return jsonify({
                'graph': [],
                'step_summary': ['Start', 'End'],
                'step_is_correct': [True, True],
                'submissions': []
            })
        
        return jsonify(tree_data)
    except Exception as e:
        print(f"Error generating solution tree: {e}")
        return jsonify({'error': 'Failed to generate tree'}), 500

# Database migration function
def migrate_database():
    """Add final_answer column to Solution table if it doesn't exist"""
    with app.app_context():
        try:
            # Check if final_answer column exists
            result = db.session.execute(db.text("PRAGMA table_info(solution)"))
            columns = [row[1] for row in result]
            
            if 'final_answer' not in columns:
                print("Adding final_answer column to Solution table...")
                db.session.execute(db.text("ALTER TABLE solution ADD COLUMN final_answer TEXT"))
                db.session.commit()
                print("Migration completed successfully!")
            else:
                print("final_answer column already exists.")
        except Exception as e:
            print(f"Migration error: {e}")

def process_existing_solutions():
    """Process existing solutions with the graph manager"""
    try:
        solutions = Solution.query.all()
        for solution in solutions:
            assignment = Assignment.query.get(solution.assignment_id)
            if assignment:
                solution_file_path = None
                if solution.solution_file:
                    solution_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'solutions', solution.solution_file)
                
                solution_uid = f"{solution.student.username}_{solution.id}"
                problem_text = assignment.description_text or ""
                graph_manager.process_solution(
                    assignment_id=solution.assignment_id,
                    solution_uid=solution_uid,
                    solution_text=solution.solution_text,
                    solution_file_path=solution_file_path,
                    final_answer=solution.final_answer,
                    correct_answer=assignment.correct_answer,
                    problem_text=problem_text
                )
        print(f"Processed {len(solutions)} existing solutions")
    except Exception as e:
        print(f"Error processing existing solutions: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_database()
        # Process existing solutions on startup
        process_existing_solutions()
    
    # Start the app
    app.run(debug=True, host='0.0.0.0', port=5003)
