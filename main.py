from app import *
if __name__ == '__main__':
    # db.connect()

    # db.create_tables([Client], safe=True)
    admin_email = 'qwetryuiop100@mail.com'
    admin_user = Client.select().where(Client.email == admin_email).first()

    if not admin_user:
        admin_user = Client(full_name='Davidcito', birth_date='2003-02-25', passport_data='12345678',
                            email=admin_email, phone='+79155553535', password='david123', role='admin')
        admin_user.save()
        print("Администратор добавлен")
    else:
        print("Администратор уже существует")

    app.run(debug=True)
