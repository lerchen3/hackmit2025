from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import json

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
    
    # Calculate total solutions for all assignments
    total_solutions = sum(len(assignment.solutions) for assignment in assignments)
    
    return render_template('teacher_dashboard.html', assignments=assignments, total_solutions=total_solutions)

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
            description_image=description_image,
            created_by=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('create_assignment.html')

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
    
    # This is a placeholder for the graph generation
    # In a real implementation, you would analyze the solutions and generate a graph
    solutions = Solution.query.filter_by(assignment_id=assignment_id).all()
    
    # Generate graph data in the new format with 0-indexed integer nodes
    graph_data = {
        'graph': [
            {'from': 0, 'to': 1},
            {'from': 1, 'to': 2},
            {'from': 2, 'to': 3},
            {'from': 3, 'to': 4},
            {'from': 1, 'to': 5},
            {'from': 5, 'to': 6},
            {'from': 4, 'to': 6}
        ],
        'step_summary': [
            'Start',      # step 0
            'Apply first method',      # step 1
            'Apply second method',     # step 2
            'Apply third method',     # step 2
            'Apply fourth method',     # step 2
            'Finalize solution',       # step 3
            'End'                 # step 4
        ],
        'step_is_correct': [
            True,   # step 0
            True,   # step 1
            True,   # step 2
            True,   # step 3
            True,    # step 4
            True,    # step 5
            True,    # step 6
        ],
        'submissions': [
            {
                'submission_uid': 'student1_1',
                'submission_nodes': [0, 1, 2, 3, 4, 6]
            },
            {
                'submission_uid': 'student2_2',
                'submission_nodes': [0, 1, 5, 6]
            }
        ]
    }
    
    # Add student submissions
    # for solution in solutions:
    #     student = User.query.get(solution.student_id)
    #     if student:
    #         # Mock submission data - in real implementation, analyze the solution
    #         submission_nodes = [0, 1, 2, 3, 4, 5, 6]  # 0-indexed integer steps
    #         graph_data['submissions'].append({
    #             'submission_uid': f"{student.username}_{solution.id}",
    #             'submission_nodes': submission_nodes
    #         })
    
    return jsonify(graph_data)

@app.route('/api/solution-graph-tree/<int:assignment_id>')
@login_required
def get_solution_graph_tree(assignment_id):
    if not current_user.is_teacher:
        return jsonify({'error': 'Access denied'}), 403
    
    # This is a placeholder for the tree graph generation
    # In a real implementation, you would analyze the solutions and generate a tree graph
    solutions = Solution.query.filter_by(assignment_id=assignment_id).all()
    
    # Generate tree graph data with hierarchical structure
    graph_data = {
        'graph': [
            {'from': 0, 'to': 1},
            {'from': 0, 'to': 2},
            {'from': 1, 'to': 3},
            {'from': 1, 'to': 4},
            {'from': 2, 'to': 5},
            {'from': 2, 'to': 6}
        ],
        'step_summary': [
            'Start',                    # step 0 - root
            'Method A',                 # step 1 - level 1
            'Method B',                 # step 2 - level 1
            'Sub-method A1',           # step 3 - level 2
            'Sub-method A2',           # step 4 - level 2
            'Sub-method B1',           # step 5 - level 2
            'Final Step'               # step 6 - level 2 (now a regular process node)
        ],
        'step_is_correct': [
            True,   # step 0
            True,   # step 1
            True,   # step 2
            True,   # step 3
            True,   # step 4
            True,   # step 5
            True,   # step 6
        ],
        'submissions': [
            {
                'submission_uid': 'student1_1',
                'submission_nodes': [0, 1, 3, 6]  # Path through Method A -> Sub-method A1 -> Final Step
            },
            {
                'submission_uid': 'student2_2',
                'submission_nodes': [0, 2, 5, 6]  # Path through Method B -> Sub-method B1 -> Final Step
            }
        ]
    }
    
    return jsonify(graph_data)

# Database migration function
def migrate_database():
    """Add final_answer column to Solution table if it doesn't exist"""
    with app.app_context():
        try:
            # Check if final_answer column exists
            result = db.engine.execute("PRAGMA table_info(solution)")
            columns = [row[1] for row in result]
            
            if 'final_answer' not in columns:
                print("Adding final_answer column to Solution table...")
                db.engine.execute("ALTER TABLE solution ADD COLUMN final_answer TEXT")
                print("Migration completed successfully!")
            else:
                print("final_answer column already exists.")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_database()
    app.run(debug=True, host='0.0.0.0', port=5001)
