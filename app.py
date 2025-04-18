from flask import Flask, request, render_template, redirect, url_for, session, flash
import boto3, os, mysql.connector, bcrypt
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
#app.config['SECRET_KEY'] = # your key here
#app.config['SQLALCHEMY_DATABASE_URI'] = #your server here
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'uploads/'

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# AWS S3 setup
# s3 = boto3.client('s3', aws_access_key_id= #aws key here, aws_secret_access_key= #aws secret key here, region_name= #server here)
S3_BUCKET = 'picture-website-storage-project'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    username = current_user.username if current_user.is_authenticated else 'Guest'

    # List all objects in the S3 bucket
    response = s3.list_objects_v2(Bucket=S3_BUCKET)
    images = []

    if 'Contents' in response:
        for obj in response['Contents']:
            image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{obj['Key']}"
            images.append(image_url)

    return render_template('home.html', username=username, images=images, posts=[])

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash("Invalid login credentials")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        s3.upload_file(filepath, S3_BUCKET, filename)

        os.remove(filepath)
        flash("Image uploaded successfully!")
    else:
        flash("No file selected.")
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
