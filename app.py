import hashlib
import random
import string
from datetime import datetime, timedelta

from flask import Flask, render_template, redirect, url_for, request
from flask_socketio import SocketIO
from peewee import *
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from playhouse.postgres_ext import DateTimeTZField
from wtforms import StringField, PasswordField, DateField
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import SubmitField
from wtforms.validators import DataRequired, NumberRange
from flask_wtf import FlaskForm
from wtforms import DecimalField, SubmitField
from wtforms.validators import DataRequired
from wtforms.fields import DecimalField as DecimalFieldHTML5
from config import Config  # Импортируем настройки

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
socketio = SocketIO(app)


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

    def reduce_balance(self, amount):
        current_balance = self.balance
        # Обновляем баланс пользователя
        updated_balance = current_balance - amount
        self.balance = updated_balance
        self.save()

    def increase_balance(self, amount):
        current_balance = self.balance
        # Обновляем баланс пользователя
        updated_balance = current_balance + amount
        self.balance = updated_balance
        self.save()

    class Meta:
        database = db
        db_table = 'client_balance'  # Specify table name explicitly


class Loan(Model):
    loan_id = AutoField(primary_key=True)
    amount = FloatField()
    interest_rate = FloatField()
    type = CharField(max_length=255)

    class Meta:
        database = db
        db_table = 'loan'


class Deposit(BaseModel):
    deposit_id = AutoField(primary_key=True)
    client_id = ForeignKeyField(Client, backref='deposits')
    closing_date = CharField(max_length=255)
    loan_id = ForeignKeyField(Loan, backref='deposit')
    date_opened = CharField(max_length=255)

    def formatted_date_opened(self):
        return datetime.strptime(self.date_opened, '%Y-%m-%d').strftime('%d.%m.%Y')

    def formatted_closing_date(self):
        return datetime.strptime(self.closing_date, '%Y-%m-%d').strftime('%d.%m.%Y')

    def calculate_interest(self):
        # Проверка наличия даты закрытия и даты открытия
        if self.closing_date and self.date_opened:
            # Преобразование строковых дат в объекты datetime
            closing_date = datetime.strptime(self.closing_date, "%Y-%m-%d")
            date_opened = datetime.strptime(self.date_opened, "%Y-%m-%d")

            # Разница в днях между датой закрытия и датой открытия
            duration_days = (closing_date - date_opened).days
            # Расчет процентов в рублях
            interest_in_rubles = self.loan_id.amount * (self.loan_id.interest_rate / 100) * (duration_days / 30 / 12)
            return round(interest_in_rubles, 2)
        else:
            return 0.0

    def calculate_total_amount(self):
        return self.calculate_interest() + self.loan_id.amount

    class Meta:
        database = db
        db_table = 'deposit'


class Credit(BaseModel):
    credit_id = AutoField(primary_key=True)
    client_id = ForeignKeyField(Client, backref='credits')
    closing_date = CharField()
    next_payment_date = CharField()
    next_payment_amount = FloatField()
    loan_id = ForeignKeyField(Loan, backref='credits')
    date_opened = CharField()

    def formatted_closing_date(self):
        return datetime.strptime(self.closing_date, '%Y-%m-%d').strftime('%d.%m.%Y')

    def formatted_next_payment_date(self):
        return datetime.strptime(self.next_payment_date, '%Y-%m-%d').strftime('%d.%m.%Y')

    class Meta:
        table_name = 'credit'


# Модель TransactionLog
class TransactionLog(BaseModel):
    operation_id = AutoField(primary_key=True)
    client_id = ForeignKeyField(Client, backref='transaction_logs')
    operation_datetime = CharField(max_length=255)
    operation_type = CharField(max_length=255)
    operation_amount = FloatField()
    recipients_name = CharField(max_length=255)

    def formatted_operation_datetime(self):
        return datetime.strptime(self.operation_datetime, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')

    class Meta:
        table_name = 'transaction_log'


# Модель Notification
class Notification(BaseModel):
    notification_id = AutoField(primary_key=True)
    client_id = ForeignKeyField(Client, backref='notifications')
    notification_type = CharField(max_length=255)
    content_data = CharField(max_length=255)
    send_datetime = CharField(max_length=255)

    class Meta:
        table_name = 'notification'


class Card(BaseModel):
    card_id = AutoField(primary_key=True)
    client_id = ForeignKeyField(Client, backref='cards')
    card_number = CharField(max_length=255, unique=True)
    expiry_date = CharField(max_length=255)

    def formatted_expiry_date(self):
        return datetime.strptime(self.expiry_date, '%Y-%m-%d').strftime('%d.%m.%Y')

    class Meta:
        table_name = 'card'


# Функция для создания уведомления
def create_notification(client, notification_type, content_data):
    notification = Notification.create(client_id=client, notification_type=notification_type, content_data=content_data,
                                       send_datetime=datetime.now().strftime("%c"))
    notification.save()


# Определение форм для входа и регистрации
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class CardForm(FlaskForm):
    submit = SubmitField('Создать')


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
            (21, '21 месяц'),
            (22, '22 месяца'),
            (23, '23 месяца'),
            (24, '24 месяца'),
        ],
        validators=[DataRequired()]
    )
    amount = DecimalFieldHTML5('Amount', validators=[DataRequired(), NumberRange(min=100)])
    submit = SubmitField('Создать')


def get_loan_period(duration):
    return f'{duration} {"год" if duration < 5 else "лет"}{"а" if 1 < duration < 5 else ""}'


# Форма для запроса на кредит
class LoanRequestForm(FlaskForm):
    amount = DecimalFieldHTML5('Желаемая сумма кредита', validators=[DataRequired()])
    duration = SelectField('Срок кредита (в годах)',
                           choices=[(i, get_loan_period(i)) for i in
                                    range(1, 11)], validators=[DataRequired()])
    submit = SubmitField('Оформить')


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
        print("1")
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

    return render_template('register.html', form=form, errors=form.errors)


# Определение формы для пополнения баланса
class AddFundsForm(FlaskForm):
    amount = DecimalFieldHTML5('Введите сумму', validators=[DataRequired()])
    submit = SubmitField('Пополнить')


class TransferFundsForm(FlaskForm):
    transfer_method = SelectField('Перевести', choices=[('phone', 'по номеру телефона'), ('card', 'по номеру карты')],
                                  validators=[DataRequired()])
    recipient_identifier = StringField('Номер', validators=[DataRequired()])
    amount = DecimalField('Сумма', validators=[DataRequired()])


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

        transaction = TransactionLog.create(client_id=current_user,
                                            operation_datetime=str(datetime.now().strftime("%c")),
                                            operation_type='replenishment',
                                            operation_amount=amount)
        transaction.save()

        return redirect(url_for('dashboard'))
    else:
        for error in form.errors:
            print(error)
    user_balance = getClientBalance(current_user)

    return render_template('add_funds.html', form=form, current_balance=user_balance)


def getClientBalance(user):
    client_balance = ClientBalance.get_or_none(client_id=user.client_id)
    if client_balance is None:
        client_balance = ClientBalance.create(client_id=user, balance=0.0)
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

    # Получаем логин клиента
    name = user.full_name

    # Получаем пароль клиента
    date_of_birth = user.birth_date

    # Получаем дату рождения клиента

    email = user.email
    phone = user.phone

    # Получаем информацию о кредитах пользователя
    user_credits = Credit.select().join(Loan).where(Credit.client_id == current_user)

    # Получаем историю операций пользователя
    transaction_logs = TransactionLog.select().where(TransactionLog.client_id == current_user)

    cards = Card.select().where(Card.client_id == current_user)

    # Отображаем данные пользователя
    return render_template('dashboard.html',
                           user=user,
                           current_balance=balance_value,
                           name=name,
                           date_of_birth=date_of_birth,
                           email=email,
                           phone_number=phone,
                           deposits=user_deposits,
                           credits=user_credits,  # Добавлено для отображения информации о кредитах
                           calculate_interest=Deposit.calculate_interest,
                           transaction_logs=transaction_logs,
                           cards=cards)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/create_deposit', methods=['GET', 'POST'])
@login_required
def create_deposit():
    form = DepositForm()
    user_balance = getClientBalance(current_user)
    if form.validate_on_submit():
        amount = float(form.amount.data)

        if amount < 100:
            return render_template('create_deposit.html', form=form, error="Недостаточно средств на балансе",
                                   current_balance=user_balance)

        # Проверка, что сумма депозита меньше баланса пользователя
        if user_balance < amount:
            return render_template('create_deposit.html', form=form, error="Недостаточно средств на балансе",
                                   current_balance=user_balance)

        # Вычитаем сумму депозита из баланса пользователя
        user_balance = current_user.balance.get()
        current_balance = user_balance.balance  # Доступ к реальному значению баланса
        updated_balance = current_balance - amount
        user_balance.balance = updated_balance
        user_balance.save()

        transaction = TransactionLog.create(client_id=current_user,
                                            operation_datetime=str(datetime.now().strftime("%c")),
                                            operation_type='deposit',
                                            operation_amount=amount)
        transaction.save()
        print(transaction.operation_datetime)

        duration = int(form.duration.data)
        # Определение процентной ставки в зависимости от срока
        if duration <= 12:
            interest_rate = 10.0
        else:
            interest_rate = 15.0

        # Определение даты окончания депозита
        end_date = datetime.now() + timedelta(days=duration * 30)

        # Создание займа
        loan = Loan.create(amount=amount, interest_rate=interest_rate, type='Вклад')

        # Создание депозита
        deposit = Deposit.create(
            client_id=current_user,
            closing_date=end_date,
            date_opened=datetime.now(),
            loan_id=loan,
        )
        deposit.save()

        return redirect(url_for('dashboard'))
    else:
        for error in form.errors:
            print(error)

        return render_template('create_deposit.html', form=form, current_balance=user_balance)


# Ваш роут для страницы запроса на кредит
# Обновленный роут для страницы запроса на кредит
@app.route('/request_loan', methods=['GET', 'POST'])
@login_required
def request_loan():
    form = LoanRequestForm()

    if form.validate_on_submit():
        amount = float(form.amount.data)
        duration = int(form.duration.data)

        # Проверка на минимальную сумму кредита
        if amount < 1000:
            return render_template('request_loan.html', form=form, error="Минимальная сумма кредита - 1000 рублей")

        # Вычитаем сумму депозита из баланса пользователя
        user_balance = current_user.balance.get()
        current_balance = user_balance.balance  # Доступ к реальному значению баланса
        updated_balance = current_balance + amount
        user_balance.balance = updated_balance
        user_balance.save()

        # Расчет процентной ставки в зависимости от срока
        interest_rate = calculate_interest_rate(duration)

        # Расчет ежемесячного платежа
        monthly_payment = calculate_monthly_payment(amount, interest_rate, duration)

        # Создание записи о кредите в базе данных
        create_credit_record(current_user.client_id, amount, duration, monthly_payment, interest_rate)

        transaction = TransactionLog.create(client_id=current_user,
                                            operation_datetime=str(datetime.now().strftime("%c")),
                                            operation_type='credit',
                                            operation_amount=amount)
        transaction.save()

        return redirect(url_for('dashboard'))
        # return render_template('dashboard.html', amount=amount, interest_rate=interest_rate, duration=duration,
        #                        monthly_payment=monthly_payment, get_loan_period=get_loan_period)

    return render_template('request_loan.html', form=form)


# Дополнительная функция для создания записи о кредите в базе данных
def create_credit_record(client_id, amount, duration, monthly_payment, interest_rate):
    end_date = datetime.now() + timedelta(days=duration * 365)
    date_opened = datetime.now()
    loan = Loan.create(amount=amount, interest_rate=interest_rate, type='Кредит')
    next_payment_date = datetime.now() + timedelta(days=30)
    credit = Credit.create(client_id=client_id, closing_date=end_date, next_payment_date=next_payment_date,
                           next_payment_amount=monthly_payment, loan_id=loan, date_opened=date_opened)
    credit.save()

    # Создание уведомления о кредите
    # notification_content = f'Оформлен кредит: {amount} рублей, ежемесячный платеж: {monthly_payment} рублей'
    # create_notification(client_id, 'credit', notification_content)


# Функция для расчета процентной ставки в зависимости от срока
def calculate_interest_rate(duration):
    if duration <= 3:
        return 8.0
    elif duration <= 5:
        return 10.0
    else:
        return 12.0


# Функция для расчета ежемесячного платежа
def calculate_monthly_payment(amount, interest_rate, duration):
    total_payments = amount * (interest_rate / 100 + 1)
    monthly_payment = total_payments / (duration * 12)
    return round(monthly_payment, 2)


@socketio.on('connect')
def handle_connect():
    # Отправить уведомления при подключении
    emit_notifications()


def emit_notifications():
    # Функция для отправки уведомлений на клиент
    # Замените этот код на ваш код получения уведомлений из базы данных
    notifications = [
        {'type': 'payment_due', 'content': 'Оплата кредита: 1000 рублей', 'date': '2024-01-15'},
        {'type': 'interest_due', 'content': 'Начисление процентов по вкладу: 500 рублей', 'date': '2024-02-01'},
        # Добавьте другие уведомления по мере необходимости
    ]

    socketio.emit('notifications', notifications)


# Ваш роут для создания виртуальной карты
@app.route('/create_virtual_card', methods=['GET', 'POST'])
@login_required
def create_virtual_card():
    form = CardForm()

    # Проверка на количество созданных карт
    if Card.select().where(Card.client_id == current_user).count() >= 1:
        error_message = "У вас уже есть виртуальная карта."
        return render_template('create_virtual_card.html', user=current_user, form=form, error=error_message)

    elif form.validate_on_submit():
        # Логика создания виртуальной карты
        expiry_date = (datetime.now() + timedelta(days=4 * 365)).strftime('%Y-%m-%d')
        print(expiry_date)
        print(datetime.now())
        # Генерация номера карты и проверка уникальности
        generated_card_number = generate_unique_card_number()

        # Создание виртуальной карты
        virtual_card = Card.create(client_id=current_user, card_number=generated_card_number, expiry_date=expiry_date)
        virtual_card.save()

        # Записываем транзакцию
        transaction = TransactionLog.create(client_id=current_user,
                                            operation_datetime=str(datetime.now().strftime("%c")),
                                            operation_type='ordering a card')
        transaction.save()

        # Вывод информации о карте
        card_info = {
            'card_number': virtual_card.card_number,
            'expiry_date': virtual_card.formatted_expiry_date(),
            'full_name': current_user.full_name,
        }

        return render_template('card_info.html', card_info=card_info)

    for error in form.errors:
        print(error)
    return render_template('create_virtual_card.html', user=current_user, form=form)


# @app.route('/card_info', methods=['GET', 'POST'])
# @login_required
# def card_info():
#
#     return render_template('card_info.html', card_info=card_info, user=current_user, expiry_date=expiry_date)

# Генерация уникального номера карты
def generate_unique_card_number():
    while True:
        # Генерация случайного 16-значного номера карты
        generated_card_number = ''.join(random.choices(string.digits, k=16))

        # Проверка на уникальность номера карты в базе данных
        if not Card.select().where(Card.card_number == generated_card_number).exists():
            break

    return generated_card_number


# Генерация уникального номера карты
def generate_unique_card_number():
    while True:
        # Генерация случайного 16-значного номера карты
        generated_card_number = ''.join(random.choices(string.digits, k=16))

        # Проверка на уникальность номера карты в базе данных
        if not Card.select().where(Card.card_number == generated_card_number).exists():
            break

    return generated_card_number


@app.route('/transfer_funds', methods=['GET', 'POST'])
@login_required
def transfer_funds():
    form = TransferFundsForm()
    balance = getClientBalance(current_user)

    if form.validate_on_submit():
        transfer_method = form.transfer_method.data
        amount = float(form.amount.data)

        if transfer_method == 'phone':
            recipient_phone = form.recipient_identifier.data
            recipient = Client.get_or_none(Client.phone == recipient_phone)
        elif transfer_method == 'card':
            recipient_card_number = form.recipient_identifier.data
            recipient = (
                Client
                .select()
                .join(Card)  # Join with the Card model
                .where(Card.card_number == recipient_card_number)
                .get()
            )
        else:
            return render_template('transfer_funds.html', error="Выберите только один метод для перевода.")

        if recipient:
            print(recipient)
            # Логика перевода средств
            sender_balance = current_user.balance.get()

            if sender_balance.balance >= amount:
                # Вычитаем сумму перевода из баланса отправителя
                sender_balance.reduce_balance(amount)

                recipient_balance = getClientBalance(recipient)

                recipient.balance.get().increase_balance(amount)
                # Получаем баланс получателя или создаем новую запись
                # recipient_balance = recipient.balance.get_or_create()
                # recipient_balance.increase_balance(amount)

                # Записываем транзакции
                transaction = TransactionLog.create(client_id=current_user,
                                                    operation_datetime=str(datetime.now().strftime("%c")),
                                                    operation_type='sending a transfer',
                                                    operation_amount=amount,
                                                    recipients_name=recipient.full_name)
                transaction.save()

                recipient_transaction = TransactionLog.create(client_id=recipient,
                                                              operation_datetime=str(datetime.now().strftime("%c")),
                                                              operation_type='transfer receipt',
                                                              operation_amount=amount,
                                                              recipients_name=current_user.full_name)
                recipient_transaction.save()

                # Возвращение в личный кабинет после перевода
                return redirect(url_for('dashboard'))
            else:
                error_message = "Недостаточно средств на балансе."
        else:
            error_message = "Получатель не найден."

        return render_template('transfer_funds.html', error=error_message,form=form, current_balance=balance)

    return render_template('transfer_funds.html', current_balance=balance, form=form)


if __name__ == '__main__':
    db.connect()
    socketio.run(app)
    # db.create_tables([Client, ClientBalance], safe=True)
    app.run(debug=True)
