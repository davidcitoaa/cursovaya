import csv
import hashlib
import json
import os
import random
import string
from datetime import datetime, timedelta, time, date
from decimal import Decimal
from flask import Flask, render_template, redirect, url_for, request, flash
from peewee import *
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from playhouse.shortcuts import model_to_dict
from wtforms import StringField, PasswordField, DateField
from wtforms.fields.choices import SelectField
from wtforms.validators import DataRequired, NumberRange
from flask_wtf import FlaskForm
from wtforms import DecimalField, SubmitField
from wtforms.validators import DataRequired
from wtforms.fields import DecimalField as DecimalFieldHTML5


class Config:
    DEBUG = True
    SECRET_KEY = 'your_secret_key'
    DATABASE_NAME = 'CreditOrganizationDB'
    DATABASE_USER = 'postgres'
    DATABASE_PASSWORD = '2404'
    DATABASE_HOST = 'localhost'
    DATABASE_PORT = 5432


app = Flask(__name__, static_url_path='/static')
app.config.from_object(Config)  # Используем настройки из config.py

# Конфигурация базы данных
db = PostgresqlDatabase(
    app.config['DATABASE_NAME'],
    user=app.config['DATABASE_USER'],
    password=app.config['DATABASE_PASSWORD'],
    host=app.config['DATABASE_HOST'],
    port=app.config['DATABASE_PORT']
)

# Инициализация Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'
