from flask import Blueprint, render_template, request, redirect, session

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == "admin" and password == "password":
            session["user"] = username
            return redirect("/upload")
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@auth.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
