from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'super_secret'

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
