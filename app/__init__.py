import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    db_path = os.path.join(app.instance_path, 'change_freeze.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path.replace(os.sep, "/")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from app.routes import bp
    app.register_blueprint(bp, url_prefix='/api')

    return app
