from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TimeField
from wtforms.validators import DataRequired, NumberRange, Optional

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
