import os
import random
from datetime import timezone
import datetime
from dotenv import load_dotenv
from bson import ObjectId, json_util
import pymongo
import certifi
from gridfs import GridFS
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify, Response
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from flask_socketio import SocketIO, join_room, leave_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

load_dotenv()
app = Flask(__name__)

# initialize database
uri = os.getenv("MONGO_URI") or \
      "mongodb://admin:secretpassword@localhost:27017/gesture_auth?authSource=admin"
mongo = pymongo.MongoClient(
    uri,
    tlsCAFile=certifi.where(), tls=True, 
)
db_name = os.getenv("MONGO_DBNAME", "test_db") or \
            "test_db"
db = mongo[db_name]
fs = GridFS(db) 
uri = os.getenv(
        "MONGO_URI",
        "mongodb://admin:secretpassword@localhost:27017/gesture_auth?authSource=admin",
    ) or "mongodb://admin:secretpassword@localhost:27017/gesture_auth?authSource=admin"
app.config["MONGO_URI"] = uri

db.Votes.create_index(
    [
      ('user_id',    pymongo.ASCENDING),
      ('target_id',  pymongo.ASCENDING),
      ('target_type',pymongo.ASCENDING)
    ],
    unique=True
)
secretkey = os.getenv("SECRET_KEY", "secretsecretkey") or "secretsecretkey"
app.secret_key = secretkey

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

socketio = SocketIO(app)

@app.route('/chat/<other_id>')
@login_required
def chat(other_id):
    # Determine room key (sorted pair of user IDs)
    user_id = current_user.id
    room = '_'.join(sorted([user_id, other_id]))
    # Load other user's name and chat history
    other = db.Users.find_one({'_id':ObjectId(other_id)})
    raw_msgs = db.Messages.find({'room': room}).sort('timestamp', 1)
    history = []
    for m in raw_msgs:
        history.append({
            'sender_id': str(m['sender_id']),
            'body': m['body'],
            'timestamp': m['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_template('chat.html', other_id=other_id, other_name=other['first_name'], room=room, history=history)

@socketio.on('join')
def on_join(data):
    join_room(data['room'])

@socketio.on('leave')
def on_leave(data):
    leave_room(data['room'])

@socketio.on('send_message')
def handle_message(data):
    sender = ObjectId(data['sender_id'])
    recipient = ObjectId(data['recipient_id'])
    body = data['body']
    ts = datetime.datetime.now(timezone.utc)
    room = data['room']
    # Save to DB
    db.Messages.insert_one({
        'sender_id': sender,
        'recipient_id': recipient,
        'body': body,
        'timestamp': ts,
        'room': room
    })
    # Broadcast
    emit('receive_message', {
        'sender_id': data['sender_id'],
        'body': body,
        'timestamp': ts.astimezone().strftime('%Y-%m-%d %H:%M:%S')
    }, room=room)

# User listing route
@app.route('/users')
@login_required
def users_list():
    raw = db.Users.find().sort([('first_name', 1), ('last_name', 1)])
    users = []
    for u in raw:
        if  not str(u['_id']) == str(current_user.get_id()):
            users.append({
                'id': str(u['_id']),
                'first_name': u.get('first_name'),
                'last_name': u.get('last_name'),
                'email': u.get('email')
            })
    return render_template('users.html', users=users)


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
    else:
        return render_template('login.html')

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

#select groups html page
@app.route("/select_groups", methods=["GET"])
def select_groups():
    groups = db.Groups.find({})
    user = db.Users.find_one({'_id': ObjectId(current_user.id)})
    print('joined_groups:', user['joined_groups'])
    group_ids = user['joined_groups']
    group_dbs = db.Groups.find({'_id': {'$in': group_ids}}, {'name': 1})
    group_names = [group['name'] for group in group_dbs]
    return render_template("select_groups.html", groups=groups, joined_groups=group_names, error=None)


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
    selected_group_names = request.form.getlist("groups")
    user_id = ObjectId(current_user.id)

    user = db.Users.find_one({'_id': user_id})
    old_group_ids = user.get('joined_groups', [])
    selected_group_ids = []

    for group_name in selected_group_names:
        group = db.Groups.find_one({'name': group_name}, {'_id': 1})
        if group:
            selected_group_ids.append(group['_id'])
            db.Groups.update_one(
                {'_id': group['_id']},
                {'$addToSet': {'members': user_id}}
            )

    unchecked_group_ids = set(old_group_ids) - set(selected_group_ids)
    for gid in unchecked_group_ids:
        db.Groups.update_one(
            {'_id': gid},
            {'$pull': {'members': user_id}}
        )

    db.Users.update_one(
        {'_id': user_id},
        {'$set': {'joined_groups': selected_group_ids}}
    )

    flash("Groups saved!", "success")
    return redirect(url_for("select_groups"))


def get_user():
        user = db.Users.find_one({"_id": ObjectId(current_user.get_id())})
        gp_list = [db.Groups.find_one(ObjectId(gid))['name'] for gid in user['joined_groups']]
        profile = {
            'name': f"{user['first_name']} {user['last_name']}",
            'groups': gp_list
        }
        try:
            profile['age'] = user['age']
        except:
            profile['age'] = None
        try:
            profile['grade'] = user['grade']
        except:
            profile['grade'] = None
        return profile

@app.route("/profile")
@login_required
def profile():
    #registration does not ask for grade, major, age etc. 
    #should add "finish setting up profile" option here to add those things
    profile = get_user()
    return render_template("profile.html", profile=profile)

@app.route("/set_age", methods=['POST'])
def set_age():
    age = request.form['age']
    db.Users.update_one({"_id": ObjectId(current_user.get_id())}, {'$set': {'age': age}})
    return redirect(url_for('profile'))

@app.route("/reset_age")
def reset_age():
    db.Users.update_one({"_id": ObjectId(current_user.get_id())}, {'$set': {'age': None}})
    return redirect(url_for('profile'))

@app.route("/set_grade", methods=['POST'])
def set_grade():
    grade = request.form['grade']
    db.Users.update_one({"_id": ObjectId(current_user.get_id())}, {'$set': {'grade': grade}})
    return redirect(url_for('profile'))

@app.route("/reset_grade")
def reset_grade():
    db.Users.update_one({"_id": ObjectId(current_user.get_id())}, {'$set': {'grade': None}})
    return redirect(url_for('profile'))

@app.route('/group_browser')
def group_browser():
    groups = db.Groups.find()
    return render_template('group_browser.html', groups=groups)


@app.route('/')
def index():
    return redirect(url_for('home'))


@app.route('/group_detail/<gid>')
@login_required
def group_detail(gid):
    group = db.Groups.find_one({'_id': ObjectId(gid)})
    if not group:
        abort(404)
    member_ids = group.get('members', [])
    is_member  = ObjectId(current_user.id) in member_ids

    history = []
    for m in db.Messages.find({'group_id': ObjectId(gid)}).sort('timestamp', 1):
        user = db.Users.find_one({'_id': m['user_id']})
        if user:
            username = user.get('first_name')
        else:
            username = 'Unknown'
        history.append({
            'sender_id': str(m['user_id']),
            'username':  username,
            'body': m['content'],
            'timestamp': m['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        })

    room = f"group_{gid}"
    return render_template(
      'group_detail.html',
      group=group,
      is_member=is_member,
      room=room,
      history=history,
      gid=gid,
      user_id=current_user.id,
      username=current_user.first_name
    )


@app.route('/groups/<gid>/join', methods=['POST'])
@login_required
def join_group(gid):
    db.Groups.update_one({"_id": ObjectId(gid)}, {"$addToSet": {"members": ObjectId(current_user.id)}})
    db.Users.update_one({"_id": ObjectId(current_user.get_id())}, {"$addToSet": {"joined_groups": ObjectId(gid)}})
    return redirect(url_for('group_detail', gid=gid))

@app.route('/groups/<gid>/leave', methods=['POST'])
@login_required
def leave_group(gid):
    db.Groups.update_one({"_id": ObjectId(gid)}, {"$pull": {"members": ObjectId(current_user.id)}})
    db.Users.update_one({"_id": ObjectId(current_user.get_id())}, {"$pull": {"joined_groups": ObjectId(gid)}})
    return redirect(url_for('group_browser'))

@app.route('/groups/<gid>/post', methods=['POST'])
@login_required
def post_message(gid):
    content = request.form.get('content', '').strip()
    if content:
        db.Messages.insert_one({
            'group_id': ObjectId(gid),
            'user_id': ObjectId(current_user.id),
            'content': content,
            'timestamp': datetime.datetime.now(timezone.utc)
        })
    return redirect(url_for('group_detail', gid=gid))

@socketio.on('join_group')
def on_join_group(data):
    join_room(data['room'])

@socketio.on('send_group_message')
def handle_group_message(data):
    ts = datetime.datetime.now(timezone.utc)
    msg_doc = {
        'group_id':   ObjectId(data['gid']),
        'user_id':    ObjectId(data['sender_id']),
        'content':    data['body'],
        'timestamp':  ts,
        'room':       data['room']
    }
    db.Messages.insert_one(msg_doc)

    emit('new_group_message', {
        'sender_id': data['sender_id'],
        'username':  data['username'],
        'body':      data['body'],
        'timestamp': ts.astimezone().strftime('%Y-%m-%d %H:%M:%S')
    }, room=data['room'])


@app.route('/get_all_groups')
def get_all_groups():
    sort = request.args.get('sort', 'oldest')
    groups = list(db.Groups.find())
    for group in groups:
        group['_id'] = str(group['_id'])
    if sort == 'newest':
        groups.reverse()
    elif sort == 'members':
        groups = sorted(groups, key=lambda x: len(x["members"]), reverse=True)
    elif sort == 'alphabetical':
        groups = sorted(groups, key=lambda x: x["name"])
    return json_util.dumps(groups), 200, {'Content-Type': 'application/json'}

@app.route('/public_board')
@login_required    
def public_board():
    cursor = db.PublicPosts.find().sort('timestamp', -1)
    posts = []
    for p in cursor:
        comment_count = db.PublicComments.count_documents({
            'post_id': p['_id']
        })
        p['id']            = str(p['_id'])
        p['comment_count'] = comment_count
        posts.append(p)
    return render_template('public_board.html', posts=posts)

@app.route('/add_post', methods=['POST'])
@login_required
def add_post():
    username = current_user.first_name  
    text = request.form.get('text')
    file = request.files.get('file')

    file_id = None
    if file and file.filename:
        # secure the filename and stream into GridFS
        safe_name = secure_filename(file.filename)
        file_id   = fs.put(
            file.stream,
            filename=safe_name,
            content_type=file.mimetype,
            upload_date=datetime.datetime.now(),
            user_id=current_user.id
        )

    db.PublicPosts.insert_one({
        'username':  username,
        'text':      text,
        'timestamp': datetime.datetime.now(),
        'file_id':  file_id,
        'score':     0
    })
    return redirect(url_for('public_board'))

@app.route('/post/<post_id>')
def post_detail(post_id):
    post = db.PublicPosts.find_one({'_id': ObjectId(post_id)})
    if not post:
        abort(404)

    comments = list(db.PublicComments.find({'post_id': post['_id']})
                             .sort('timestamp', 1))

    tree = {}
    for c in comments:
        c['id']        = str(c['_id'])
        c['parent_id'] = str(c['parent_id']) if c.get('parent_id') else None
        c['timestamp'] = c['timestamp'].strftime('%Y-%m-%d %H:%M')
        tree.setdefault(c['parent_id'], []).append(c)

    return render_template('post_detail.html',
                           post=post, tree=tree)

@app.route('/uploads/<file_id>')
def serve_file(file_id):
    grid_out = fs.get(ObjectId(file_id))
    return Response(
        grid_out.read(),
        mimetype=grid_out.content_type,
        headers={'Content-Disposition': f'inline; filename={grid_out.filename}'}
    )

@app.route('/post/<post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    parent = request.form.get('parent_id')  
    text   = request.form['text'].strip()
    if not text:
        flash('Cannot post empty comment.', 'warning')
        return redirect(url_for('post_detail', post_id=post_id))

    db.PublicComments.insert_one({
        'post_id':   ObjectId(post_id),
        'parent_id': ObjectId(parent) if parent else None,
        'user_id':   ObjectId(current_user.id),
        'username':  current_user.first_name,
        'text':      text,
        'timestamp': datetime.datetime.now(),
        'score':     0
    })
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/vote', methods=['POST'])
@login_required
def vote():
    user_id     = ObjectId(current_user.id)
    target_id   = ObjectId(request.form['id'])
    vote_val    = int(request.form['vote'])   
    target_type = request.form['type']       

    # pick the right collection
    coll = db.PublicPosts if target_type == 'post' else db.PublicComments

    # vote record key
    vote_doc = {
      'user_id':     user_id,
      'target_id':   target_id,
      'target_type': target_type
    }

    existing = db.Votes.find_one(vote_doc)
    if existing:
        if existing['vote'] == vote_val:
            # already voted the same way
            flash('You already voted.', 'info')
        else:
            
            coll.update_one({'_id': target_id},
                            {'$inc': {'score': 2 * vote_val}})
            db.Votes.update_one(vote_doc, {'$set': {'vote': vote_val}})
    else:
        # first time voting
        coll.update_one({'_id': target_id},
                        {'$inc': {'score': vote_val}})
        db.Votes.insert_one({**vote_doc,
                             'vote':      vote_val,
                             'timestamp': datetime.datetime.now()})
    # go back where we came from
    return redirect(request.form.get('next') or url_for('public_board'))


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)

