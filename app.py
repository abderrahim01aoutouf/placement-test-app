from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from models.database import db, init_db, Student, TestResult
from datetime import datetime
import json
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os
from functools import wraps
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import flash
import csv

os.environ.pop('ADMIN_USERNAME', None)
os.environ.pop('ADMIN_PASSWORD_HASH', None)

# Recharger depuis fichier
load_dotenv('.env', override=True)





# Configuration de l'application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_tests.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialisation de la base de données
init_db(app)
csrf = CSRFProtect(app)


# Chemins des fichiers de test
TEST_PATHS = {
    'adult_general': 'static/data/adult_general.json',
    'adult_exam_prep': 'static/data/adult_exam_prep.json',
    'teenager': 'static/data/teenager.json',
    'kids': 'static/data/kids.json'
}
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '').strip()
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', '').strip()

if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    raise RuntimeError("Configuration admin manquante dans .env")



app.config['WTF_CSRF_TIME_LIMIT'] = 3600

def load_test_questions(test_type):
    """Charge les questions depuis le fichier JSON approprié"""
    try:
        file_path = TEST_PATHS.get(test_type)
        if not file_path:
            abort(400, description="Type de test invalide")
            
        with open(file_path, 'r') as f:
            return json.load(f)
            
    except FileNotFoundError:
        abort(404, description="Fichier de test introuvable")
    except json.JSONDecodeError:
        abort(500, description="Erreur de format des questions")
    except Exception as e:
        app.logger.error(f"Erreur critique: {str(e)}")
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

# Route de connexion admin
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Veuillez remplir tous les champs', 'danger')
            return redirect(url_for('admin_login'))
        
        try:
            if (username == ADMIN_USERNAME and 
                check_password_hash(ADMIN_PASSWORD_HASH, password)):
                session['admin_logged_in'] = True
                session.permanent = False  # Sécurité supplémentaire
                return redirect(url_for('admin_dashboard'))
        except Exception as e:
            app.logger.error(f"Erreur d'authentification : {str(e)}")
        
        flash('Identifiants incorrects', 'danger')
    
    return render_template('admin_login.html')

# Route dashboard admin
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Récupération des étudiants avec leurs résultats
    students_with_results = []
    
    students = Student.query.all()
    for student in students:
        # Récupérer le dernier résultat de test
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
            'test_date': test_result.test_date.strftime('%Y-%m-%d %H:%M:%S') if test_result else None
        }
        
        students_with_results.append(student_data)
    
    return render_template('admin_dashboard.html', students=students_with_results)

@app.route('/admin/export_csv')
@admin_required
def export_csv():
    file_path = os.path.join(app.static_folder, 'data/students_export.csv')
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Nom', 'Âge', 'Email', 'Téléphone', 'Catégorie', 'Type Test', 'Score', 'Niveau', 'Date Inscription', 'Date Test'])

        students = Student.query.all()
        for student in students:
            result = TestResult.query.filter_by(student_id=student.id).order_by(TestResult.test_date.desc()).first()
            writer.writerow([
                student.id, student.full_name, student.age, student.email, student.phone,
                student.category, student.test_type, result.score if result else '',
                result.level if result else '', student.registration_date, result.test_date if result else ''
            ])
    
    flash('Export CSV réalisé avec succès ✅', 'success')
    return redirect(url_for('admin_dashboard'))

    
# Route pour exporter les données en JSON
@app.route('/admin/export')
@admin_required
def admin_export():
    # Récupération des étudiants avec leurs résultats
    students_with_results = []
    
    students = Student.query.all()
    for student in students:
        # Récupérer tous les résultats de test pour cet étudiant
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
    
    # Création du répertoire static/data s'il n'existe pas
    data_dir = os.path.join(app.static_folder, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Enregistrement des données dans un fichier JSON
    file_path = os.path.join(data_dir, 'students_export.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(students_with_results, f, ensure_ascii=False, indent=4)
    
    flash('Export JSON réalisé avec succès', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/clean_database', methods=['POST'])
@admin_required
def clean_database():
    """Supprime toutes les données: résultats et étudiants"""
    try:
        # Supprimer d'abord tous les résultats de tests (pour respecter les contraintes FK)
        TestResult.query.delete()
        
        # Supprimer ensuite tous les étudiants
        Student.query.delete()
        
        db.session.commit()
        flash("Toutes les données ont été supprimées avec succès", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors du nettoyage de la base de données: {str(e)}", 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clean_results', methods=['POST'])
@admin_required
def clean_results():
    """Supprime uniquement les résultats de tests, garde les étudiants"""
    try:
        # Supprimer tous les résultats de tests
        TestResult.query.delete()
        db.session.commit()
        flash("Tous les résultats de tests ont été supprimés avec succès", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression des résultats: {str(e)}", 'danger')
    
    return redirect(url_for('admin_dashboard'))

# Route pour se déconnecter
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('admin_login'))





# Routes de l'application
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        age = int(request.form['age'])
        email = request.form['email']
        phone = request.form['phone']
        
        # Détermination de la catégorie
        if age < 12:
            category = 'kids'
        elif age < 18:
            category = 'teenager'
        else:
            category = 'adult'
        
        # Création du student
        new_student = Student(
            full_name=full_name,
            age=age,
            email=email,
            phone=phone,
            category=category
        )
        
        try:
            db.session.add(new_student)
            db.session.commit()
            session['student_id'] = new_student.id
            return redirect(url_for('test_selection'))
        except Exception as e:
            db.session.rollback()
            flash("Erreur d'inscription : Cet email est déjà utilisé" if "UNIQUE constraint failed" in str(e) 
                  else "Erreur lors de l'inscription")
            return redirect(url_for('register'))
    
    return render_template('registration.html')

@app.route('/test_selection', methods=['GET', 'POST'])
def test_selection():
    if 'student_id' not in session:
        return redirect(url_for('register'))
    
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
    
    # Détermination du type de test
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
        
        # Calcul du niveau
        max_score = len(questions)
        level = calculate_level(score, max_score, test_type)
        
        # Enregistrement du résultat
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
            abort(500, description="Erreur d'enregistrement des résultats")
    
    return render_template('test.html', student=student, questions=questions)

def calculate_level(score, max_score, test_type):
    """Calcule le niveau CECRL selon le score"""
    percentage = (score / max_score) * 100
    level_ranges = {
        'adult_exam_prep': {'C2': 95, 'C1': 85, 'B2': 70, 'B1': 55, 'A2': 40, 'A1': 0},
        'default': {'C2': 90, 'C1': 75, 'B2': 60, 'B1': 45, 'A2': 30, 'A1': 0}
    }
    
    ranges = level_ranges.get(test_type, level_ranges['default'])
    for level, threshold in reversed(ranges.items()):
        if percentage >= threshold:
            return level
    return 'A1'

@app.route('/results')
def show_results():
    if 'result_id' not in session:
        return redirect(url_for('index'))
    
    result = TestResult.query.get(session['result_id'])
    student = Student.query.get(result.student_id)
    
    return render_template('results.html', student=student, result=result)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Créer la base de données si elle n'existe pas
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)