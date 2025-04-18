# add_columns.py
from app import app
from models.database import db
from sqlalchemy import text

with app.app_context():
    # Add access_code column
    db.session.execute(text("ALTER TABLE students ADD COLUMN access_code VARCHAR(10) UNIQUE NOT NULL DEFAULT '';"))
    # Add is_approved column
    db.session.execute(text("ALTER TABLE students ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT 0;"))
    db.session.commit()
    print("Columns added successfully!")

with app.app_context():
    # Drop all existing tables
    db.drop_all()
    # Create new tables with the updated schema
    db.create_all()
    print("Database reset successfully!")