import os
from dotenv import load_dotenv
import pymongo
import certifi
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

load_dotenv()
app = Flask(__name__)

# initialize database
mongo = pymongo.MongoClient(
    os.getenv(
        "MONGO_URI",
        "mongodb://admin:secretpassword@localhost:27017/gesture_auth?authSource=admin",
    ),
    tlsCAFile=certifi.where(), ssl = True
)
db = mongo[os.getenv("MONGO_DBNAME", "test_db")]
app.config["MONGO_URI"] = os.getenv(
        "MONGO_URI",
        "mongodb://admin:secretpassword@localhost:27017/gesture_auth?authSource=admin",
    )
app.secret_key = os.getenv("SECRET_KEY", "secretsecretkey")

#temporary- just for making sure that db connection works
@app.route('/test_db')
def test_db():
    user = db.Users.find_one({"name": "test"})
    if not user:
        return abort(404, "User not found")
    return user["name"]

#need to fill in for how to connect to NYU SSO
@app.route('/login', methods=["GET", "POST"])
def login():
    return render_template("login.html")

#select groups html page
@app.route("/select_groups", methods=["GET"])
def select_groups():
    if "groups" not in session:
        session["groups"] = ["Running", "Swimming", "Music", "Photography", "Cooking", "Coding"]
    return render_template("select_groups.html", groups=session["groups"], error=None)

@app.route("/add_group", methods=["POST"])
def add_group():
    new_group = request.form.get("custom_group", "").strip()
    if not new_group:
        return render_template("select_groups.html", groups=session["groups"], error="Please enter a group name.")

    lowercased = [g.lower() for g in session["groups"]]
    if new_group.lower() in lowercased:
        return render_template("select_groups.html", groups=session["groups"], error="Group already exists.")

    session["groups"].append(new_group)
    return redirect(url_for("select_groups"))

@app.route("/save_groups", methods=["POST"])
def save_groups():
    selected_groups = request.form.getlist("groups")
    print("User selected:", selected_groups)
    session['selected_groups'] = selected_groups    # testing profile, should save to database instead
    flash("Groups saved!", "success")
    return redirect(url_for("select_groups"))

@app.route("/profile")
def profile():
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
        'groups': session.get('selected_groups', 'None joined yet.')
    }
    return render_template("profile.html", profile=profile)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
