# для того, чтобы код работал, нужно, чтобы была такая таблица:
# CREATE TABLE IF NOT EXISTS public.deposit
# (
#     deposit_id integer NOT NULL DEFAULT nextval('deposit_deposit_id_seq'::regclass),
#     client_id integer NOT NULL,
#     storage_period date NOT NULL,
#     loan_id integer,
#     interest_capitalization_frequency character varying(255) COLLATE pg_catalog."default" NOT NULL,
#     CONSTRAINT deposit_pkey PRIMARY KEY (deposit_id),
#     CONSTRAINT deposit_client_id_fkey FOREIGN KEY (client_id)
#         REFERENCES public.client (client_id) MATCH SIMPLE
#         ON UPDATE NO ACTION
#         ON DELETE NO ACTION,
#     CONSTRAINT deposit_loan_id_fkey FOREIGN KEY (loan_id)
#         REFERENCES public.loan (loan_id) MATCH SIMPLE
#         ON UPDATE NO ACTION
#         ON DELETE NO ACTION
# )

import hashlib
from flask import Flask, render_template, redirect, url_for
from peewee import *
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import SubmitField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from wtforms import DecimalField, SubmitField
from wtforms.validators import DataRequired
from wtforms.fields import DecimalField as DecimalFieldHTML5
from config import Config  # Импортируем настройки

app = Flask(__name__)
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


# Определение базовой модели Peewee
class BaseModel(Model):
    class Meta:
        database = db


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
    client_id = ForeignKeyField(Client, backref='balance')
    balance = FloatField()

    class Meta:
        database = db
        db_table = 'clientbalance'  # Specify table name explicitly


class Loan(Model):
    loan_id = AutoField(primary_key=True)
    amount = FloatField()
    interest_rate = FloatField()

    class Meta:
        database = db
        db_table = 'loan'


class Deposit(Model):
    deposit_id = AutoField(primary_key=True)
    client_id = ForeignKeyField(Client, backref='deposit')
    storage_period = CharField(max_length=255)
    interest_capitalization_frequency = CharField(max_length=255)
    loan_id = ForeignKeyField(Loan, null=True)

    class Meta:
        database = db
        db_table = 'deposit'


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


class DepositForm(FlaskForm):
    storage_period = DateField(validators=[DataRequired()])
    interest_capitalization_frequency = SelectField(
        'Период капитализации процентов',
        choices=[
            ('1 месяц', '1 месяц'),
            ('3 месяца', '3 месяца'),
            ('6 месяцев', '6 месяцев'),
            ('1 год', '1 год'),
            ('3 года', '3 года'),
        ]
    )
    amount = DecimalFieldHTML5('Amount', validators=[DataRequired()])
    interest_rate = DecimalFieldHTML5('interest_rate', validators=[DataRequired()])


@login_manager.user_loader
def load_user(user_id):
    return Client.get_by_id(user_id)


# Маршруты Flask
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = Client.get_or_none(Client.email == form.username.data)
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))

    return render_template('login.html', form=form)


def get_hashed_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = Client.create(
            full_name=form.username.data,
            birth_date=form.birth_date.data,
            passport_data=form.password.data,
            email=form.email.data,
            phone=form.phone.data,
            password=get_hashed_password(form.password.data)
        )
        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('register.html', form=form)


# Определение формы для пополнения баланса
class AddFundsForm(FlaskForm):
    amount = DecimalFieldHTML5('Amount', validators=[DataRequired()])
    submit = SubmitField('Add Funds')


# Маршрут для пополнения баланса
@app.route('/add_funds', methods=['GET', 'POST'])
@login_required
def add_funds():
    form = AddFundsForm()
    if form.validate_on_submit():
        # Получаем сумму пополнения из формы в виде числа
        amount = float(form.amount.data)

        # Получаем объект баланса пользователя
        user_balance_query = current_user.balance

        # Если у пользователя нет баланса, создаем новую запись
        if user_balance_query.exists() is False:
            user_balance = ClientBalance.create(client=current_user, balance=amount)
        else:
            # Получаем первый объект баланса из запроса
            user_balance = user_balance_query.get()

            # Получаем значение баланса из объекта
            current_balance = user_balance.balance  # Доступ к реальному значению баланса

            # Обновляем баланс пользователя
            updated_balance = current_balance + amount
            user_balance.balance = updated_balance
            user_balance.save()

        return redirect(url_for('dashboard'))

    return render_template('add_funds.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    # Получаем баланс текущего пользователя или создаем новую запись с балансом 0.0
    client_balance = ClientBalance.get_or_none(client_id=current_user.client_id)
    if client_balance is None:
        client_balance = ClientBalance.create(client_id=current_user, balance=0.0)
        client_balance.save()

    balance_value = client_balance.balance

    # Получаем логин клиента
    name = user.full_name

    # Получаем пароль клиента
    date_of_birth = user.birth_date

    # Получаем дату рождения клиента

    email = user.email
    phone = user.phone

    # Отображаем данные пользователя
    return render_template('dashboard.html',
                           user=user,
                           current_balance=balance_value,
                           name=name,
                           date_of_birth=date_of_birth,
                           email=email,
                           phone_number=phone)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))



@app.route('/create_deposit', methods=['POST'])
@login_required
def create_deposit():
    form = DepositForm()

    if form.validate_on_submit():
        amount = float(form.amount.data)
        interest_rate = float(form.interest_rate.data)
        loan = Loan.create(
            amount=amount,  # Получаем значение поля формы
            interest_rate=interest_rate
        )
        loan_id = loan
        print(loan_id)

        client_id = current_user
        storage_period = form.storage_period.data
        interest_capitalization_frequency = form.interest_capitalization_frequency.data

        print(client_id, storage_period, interest_capitalization_frequency)
        deposit = Deposit.create(
            client_id=client_id,
            storage_period=storage_period,
            interest_capitalization_frequency=interest_capitalization_frequency,
            loan_id=loan_id,
        )
        deposit.save()

        return redirect(url_for('dashboard'))
    else:
        # Данные некорректны, выводим ошибки
        for error in form.errors:
            print(error)

        return render_template('create_deposit.html', form=form)

    # return render_template('create_deposit.html', form=form)


if __name__ == '__main__':
    db.connect()
    # db.create_tables([Client, ClientBalance], safe=True)
    app.run(debug=True)
