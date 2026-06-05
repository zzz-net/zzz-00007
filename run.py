from app import create_app, db
from init_db import init_database

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_database()
    app.run(host='127.0.0.1', port=5000, debug=True)
