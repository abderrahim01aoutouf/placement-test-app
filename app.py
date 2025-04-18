from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from models.database import db, init_db, Student, TestResult
from datetime import datetime
import json
from flask_wtf.csrf import CSRFProtect
import os
from functools import wraps
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import csv
from flask_migrate import Migrate
from openpyxl import Workbook

# Remove environment variables if they exist
os.environ.pop('ADMIN_USERNAME', None)
os.environ.pop('ADMIN_PASSWORD_HASH', None)

# Reload from file
load_dotenv('.env', override=True)

# Application configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_tests.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Test file paths
TEST_PATHS = {
    'adult_general': 'static/data/adult_general.json',
    'adult_exam_prep': 'static/data/adult_exam_prep.json',
    'teenager': 'static/data/teenager.json',
    'kids': 'static/data/kids.json'
}

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '').strip()
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', '').strip()

if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    raise RuntimeError("Missing admin configuration in .env")

app.config['WTF_CSRF_TIME_LIMIT'] = 3600

def load_test_questions(test_type):
    """Load questions from the appropriate JSON file"""
    try:
        file_path = TEST_PATHS.get(test_type)
        if not file_path:
            abort(400, description="Invalid test type")
            
        with open(file_path, 'r') as f:
            return json.load(f)
            
    except FileNotFoundError:
        abort(404, description="Test file not found")
    except json.JSONDecodeError:
        abort(500, description="Question format error")
    except Exception as e:
        app.logger.error(f"Critical error: {str(e)}")
        abort(500)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Admin login route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('admin_login'))
        
        try:
            if (username == ADMIN_USERNAME and 
                check_password_hash(ADMIN_PASSWORD_HASH, password)):
                session['admin_logged_in'] = True
                session.permanent = False  # Additional security
                return redirect(url_for('admin_dashboard'))
        except Exception as e:
            app.logger.error(f"Authentication error: {str(e)}")
        
        flash('Incorrect credentials', 'danger')
    
    return render_template('admin_login.html')

# Admin dashboard route
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Retrieve students with their results
    students_with_results = []
    
    students = Student.query.all()
    for student in students:
        # Get the most recent test result
        test_result = TestResult.query.filter_by(student_id=student.id).order_by(TestResult.test_date.desc()).first()
        
        student_data = {
            'id': student.id,
            'full_name': student.full_name,
            'age': student.age,
            'email': student.email,
            'phone': student.phone,
            'category': student.category,
            'test_type': student.test_type,
            'registration_date': student.registration_date.strftime('%Y-%m-%d %H:%M:%S'),
            'score': test_result.score if test_result else None,
            'level': test_result.level if test_result else None,
            'test_date': test_result.test_date.strftime('%Y-%m-%d %H:%M:%S') if test_result else None,
            'access_code': student.access_code 
        }
        
        students_with_results.append(student_data)
    
    return render_template('admin_dashboard.html', students=students_with_results)

@app.route('/admin/export_excel')
@admin_required
def export_excel():
    file_path = os.path.join(app.static_folder, 'data/students_export.xlsx')
    
    # Create a new Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    
    # Add header
    headers = ['ID', 'Name', 'Access Code', 'Age', 'Email', 'Phone', 'Category', 
               'Test Type', 'Score', 'Level', 'Registration Date', 'Test Date']
    ws.append(headers)
    
    # Add data
    students = Student.query.all()
    for student in students:
        result = TestResult.query.filter_by(student_id=student.id).order_by(TestResult.test_date.desc()).first()
        category_name = {
            'adult': 'Adult',
            'teenager': 'Teenager',
            'kids': 'Child'
        }.get(student.category, student.category)
        
        test_type_name = {
            'general': 'General Communication',
            'exam_prep': 'Exam Preparation'
        }.get(student.test_type, student.test_type)
        
        ws.append([
            student.id, 
            student.full_name, 
            student.access_code,
            student.age, 
            student.email, 
            student.phone,
            category_name, 
            test_type_name, 
            result.score if result else None,
            result.level if result else None, 
            student.registration_date.strftime('%Y-%m-%d %H:%M:%S'), 
            result.test_date.strftime('%Y-%m-%d %H:%M:%S') if result else None
        ])
    
    # Format the table
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width
    
    # Save the file
    wb.save(file_path)
    
    flash('Excel export completed successfully ✅', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export_csv')
@admin_required
def export_csv():
    file_path = os.path.join(app.static_folder, 'data/students_export.csv')
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Age', 'Email', 'Phone', 'Category', 'Test Type', 'Score', 'Level', 'Registration Date', 'Test Date'])

        students = Student.query.all()
        for student in students:
            result = TestResult.query.filter_by(student_id=student.id).order_by(TestResult.test_date.desc()).first()
            writer.writerow([
                student.id, student.full_name, student.age, student.email, student.phone,
                student.category, student.test_type, result.score if result else '',
                result.level if result else '', student.registration_date, result.test_date if result else ''
            ])
    
    flash('CSV export completed successfully ✅', 'success')
    return redirect(url_for('admin_dashboard'))

# Route to export data as JSON
@app.route('/admin/export')
@admin_required
def admin_export():
    # Retrieve students with their results
    students_with_results = []
    
    students = Student.query.all()
    for student in students:
        # Get all test results for this student
        test_results = TestResult.query.filter_by(student_id=student.id).all()
        
        results_data = []
        for result in test_results:
            results_data.append({
                'id': result.id,
                'test_date': result.test_date.strftime('%Y-%m-%d %H:%M:%S'),
                'score': result.score,
                'level': result.level,
                'answers': json.loads(result.answers)
            })
        
        student_data = {
            'id': student.id,
            'full_name': student.full_name,
            'age': student.age,
            'email': student.email,
            'phone': student.phone,
            'category': student.category,
            'test_type': student.test_type,
            'registration_date': student.registration_date.strftime('%Y-%m-%d %H:%M:%S'),
            'test_results': results_data
        }
        
        students_with_results.append(student_data)
    
    # Create static/data directory if it doesn't exist
    data_dir = os.path.join(app.static_folder, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Save data to a JSON file
    file_path = os.path.join(data_dir, 'students_export.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(students_with_results, f, ensure_ascii=False, indent=4)
    
    flash('JSON export completed successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clean_database', methods=['POST'])
@admin_required
def clean_database():
    """Delete all data: results and students"""
    try:
        # First delete all test results (to respect FK constraints)
        TestResult.query.delete()
        
        # Then delete all students
        Student.query.delete()
        
        db.session.commit()
        flash("All data has been successfully deleted", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error cleaning the database: {str(e)}", 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clean_results', methods=['POST'])
@admin_required
def clean_results():
    """Delete only test results, keep students"""
    try:
        # Delete all test results
        TestResult.query.delete()
        db.session.commit()
        flash("All test results have been successfully deleted", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting results: {str(e)}", 'danger')
    
    return redirect(url_for('admin_dashboard'))

# Route to log out
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

# Application routes

# Registration and validation routes

@app.route('/admin/create_student', methods=['GET', 'POST'])
@admin_required
def admin_create_student():
    """Route for admin to create a new student"""
    if request.method == 'POST':
        full_name = request.form['full_name']
        age = int(request.form['age'])
        email = request.form['email']
        phone = request.form['phone']
        
        # Determine category
        if age < 12:
            category = 'kids'
        elif age < 18:
            category = 'teenager'
        else:
            category = 'adult'
        
        # Generate unique access code
        access_code = Student.generate_access_code()
        
        # Create student
        new_student = Student(
            full_name=full_name,
            age=age,
            email=email,
            phone=phone,
            category=category,
            access_code=access_code,
            is_approved=True  # Automatically approved since created by admin
        )
        
        try:
            db.session.add(new_student)
            db.session.commit()
            flash(f"Student created successfully. Access code: {access_code}", 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash("Registration error: This email is already in use" if "UNIQUE constraint failed" in str(e) 
                  else f"Error during registration: {str(e)}", 'danger')
    
    return render_template('admin_create_student.html')

@app.route('/admin/approve_student/<int:student_id>', methods=['POST'])
@admin_required
def admin_approve_student(student_id):
    """Route for admin to approve a student"""
    student = Student.query.get_or_404(student_id)
    student.is_approved = True
    
    try:
        db.session.commit()
        flash(f"Student {student.full_name} has been successfully approved.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error during approval: {str(e)}", 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for a student to register themselves (pending approval)"""
    if request.method == 'POST':
        full_name = request.form['full_name']
        age = int(request.form['age'])
        email = request.form['email']
        phone = request.form['phone']
        
        # Determine category
        if age < 12:
            category = 'kids'
        elif age < 18:
            category = 'teenager'
        else:
            category = 'adult'
        
        # Generate unique access code
        access_code = Student.generate_access_code()
        
        # Create student (not approved)
        new_student = Student(
            full_name=full_name,
            age=age,
            email=email,
            phone=phone,
            category=category,
            access_code=access_code,
            is_approved=False  # Waiting for admin approval
        )
        
        try:
            db.session.add(new_student)
            db.session.commit()
            flash("Your registration has been recorded and is pending approval by an administrator. "
                  f"Your access code is: {access_code}. Keep it safe.", 'info')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash("Registration error: This email is already in use" if "UNIQUE constraint failed" in str(e) 
                  else f"Error during registration: {str(e)}", 'danger')
    
    return render_template('registration.html')

@app.route('/student_access', methods=['GET', 'POST'])
def student_access():
    """Route to access with an access code"""
    if request.method == 'POST':
        access_code = request.form['access_code'].upper()
        student = Student.query.filter_by(access_code=access_code).first()
        
        if not student:
            flash("Invalid access code. Please try again.", 'danger')
            return redirect(url_for('student_access'))
            
        if not student.is_approved:
            flash("Your account is pending approval by an administrator.", 'warning')
            return redirect(url_for('student_access'))
        
        # If everything is correct, store the student ID in the session
        session['student_id'] = student.id
        return redirect(url_for('test_selection'))
    
    return render_template('student_access.html')

@app.route('/test_selection', methods=['GET', 'POST'])
def test_selection():
    """Check that the student is logged in before accessing test selection"""
    if 'student_id' not in session:
        flash("Please enter your access code to continue.", 'warning')
        return redirect(url_for('student_access'))
    
    student = Student.query.get(session['student_id'])
    
    if request.method == 'POST':
        if student.category == 'adult':
            student.test_type = request.form['test_type']
            db.session.commit()
        
        return redirect(url_for('take_test'))
    
    return render_template('test_selection.html', student=student)

@app.route('/test', methods=['GET', 'POST'])
def take_test():
    if 'student_id' not in session:
        return redirect(url_for('register'))
    
    student = Student.query.get(session['student_id'])
    
    # Determine test type
    if student.category == 'adult':
        test_type = f'adult_{student.test_type}'
    else:
        test_type = student.category
    
    questions = load_test_questions(test_type)
    
    if request.method == 'POST':
        answers = {}
        score = 0
        
        for q_id in request.form:
            if q_id.startswith('q_'):
                question_num = int(q_id[2:])
                answers[question_num] = request.form[q_id]
                
                if question_num <= len(questions) and request.form[q_id] == questions[question_num - 1]['correct_answer']:
                    score += 1
        
        # Calculate level
        max_score = len(questions)
        level = calculate_level(score, max_score, test_type)
        
        # Save result
        test_result = TestResult(
            student_id=student.id,
            answers=json.dumps(answers),
            score=score,
            level=level
        )
        
        try:
            db.session.add(test_result)
            db.session.commit()
            session['result_id'] = test_result.id
            return redirect(url_for('show_results'))
        except Exception as e:
            db.session.rollback()
            abort(500, description="Error saving results")
    
    return render_template('test.html', student=student, questions=questions)

def calculate_level(score, max_score, test_type):
    """Calculate level based on score and test type"""
    
    # Extract the base category from test_type (adult_general -> adult, etc.)
    base_category = test_type.split('_')[0] if '_' in test_type else test_type
    
    if base_category == 'kids':
        # Kids level calculation (0-5, 6-10, 11-20, 21-30, 31-40, 41-50)
        if score <= 5:
            return "Starter level"
        elif score <= 10:
            return "Level 1 (CEFR Pre-A1)"
        elif score <= 20:
            return "Level 2 (CEFR Pre-A1)"
        elif score <= 30:
            return "Level 3 (CEFR A1)"
        elif score <= 40:
            return "Level 4 (CEFR A1)"
        else:
            return "Level 5 (CEFR A2)"
            
    elif base_category == 'teenager':
        # Teenager level calculation (0-10, 10-20, 20-30, 30-40)
        if score <= 10:
            return "JUNIOR 1"
        elif score <= 20:
            return "JUNIOR 2"
        elif score <= 30:
            return "JUNIOR 3"
        else:
            return "JUNIOR 4"
            
    else:  # Adult levels based on the image provided
        # For adults, we'll map score ranges to the levels in the image
        # Let's create a scale based on percentage
        percentage = (score / max_score) * 100
        
        # Define level ranges based on percentage
        if percentage <= 20:
            return "Starter"
        elif percentage <= 40:
            return "Elementary"
        elif percentage <= 60:
            return "Pre-intermediate"
        elif percentage <= 80:
            return "Intermediate"
        elif percentage <= 90:
            return "Upper Intermediate"
        else:
            return "Advanced"

@app.route('/results')
def show_results():
    if 'result_id' not in session:
        return redirect(url_for('index'))
    
    result = TestResult.query.get(session['result_id'])
    student = Student.query.get(result.student_id)
    
    return render_template('results.html', student=student, result=result)

# Add these routes to your Flask application

@app.route('/admin/student/<int:student_id>/results')
@admin_required
def admin_view_student_results(student_id):
    """View all test results for a specific student"""
    student = Student.query.get_or_404(student_id)
    
    # Get all test results for this student, ordered by most recent first
    results = TestResult.query.filter_by(student_id=student_id).order_by(TestResult.test_date.desc()).all()
    
    return render_template('admin_student_results.html', student=student, results=results)

@app.route('/admin/result/<int:result_id>')
@admin_required
def admin_view_result_details(result_id):
    """View detailed information about a specific test result"""
    result = TestResult.query.get_or_404(result_id)
    student = Student.query.get(result.student_id)
    
    # Determine test type based on student category
    if student.category == 'adult':
        test_type = f'adult_{student.test_type}'
    else:
        test_type = student.category
    
    # Load questions
    questions = load_test_questions(test_type)
    
    # Parse answers from JSON string
    answers = json.loads(result.answers)
    
    return render_template('admin_result_details.html', student=student, result=result, 
                          questions=questions, answers=answers, test_type=test_type)

@app.route('/admin/result/<int:result_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_result(result_id):
    """Edit a student's test result"""
    result = TestResult.query.get_or_404(result_id)
    student = Student.query.get(result.student_id)
    
    if request.method == 'POST':
        # Get form data
        score = request.form.get('score')
        level_type = request.form.get('level_type')
        
        if level_type == 'predefined':
            level = request.form.get('predefined_level')
        else:  # Custom level
            level = request.form.get('custom_level')
        
        # Update result
        result.score = score
        result.level = level
        
        try:
            db.session.commit()
            flash('Test result updated successfully', 'success')
            return redirect(url_for('admin_view_student_results', student_id=student.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating result: {str(e)}', 'danger')
    
    # Determine test type
    if student.category == 'adult':
        test_type = f'adult_{student.test_type}'
    else:
        test_type = student.category
    
    return render_template('admin_edit_result.html', student=student, result=result, test_type=test_type)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Create database if it doesn't exist
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)