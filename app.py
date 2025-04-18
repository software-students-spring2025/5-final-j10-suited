from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'super_secret'

#need to fill in for how to connect to NYU SSO

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
    return "Groups saved!"
