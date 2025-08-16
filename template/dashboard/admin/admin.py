from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:kawser@localhost/clients_db'
db = SQLAlchemy(app)

# Example model
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(50))

# Flask-Admin setup
admin = Admin(app, name='Campaign Dashboard', template_mode='bootstrap3')
admin.add_view(ModelView(Campaign, db.session))

if __name__ == "__main__":
    app.run(debug=True)
