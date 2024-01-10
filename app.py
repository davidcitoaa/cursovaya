import hashlib
from datetime import datetime, timedelta

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
    duration = SelectField(
        'Срок вклада',
        choices=[
            (3, '3 месяца'),
            (4, '4 месяца'),
            (5, '5 месяцев'),
            (6, '6 месяцев'),
            (7, '7 месяцев'),
            (8, '8 месяцев'),
            (9, '9 месяцев'),
            (10, '10 месяцев'),
            (11, '11 месяцев'),
            (12, '12 месяцев'),
            (13, '13 месяцев'),
            (14, '14 месяцев'),
            (15, '15 месяцев'),
            (16, '16 месяцев'),
            (17, '17 месяцев'),
            (18, '18 месяцев'),
            (19, '19 месяцев'),
            (20, '20 месяцев'),
            (21, '21 месяцев'),
            (22, '22 месяцев'),
            (23, '23 месяцев'),
            (24, '24 месяца'),
        ],
        validators=[DataRequired()]
    )
    amount = DecimalFieldHTML5('Amount', validators=[DataRequired()])
    submit = SubmitField('Создать')


class DepositForm1(FlaskForm):
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
    for error in form.errors:
        print(error)

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
    amount = DecimalFieldHTML5('Введите сумму', validators=[DataRequired()])
    submit = SubmitField('Пополнить')


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
    else:
        for error in form.errors:
            print(error)
    user_balance = getClientBalance()

    return render_template('add_funds.html', form=form, current_balance=user_balance)


def getClientBalance():
    client_balance = ClientBalance.get_or_none(client_id=current_user.client_id)
    if client_balance is None:
        client_balance = ClientBalance.create(client_id=current_user, balance=0.0)
        client_balance.save()

    balance_value = client_balance.balance
    return balance_value

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

    # Получаем информацию о депозитах пользователя
    user_deposits = Deposit.select().join(Loan).where(Deposit.client_id == current_user)
    print(user_deposits)

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
                           phone_number=phone,
                           deposits=user_deposits)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/create_deposit', methods=['GET', 'POST'])
@login_required
def create_deposit():
    form = DepositForm()
    user_balance = getClientBalance()
    if form.validate_on_submit():
        amount = float(form.amount.data)

        # Проверка, что сумма депозита меньше баланса пользователя
        if user_balance < amount:
            return render_template('create_deposit.html', form=form, error="Недостаточно средств на балансе", current_balance=user_balance)

        # Вычитаем сумму депозита из баланса пользователя
        user_balance = current_user.balance.get()

        # Получаем значение баланса из объекта
        current_balance = user_balance.balance  # Доступ к реальному значению баланса

        # Обновляем баланс пользователя
        updated_balance = current_balance - amount
        user_balance.balance = updated_balance
        user_balance.save()

        duration = int(form.duration.data)
        # Определение процентной ставки в зависимости от срока
        if duration <= 12:
            interest_rate = 10.0
        else:
            interest_rate = 15.0

        # Определение даты окончания депозита
        end_date = datetime.now() + timedelta(days=duration * 30)

        # Создание займа
        loan = Loan.create(amount=amount, interest_rate=interest_rate)

        # Создание депозита
        deposit = Deposit.create(
            client_id=current_user,
            storage_period=end_date,
            interest_capitalization_frequency='1 месяц',
            loan_id=loan,
        )
        deposit.save()

        return redirect(url_for('dashboard'))
    else:
        for error in form.errors:
            print(error)

        return render_template('create_deposit.html', form=form, current_balance=user_balance)


if __name__ == '__main__':
    db.connect()
    # db.create_tables([Client, ClientBalance], safe=True)
    app.run(debug=True)
