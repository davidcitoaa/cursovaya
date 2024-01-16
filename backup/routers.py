from models import *


@login_manager.user_loader
def load_user(user_id):
    return Client.get_by_id(user_id)


@app.route('/user_list')
@login_required  # Декоратор, требующий аутентификации пользователя
def user_list():
    # Здесь вы можете получить список всех пользователей из базы данных
    # Например, используя ORM Peewee: users = User.select()
    users = Client.select()

    # Затем передайте список пользователей в шаблон
    return render_template('user_list.html', current_user=current_user, users=users)


# Маршруты Flask
@app.route('/')
def index():
    # Проверяем роль пользователяs
    if current_user.is_authenticated:
        print(current_user.role)
        if current_user.role == 'admin':
            return render_template('admin_dashboard.html', current_user=current_user)
        else:
            return render_template('dashboard.html', current_user=current_user)
    return render_template('index.html', current_user=current_user)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Проверяем роль пользователя
    if current_user.is_authenticated and current_user.role == 'admin':
        return render_template('admin_dashboard.html', current_user=current_user)
    else:
        flash('У вас нет доступа к этой странице.', 'danger')
        return redirect(url_for('index'))


@app.route('/block_user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    user = Client.get_or_none(Client.client_id == user_id)

    if user:
        user.block()
        print(f'Пользователь {user.full_name} заблокирован успешно!', 'success')
    else:
        print('Пользователь не найден', 'error')

    return redirect(url_for('user_list'))


@app.route('/admin/users_list')
@login_required
def users_list():
    # Проверяем роль пользователя
    if current_user.is_authenticated and current_user.role == 'admin':
        users = Client.select()
        return render_template('users_list.html', users=users, current_user=current_user)
    else:
        flash('У вас нет доступа к этой странице.', 'danger')
        return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    for error in form.errors:
        print(error)

    error = ''

    if form.validate_on_submit():
        user = Client.get_or_none(Client.email == form.username.data)
        if user and user.check_password(form.password.data):
            # Проверка на блокировку пользователя
            if not user.is_blocked():
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                error = 'Ваша учетная запись заблокирована. Обратитесь к администратору.'
        else:
            error = 'Неверный логин или пароль'
    return render_template('login.html', form=form, error=error)


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

        return render_template('transfer_funds.html', error=error_message, form=form, current_balance=balance)

    return render_template('transfer_funds.html', current_balance=balance, form=form)


# Роут для страницы загрузки данных
@app.route('/upload_data', methods=['GET', 'POST'])
@login_required
def upload_data():
    form = UploadDataForm()

    if form.validate_on_submit():
        selected_table = form.tables.data
        selected_format = form.format.data
        file_name = form.file_name.data

        # Получите данные из базы данных (пример)
        model_class = Client.get()  # Получаем класс модели по имени таблицы
        data_from_db = model_class.select().dicts()

        # Создайте файл в выбранном формате
        if selected_format == 'json':
            export_to_json([model_to_dict(row) for row in data_from_db], f'{file_name}.json')
        elif selected_format == 'csv':
            export_to_csv(data_from_db, f'{file_name}.csv')

        flash(f'Данные из таблицы {selected_table} успешно выгружены в формате {selected_format}', 'success')
        return redirect(url_for('upload_data'))

    return render_template('upload_data.html', form=form)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (time, datetime)):
            return obj.isoformat()
        elif isinstance(obj, date):
            return str(obj)
        elif isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


# Функция для экспорта данных в CSV
def export_to_csv(data, headers, file_name):
    with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(data)


# Функция для экспорта данных в JSON
def export_to_json(data, file_name, saves_dir):
    with open(os.path.join(saves_dir, file_name), 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=4, cls=CustomEncoder)


def get_saves_directory(directory):
    # Получить путь к корневой папке приложения
    root_dir = os.path.dirname(os.path.realpath(__file__))

    # Объединить путь к корневой папке с именем файла
    saves_dir = os.path.join(root_dir, f'{directory}')
    return saves_dir


@app.route('/saves')
@login_required
def saves():
    # Получить данные из запроса
    credit = Credit.select().join(Loan).where(Credit.client_id == current_user)
    deposit = Deposit.select().join(Loan).where(Deposit.client_id == current_user)
    transaction_log = TransactionLog.select().where(TransactionLog.client_id == current_user)
    card = Card.select().where(Card.client_id == current_user)

    # loan
    deposit_loans = Loan.select().join(Deposit).where(Deposit.client_id == current_user)
    credit_loans = Loan.select().join(Credit).where(Credit.client_id == current_user)

    # Объединяем данные о займах из обеих моделей
    all_loans_data = list(deposit_loans) + list(credit_loans)
    # Информация о займах из модели Credit

    saves_dir = get_saves_directory('saves')

    # Сохранить данные
    save_to_csv_and_json(credit, saves_dir, table_name='credit')
    save_to_csv_and_json(deposit, saves_dir, table_name='deposit')
    save_to_csv_and_json(transaction_log, saves_dir, table_name='transaction_log')
    save_to_csv_and_json(card, saves_dir, table_name='card')
    save_to_csv_and_json(all_loans_data, saves_dir, table_name='loan')

    # Показать сообщение об успешном сохранении
    return render_template('saves.html', saves_dir=saves_dir)


def save_to_csv_and_json(data, saves_dir, table_name):
    with open(os.path.join(saves_dir, f'{table_name}_id={current_user}.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Получаем названия полей из модели
        header = data[0]._meta.fields
        field_names = [field for field in header]
        writer.writerow(field_names)

        # Записываем данные в CSV
        for item in data:
            row = [str(getattr(item, field)) for field in field_names]
            writer.writerow(row)

    if table_name == 'loan':
        # Информация о займах из модели Credit
        credit_loan_json = [c.loan_id.__data__ for c in
                            Credit.select().join(Loan).where(Credit.client_id == current_user)]

        # Информация о займах из модели Deposit
        deposit_loan_json = [c.loan_id.__data__ for c in
                             Deposit.select().join(Loan).where(Deposit.client_id == current_user)]

        # Объединение информации о займах из обеих моделей
        result_json = credit_loan_json + deposit_loan_json
    else:
        result_json = [c.__data__ for c in data]

    export_to_json(result_json, f'{table_name}_id={current_user}.json', saves_dir)


if __name__ == '__main__':
    db.connect()
    app.run(debug=True)