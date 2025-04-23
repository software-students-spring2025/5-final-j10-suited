import os
import random
from dotenv import load_dotenv
from bson.objectid import ObjectId
import pymongo
import certifi
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

load_dotenv()
app = Flask(__name__)

# initialize database
mongo = pymongo.MongoClient(
    os.getenv(
        "MONGO_URI",
        "mongodb://admin:secretpassword@localhost:27017/gesture_auth?authSource=admin",
    ),
    tlsCAFile=certifi.where(), tls=True, 
)
db = mongo[os.getenv("MONGO_DBNAME", "test_db")]
app.config["MONGO_URI"] = os.getenv(
        "MONGO_URI",
        "mongodb://admin:secretpassword@localhost:27017/gesture_auth?authSource=admin",
    )
app.secret_key = os.getenv("SECRET_KEY", "secretsecretkey")

app.config.update(
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.example.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
)
mail = Mail(app)

#login manager setup
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, data):
        self.id = str(data['_id'])
        self.first_name = data.get('first_name')
        self.last_name = data.get('last_name')
        self.email = data.get('email')
        self.verified = data.get('verified', False)


@login_manager.user_loader
def load_user(user_id):
    data = db.Users.find_one({'_id': ObjectId(user_id)})
    return User(data) if data else None


#temporary- just for making sure that db connection works
@app.route('/test_db')
def test_db():
    user = db.Users.find_one({"name": "test"})
    if not user:
        return abort(404, "User not found")
    return user["name"]


@app.route('/home')
def home():
    return render_template("home.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm  = request.form['confirm_password']

        # Validations
        #add validation that email is nyu
        domain = email.split("@")[-1]
        if domain != "nyu.edu":
            flash('Must be an NYU email.', 'danger')
            return render_template('register.html')
        if db.Users.find_one({'email': email}):
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        # Hash password
        hashed_pw = generate_password_hash(password)

        # Generate verification code
        code = str(random.randint(100000, 999999))

        # Store user with unverified status
        db.Users.insert_one({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': hashed_pw,
            'verified': False,
            'verification_code': code,
            'joined_groups': []
        })

        # Send verification email
        msg = Message('Your Verification Code', recipients=[email])
        msg.body = f"Hi {first_name},\n\nYour verification code is: {code}\n\nEnter this on the site to complete registration."
        mail.send(msg)

        return redirect(url_for('verify_email', email=email))

    return render_template('register.html')


@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    email = request.args.get('email')
    if request.method == 'POST':
        code = request.form['code']
        user = db.Users.find_one({'email': email})
        if not user:
            flash('Invalid request.')
            return redirect(url_for('register'))

        if user.get('verification_code') == code:
            # Mark verified and remove code
            db.Users.update_one(
                {'email': email},
                {'$set': {'verified': True}, '$unset': {'verification_code': ''}}
            )
            flash('Email verified! You can now log in.')
            return redirect(url_for('login'))
        else:
            return render_template('verify_email.html', email=email, error='Incorrect code')

    return render_template('verify_email.html', email=email)


#need to fill in for how to connect to NYU SSO
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        data = db.Users.find_one({'email': email})
        if not data or not check_password_hash(data['password'], password):
            return render_template('login.html', error='Invalid email or password')

        if not data.get('verified', False):
            flash('Please verify your email before logging in.')
            return redirect(url_for('verify_email', email=email))

        user = User(data)
        login_user(user)
        flash('Logged in successfully.')
        return redirect(url_for('group_browser'))

    return render_template('login.html')


#select groups html page
@app.route("/select_groups", methods=["GET"])
def select_groups():
    groups = db.Groups.find({})
    user = db.Users.find_one({'_id': ObjectId(current_user.id)})
    print('joined_groups:', user['joined_groups'])
    joined_groups = user['joined_groups']
    return render_template("select_groups.html", groups=groups, joined_groups=joined_groups, error=None)


@app.route("/add_group", methods=["POST"])
def add_group():
    groups = db.Groups.find({})
    new_group = request.form.get("custom_group", "").strip()
    if not new_group:
        return render_template("select_groups.html", groups=groups, error="Please enter a group name.")

    lowercased = [g['name'].lower() for g in groups]
    if new_group.lower() in lowercased:
        return render_template("select_groups.html", groups=groups, error="Group already exists.")

    user_name = current_user.first_name + ' ' + current_user.last_name
    new_group_dict = {
        'name': new_group,
        'owner': ObjectId(current_user.id),
        'members': []
    }
    db.Groups.insert_one(new_group_dict)
    return redirect(url_for("select_groups"))


@app.route("/save_groups", methods=["POST"])
def save_groups():
    selected_groups = request.form.getlist("groups")
    user_id = ObjectId(current_user.id)

    user = db.Users.find_one({'_id': user_id})
    old_groups = user.get('joined_groups', [])

    db.Users.update_one(
        {'_id': user_id},
        {'$set': {'joined_groups': selected_groups}},
    )

    for group_name in selected_groups:
        db.Groups.update_one(
            {'name': group_name},
            {'$addToSet': {'members': user_id}}
        )

    unchecked_groups = set(old_groups) - set(selected_groups)
    for group_name in unchecked_groups:
        db.Groups.update_one(
            {'name': group_name},
            {'$pull': {'members': user_id}}
        )
    flash("Groups saved!", "success")
    return redirect(url_for("select_groups"))


@app.route("/profile")
def profile():
    #registration does not ask for grade, major, age etc. 
    #should add "finish setting up profile" option here to add those things

    # get mongodb user from user_id
    # user = users_collection.find_one({"_id": session["user_id"]})
    # profile = {
    #     'name': user['name'],
    #     'age': user['age'],
    #     'grade': user['grade'],
    #     'groups': user['groups']
    # }
    profile = {
        'picture': 'example_image',
        'name': "Jack",
        'age': 21,
        'grade': "Junior",
        'groups': session.get('selected_groups', ['None joined yet'])
    }
    return render_template("profile.html", profile=profile)


@app.route('/group_browser')
def group_browser():
    groups = db.Groups.find()
    return render_template('group_browser.html', groups=groups)


@app.route('/')
def index():
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
