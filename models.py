# models.py
import hashlib

from flask_login import UserMixin
from flask_wtf import FlaskForm
from peewee import Model, AutoField, CharField, DecimalField, ForeignKeyField, DateField
from wtforms.fields.simple import StringField, PasswordField
from wtforms.validators import DataRequired

from app import db, BaseModel



def get_hashed_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Определение моделей Client и ClientBalance
class Client(BaseModel, UserMixin):
    client_id = AutoField(primary_key=True)
    full_name = CharField(max_length=255)
    birth_date = CharField(max_length=255)
    passport_data = CharField(max_length=255)
    password = CharField(max_length=255)
    email = CharField(max_length=255, null=True)
    phone = CharField(max_length=20)

    def check_password(self, password):
        return get_hashed_password(password) == self.password


class ClientBalance(BaseModel):
    balance_id = AutoField(primary_key=True)  # Добавлен столбец balance_id
    client = ForeignKeyField(Client, backref='balance')
    balance = DecimalField(max_digits=10, decimal_places=2, default=0.0)


# Определение форм для входа и регистрации
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


# Определение формы для регистрации
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    birth_date = DateField('Birth Date', validators=[DataRequired()], format='%Y-%m-%d')
    passport_data = StringField('Passport Data', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])