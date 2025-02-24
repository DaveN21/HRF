from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SelectField, IntegerField, TimeField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional
from app import app, db, login_manager
from models import User, WellnessProfile, WellnessPlan, WorkoutLog, ExerciseProgress, MealPreference, MealPlan, WellnessTip
from utils.ai_helper import generate_wellness_plan
from utils.wellness_tips import generate_wellness_tip
from utils.stripe_helper import create_checkout_session, STRIPE_PUBLIC_KEY
from utils.meal_planner import generate_meal_plan, generate_shopping_list, generate_recipes_from_ingredients
import json
import logging
from datetime import datetime, date

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.template_filter('from_json')
def from_json_filter(value):
    try:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        return json.loads(value)
    except Exception as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return {}

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=50, message="Username must be between 3 and 50 characters")
    ])
    email = EmailField('Email', validators=[
        DataRequired(), 
        Email(message="Please enter a valid email address")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    return render_template('index.html', stripe_public_key=STRIPE_PUBLIC_KEY)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Check if username or email already exists
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('register.html', form=form)

            if User.query.filter_by(email=form.email.data).first():
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('register.html', form=form)

            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            # Log the user in
            login_user(user)
            flash('Registration successful! Welcome to AI Wellness Planner.', 'success')
            return redirect(url_for('questionnaire'))

        except Exception as e:
            logging.error(f"Registration error: {str(e)}")
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/questionnaire', methods=['GET', 'POST'])
@login_required
def questionnaire():
    if request.method == 'POST':
        profile = WellnessProfile(
            user_id=current_user.id,
            age=request.form.get('age'),
            height=float(request.form.get('height')),
            weight=float(request.form.get('weight')),
            goals=request.form.get('goals'),
            dietary_restrictions=request.form.get('dietary_restrictions'),
            activity_level=request.form.get('activity_level')
        )
        db.session.add(profile)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('questionnaire.html')

@app.route('/dashboard')
@login_required
def dashboard():
    profile = WellnessProfile.query.filter_by(user_id=current_user.id).first()
    plan = WellnessPlan.query.filter_by(user_id=current_user.id).order_by(WellnessPlan.created_at.desc()).first()
    return render_template('dashboard.html', profile=profile, plan=plan, stripe_public_key=STRIPE_PUBLIC_KEY)

@app.route('/generate-plan')
@login_required
def generate_plan():
    try:
        if not current_user.subscription_active:
            flash('Please subscribe to generate a wellness plan', 'warning')
            return redirect(url_for('dashboard'))

        profile = WellnessProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            flash('Please complete your wellness profile first', 'warning')
            return redirect(url_for('questionnaire'))

        plan_data = generate_wellness_plan(profile)
        if not plan_data:
            flash('Error generating wellness plan. Please try again.', 'error')
            return redirect(url_for('dashboard'))

        plan = WellnessPlan(
            user_id=current_user.id,
            meal_plan=json.dumps(plan_data.get('meal_plan', {})),
            workout_plan=json.dumps(plan_data.get('workout_plan', {}))
        )
        db.session.add(plan)
        db.session.commit()

        flash('Your wellness plan has been generated successfully!', 'success')
        return redirect(url_for('plan'))

    except Exception as e:
        logger.error(f"Error in generate_plan: {e}")
        flash('Sorry, there was an error generating your wellness plan. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/plan')
@login_required
def plan():
    plan = WellnessPlan.query.filter_by(user_id=current_user.id).order_by(WellnessPlan.created_at.desc()).first()
    if not plan:
        flash('No wellness plan found. Please generate one.', 'info')
        return redirect(url_for('dashboard'))

    # Parse JSON data before passing to template
    try:
        if isinstance(plan.meal_plan, str):
            plan.meal_plan = json.loads(plan.meal_plan)
        if isinstance(plan.workout_plan, str):
            plan.workout_plan = json.loads(plan.workout_plan)
    except Exception as e:
        logger.error(f"Error parsing plan data: {str(e)}")
        plan.meal_plan = {}
        plan.workout_plan = {}

    return render_template('plan.html', plan=plan)

@app.route('/create-checkout-session')
@login_required
def checkout():
    try:
        # Create Stripe checkout session
        result = create_checkout_session(current_user.id)

        if not result:
            logger.error("Failed to create checkout session")
            return jsonify({'error': 'Failed to create checkout session'}), 500

        return jsonify(result)

    except Exception as e:
        logger.error(f"Stripe checkout error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/workout/log', methods=['GET', 'POST'])
@login_required
def log_workout():
    if request.method == 'POST':
        try:
            exercises = request.form.getlist('exercises[]')
            workout_log = WorkoutLog(
                user_id=current_user.id,
                workout_type=request.form.get('workout_type'),
                duration=int(request.form.get('duration')),
                intensity=request.form.get('intensity'),
                exercises=json.dumps(exercises),
                calories_burned=int(request.form.get('calories_burned')),
                notes=request.form.get('notes')
            )
            db.session.add(workout_log)

            # Log individual exercise progress if weights/reps provided
            for exercise in exercises:
                if request.form.get(f'weight_{exercise}') and request.form.get(f'reps_{exercise}'):
                    progress = ExerciseProgress(
                        user_id=current_user.id,
                        exercise_name=exercise,
                        weight=float(request.form.get(f'weight_{exercise}')),
                        reps=int(request.form.get(f'reps_{exercise}')),
                        sets=int(request.form.get(f'sets_{exercise}', 1))
                    )
                    db.session.add(progress)

            db.session.commit()
            flash('Workout logged successfully!', 'success')
            return redirect(url_for('workout_progress'))
        except Exception as e:
            db.session.rollback()
            flash('Error logging workout. Please try again.', 'error')
            return redirect(url_for('log_workout'))

    return render_template('workout/log.html')

@app.route('/workout/progress')
@login_required
def workout_progress():
    # Get recent workouts
    workouts = WorkoutLog.query.filter_by(user_id=current_user.id)\
        .order_by(WorkoutLog.completed_at.desc())\
        .limit(10).all()

    # Get exercise progress data for charts
    progress_data = {}
    exercises = ExerciseProgress.query.filter_by(user_id=current_user.id)\
        .order_by(ExerciseProgress.recorded_at.desc())\
        .limit(50).all()

    for exercise in exercises:
        if exercise.exercise_name not in progress_data:
            progress_data[exercise.exercise_name] = {
                'dates': [],
                'weights': [],
                'reps': []
            }
        progress_data[exercise.exercise_name]['dates'].append(
            exercise.recorded_at.strftime('%Y-%m-%d')
        )
        progress_data[exercise.exercise_name]['weights'].append(exercise.weight)
        progress_data[exercise.exercise_name]['reps'].append(exercise.reps)

    return render_template(
        'workout/progress.html',
        workouts=workouts,
        progress_data=progress_data
    )

class MealPreferenceForm(FlaskForm):
    meal_type = SelectField('Meal Type', choices=[
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack')
    ], validators=[DataRequired()])
    preferred_time = TimeField('Preferred Time', validators=[DataRequired()])
    calories_target = IntegerField('Target Calories', validators=[NumberRange(min=0, max=2000)])
    protein_target = IntegerField('Target Protein (g)', validators=[NumberRange(min=0, max=200)])
    carbs_target = IntegerField('Target Carbs (g)', validators=[NumberRange(min=0, max=300)])
    fat_target = IntegerField('Target Fat (g)', validators=[NumberRange(min=0, max=100)])
    excluded_ingredients = StringField('Excluded Ingredients (comma-separated)', validators=[Optional()])
    available_ingredients = StringField('Available Ingredients (comma-separated)', validators=[Optional()])
    preferred_cuisine = SelectField('Preferred Cuisine', choices=[
        ('any', 'Any'),
        ('mediterranean', 'Mediterranean'),
        ('asian', 'Asian'),
        ('mexican', 'Mexican'),
        ('indian', 'Indian'),
        ('italian', 'Italian'),
        ('american', 'American'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan')
    ])

@app.route('/meal-preferences', methods=['GET', 'POST'])
@login_required
def meal_preferences():
    form = MealPreferenceForm()
    if form.validate_on_submit():
        try:
            preference = MealPreference.query.filter_by(
                user_id=current_user.id,
                meal_type=form.meal_type.data
            ).first()

            if not preference:
                preference = MealPreference(user_id=current_user.id)

            # Update preference data
            preference.meal_type = form.meal_type.data
            preference.preferred_time = form.preferred_time.data.strftime('%H:%M') if form.preferred_time.data else None
            preference.calories_target = form.calories_target.data
            preference.protein_target = form.protein_target.data
            preference.carbs_target = form.carbs_target.data
            preference.fat_target = form.fat_target.data

            # Handle empty form fields
            excluded = form.excluded_ingredients.data or ''
            available = form.available_ingredients.data or ''

            # Clean and format ingredients lists
            excluded_list = [i.strip() for i in excluded.split(',') if i.strip()]
            available_list = [i.strip() for i in available.split(',') if i.strip()]

            preference.excluded_ingredients = json.dumps(excluded_list)
            preference.available_ingredients = json.dumps(available_list)
            preference.preferred_cuisine = form.preferred_cuisine.data

            if not preference.id:
                db.session.add(preference)
            db.session.commit()

            flash('Meal preferences updated successfully!', 'success')
            return redirect(url_for('meal_preferences'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating meal preferences: {str(e)}")
            flash('Error updating meal preferences. Please try again.', 'error')

    # Get existing preferences for display
    preferences = MealPreference.query.filter_by(user_id=current_user.id).all()

    return render_template('meal_preferences.html', form=form, preferences=preferences)

@app.route('/meal-plan/generate', methods=['POST'])
@login_required
def generate_new_meal_plan():
    try:
        # Get user's meal preferences
        preferences = MealPreference.query.filter_by(user_id=current_user.id).first()
        if not preferences:
            flash('Please set your meal preferences first', 'warning')
            return redirect(url_for('meal_preferences'))

        # Generate meal plan
        meal_plan_data = generate_meal_plan(preferences)
        shopping_list_data = generate_shopping_list(meal_plan_data)

        # Get date range from the meal plan
        start_date = datetime.strptime(meal_plan_data['meal_plan'][0]['date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(meal_plan_data['meal_plan'][-1]['date'], '%Y-%m-%d').date()

        # Create new meal plan
        meal_plan = MealPlan(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            meal_plan_data=json.dumps(meal_plan_data),
            shopping_list=json.dumps(shopping_list_data)
        )

        db.session.add(meal_plan)
        db.session.commit()

        flash('Your personalized meal plan has been generated!', 'success')
        return redirect(url_for('view_meal_plan', plan_id=meal_plan.id))

    except Exception as e:
        flash(f'Error generating meal plan: {str(e)}', 'error')
        return redirect(url_for('meal_preferences'))

@app.route('/meal-plan/<int:plan_id>')
@login_required
def view_meal_plan(plan_id):
    plan = MealPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    return render_template('meal_plan/view.html', plan=plan)

@app.route('/meal-plans')
@login_required
def list_meal_plans():
    plans = MealPlan.query.filter_by(user_id=current_user.id)\
        .order_by(MealPlan.created_at.desc()).all()
    return render_template('meal_plan/list.html', plans=plans)

@app.route('/ingredient-recipes', methods=['GET', 'POST'])
@login_required
def ingredient_recipes():
    if request.method == 'POST':
        ingredients = request.form.get('ingredients', '').strip()
        if not ingredients:
            flash('Please enter at least one ingredient', 'warning')
            return redirect(url_for('ingredient_recipes'))

        try:
            # Get user's wellness profile
            profile = WellnessProfile.query.filter_by(user_id=current_user.id).first()

            # Get recipes based on available ingredients and wellness profile
            ingredients_list = [i.strip() for i in ingredients.split(',') if i.strip()]
            recipes = generate_recipes_from_ingredients(ingredients_list, profile)

            return render_template('meal_plan/ingredient_recipes.html', recipes=recipes)

        except Exception as e:
            logger.error(f"Error generating recipes: {str(e)}")
            flash('Error generating recipes. Please try again.', 'error')
            return render_template('meal_plan/ingredient_recipes.html', recipes=None)

    # GET request
    return render_template('meal_plan/ingredient_recipes.html', recipes=None)

@app.route('/wellness-tip')
@login_required
def wellness_tip():
    # Check if user has a tip for today
    today = datetime.now().date()
    tip = WellnessTip.query.filter(
        WellnessTip.user_id == current_user.id,
        db.func.date(WellnessTip.created_at) == today
    ).first()

    if not tip:
        # Generate new tip if none exists for today
        profile = WellnessProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            flash('Please complete your wellness profile first', 'warning')
            return redirect(url_for('questionnaire'))

        try:
            tip_data = generate_wellness_tip(profile)
            tip = WellnessTip(
                user_id=current_user.id,
                tip_content=tip_data['tip'],
                motivation_quote=tip_data['quote'],
                category=tip_data['category']
            )
            db.session.add(tip)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error generating wellness tip: {str(e)}")
            flash('Error generating wellness tip. Please try again later.', 'error')
            return redirect(url_for('dashboard'))

    # Mark tip as viewed
    if not tip.is_viewed:
        tip.is_viewed = True
        db.session.commit()

    return render_template('wellness_tip.html', tip=tip)

@app.route('/trial/signup', methods=['GET', 'POST'])
def trial_signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('trial_signup.html')