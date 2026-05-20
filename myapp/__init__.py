from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

with app.app_context():
    from myapp.models import EWord,Translation
    db.create_all()

from myapp import routes


#if __name__ == "__main__":
#    app.run(host='0.0.0.0')