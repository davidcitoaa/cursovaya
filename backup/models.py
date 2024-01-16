# models.py
from app import *


# Определение базовой модели Peewee
class BaseModel(Model):
    class Meta:
        database = db


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
    role = CharField(max_length=50, default='user')
    blocked = CharField(max_length=50, default=None)

    def block(self):
        # Реализуйте здесь логику блокировки клиента
        # Например, вы можете установить флаг в базе данных, указывающий на блокировку
        self.blocked = True
        self.save()  # Сохраняем изменения в базе данных

    def is_blocked(self):
        return self.blocked

    def check_password(self, password):
        return get_hashed_password(password) == self.password

    class Meta:
        database = db
        db_table = 'client'


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


class Card(BaseModel):
    card_id = AutoField(primary_key=True)
    client_id = ForeignKeyField(Client, backref='cards')
    card_number = CharField(max_length=255, unique=True)
    expiry_date = CharField(max_length=255)

    def formatted_expiry_date(self):
        return datetime.strptime(self.expiry_date, '%Y-%m-%d').strftime('%d.%m.%Y')

    class Meta:
        table_name = 'card'


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


class UploadDataForm(FlaskForm):
    tables = SelectField('Выбрать таблицы', choices=[
        (table, table) for table in db.get_tables()
    ])
    format = SelectField('Формат', choices=[('json', 'JSON'), ('csv', 'CSV')])
    file_name = StringField('Имя файла')


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