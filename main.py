from app import *
if __name__ == '__main__':
    db.connect()
    db.create_tables([Client], safe=True)
    app.run(debug=True)
