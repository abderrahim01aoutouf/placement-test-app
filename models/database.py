from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    category = db.Column(db.String(20), nullable=False)  # 'adult', 'teenager', 'kids'
    test_type = db.Column(db.String(30))  # 'general' ou 'exam_prep' pour les adultes
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    tests = db.relationship('TestResult', backref='student', lazy=True)

    def __repr__(self):
        return f"<Student {self.full_name} ({self.category})>"

class TestResult(db.Model):
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    test_date = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.Text, nullable=False)  # Stockage JSON des réponses
    score = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String(10), nullable=False)  # Niveau CECRL

    def __repr__(self):
        return f"<TestResult {self.student_id} - {self.level}>"

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")

def create_tables(app):
    with app.app_context():
        db.create_all()
        print("Tables verified/created")