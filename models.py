from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    subscription_active = db.Column(db.Boolean, default=False)
    subscription_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class WellnessProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    age = db.Column(db.Integer)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    goals = db.Column(db.String(500))
    dietary_restrictions = db.Column(db.String(500))
    activity_level = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WellnessPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_plan = db.Column(db.Text)
    workout_plan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WorkoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workout_type = db.Column(db.String(50))  # e.g., 'cardio', 'strength', 'flexibility'
    duration = db.Column(db.Integer)  # in minutes
    intensity = db.Column(db.String(20))  # 'low', 'medium', 'high'
    exercises = db.Column(db.Text)  # JSON string of exercises completed
    calories_burned = db.Column(db.Integer)
    notes = db.Column(db.Text)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExerciseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_name = db.Column(db.String(100))
    weight = db.Column(db.Float)  # weight used in kg
    reps = db.Column(db.Integer)  # number of repetitions
    sets = db.Column(db.Integer)  # number of sets
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class MealPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_type = db.Column(db.String(20))  # breakfast, lunch, dinner, snack
    preferred_time = db.Column(db.String(5))  # HH:MM format
    calories_target = db.Column(db.Integer)
    protein_target = db.Column(db.Integer)  # in grams
    carbs_target = db.Column(db.Integer)   # in grams
    fat_target = db.Column(db.Integer)     # in grams
    excluded_ingredients = db.Column(db.Text)  # JSON array of ingredients to avoid
    available_ingredients = db.Column(db.Text)  # JSON array of ingredients in stock
    preferred_cuisine = db.Column(db.String(50))  # e.g., Mediterranean, Asian, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MealPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    meal_plan_data = db.Column(db.Text, nullable=False)  # JSON string of the meal plan
    shopping_list = db.Column(db.Text)  # JSON string of the shopping list
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_meal_plan(self):
        import json
        return json.loads(self.meal_plan_data) if self.meal_plan_data else {}

    def get_shopping_list(self):
        import json
        return json.loads(self.shopping_list) if self.shopping_list else {}

class WellnessTip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tip_content = db.Column(db.Text, nullable=False)
    motivation_quote = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50))  # e.g., 'nutrition', 'fitness', 'mindfulness'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_viewed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<WellnessTip {self.id}>'

class TrialUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    trial_start = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end = db.Column(db.DateTime)
    has_converted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, email, name):
        self.email = email
        self.name = name
        self.trial_start = datetime.utcnow()
        self.trial_end = self.trial_start + timedelta(days=7)

    def is_trial_active(self):
        return datetime.utcnow() <= self.trial_end