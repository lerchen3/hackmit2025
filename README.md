# Assignment Management System

A comprehensive Flask web application for managing assignments between teachers and students, featuring solution visualization and feedback systems.

## Features

### For Teachers
- **Assignment Creation**: Create assignments with text descriptions and optional images
- **Solution Management**: View all student solutions for each assignment
- **Feedback System**: Provide detailed feedback to students on their submissions
- **Graph Visualization**: Interactive graph analysis of student solution patterns
- **Dashboard**: Overview of all assignments and submission statistics

### For Students
- **Assignment Access**: View all available assignments with descriptions
- **Solution Submission**: Submit solutions as text or PDF files
- **Feedback Review**: View teacher feedback on submitted solutions
- **Progress Tracking**: Monitor submission status and progress

### System Features
- **Authentication**: Separate login systems for teachers (password) and students (name only)
- **File Management**: Secure file upload and storage for assignments and solutions
- **Responsive Design**: Modern, mobile-friendly interface
- **Interactive Graphs**: D3.js-powered visualization of solution patterns

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone or download the project**
   ```bash
   cd /Users/lunchbox/Documents/hackmit2
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Usage

### Getting Started

1. **Register Users**
   - Teachers: Register with username and password
   - Students: Register with username only (no password required)

2. **Teacher Workflow**
   - Login with teacher credentials
   - Create assignments with descriptions and optional images
   - View student solutions and provide feedback
   - Use graph visualization to analyze solution patterns

3. **Student Workflow**
   - Login with student username
   - View available assignments
   - Submit solutions as text or PDF files
   - Check for teacher feedback

### Key Features

#### Assignment Creation
- Teachers can create assignments with:
  - Descriptive titles
  - Text descriptions
  - Optional image attachments
  - Automatic timestamping

#### Solution Submission
- Students can submit solutions in multiple formats:
  - Text responses
  - PDF file uploads
  - Combination of both
- File size limit: 16MB
- Supported file types: PDF for solutions, images for assignments

#### Feedback System
- Teachers can provide detailed feedback on student solutions
- Students can view feedback in their dashboard
- Feedback is linked to specific assignments and students

#### Graph Visualization
- Interactive D3.js-powered graphs
- Visual representation of solution patterns
- Student path highlighting
- Aesthetic and modern design

## File Structure

```
hackmit2/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── teacher_dashboard.html
│   ├── create_assignment.html
│   ├── view_solutions.html
│   ├── solution_detail.html
│   ├── student_dashboard.html
│   └── view_assignment.html
├── static/               # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── uploads/              # File uploads (created automatically)
    ├── assignments/
    └── solutions/
```

## Database Schema

The application uses SQLite with the following models:

- **User**: Stores teacher and student information
- **Assignment**: Assignment details and metadata
- **Solution**: Student submissions linked to assignments
- **Feedback**: Teacher feedback on student solutions

## Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key for sessions
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `UPLOAD_FOLDER`: Directory for file uploads
- `MAX_CONTENT_LENGTH`: Maximum file upload size

### Security Notes
- Change the `SECRET_KEY` in production
- Use environment variables for sensitive configuration
- Implement proper file validation in production
- Consider using a more robust database (PostgreSQL) for production

## API Endpoints

### Authentication
- `GET /` - Home page (redirects based on user type)
- `GET/POST /login` - User login
- `GET/POST /register` - User registration
- `GET /logout` - User logout

### Teacher Routes
- `GET /teacher/dashboard` - Teacher dashboard
- `GET/POST /teacher/assignment/create` - Create assignment
- `GET /teacher/assignment/<id>/solutions` - View solutions
- `GET /teacher/solution/<id>` - View solution detail
- `POST /teacher/feedback/<assignment_id>/<student_id>` - Submit feedback

### Student Routes
- `GET /student/dashboard` - Student dashboard
- `GET /student/assignment/<id>` - View assignment
- `POST /student/assignment/<id>/submit` - Submit solution

### API Routes
- `GET /api/solution-graph/<assignment_id>` - Get graph data

## Technologies Used

- **Backend**: Flask, SQLAlchemy, Werkzeug
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Visualization**: D3.js
- **Database**: SQLite
- **File Handling**: Pillow (PIL)

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Change the port in `app.py`: `app.run(debug=True, port=5001)`

2. **File upload errors**
   - Check file size limits
   - Ensure upload directories exist
   - Verify file permissions

3. **Database errors**
   - Delete `assignment_system.db` to reset the database
   - Check SQLite installation

4. **Static files not loading**
   - Ensure the `static` directory structure is correct
   - Check file permissions

### Development Tips

- Use `debug=True` for development
- Check browser console for JavaScript errors
- Monitor Flask logs for backend issues
- Use browser developer tools for debugging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the code comments
3. Create an issue in the repository

---

**Note**: This is a development version. For production use, implement additional security measures, use a production database, and follow Flask best practices.
