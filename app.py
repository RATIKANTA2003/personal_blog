from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def index():
    posts = Post.query.order_by(Post.date.desc()).all()
    return render_template("index.html", posts=posts)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    posts = Post.query.all()
    return render_template("dashboard.html", posts=posts)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        post = Post(
            title=request.form["title"],
            content=request.form["content"]
        )
        db.session.add(post)
        db.session.commit()
        return redirect("/dashboard")
    return render_template("add_post.html")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if request.method == "POST":
        post.title = request.form["title"]
        post.content = request.form["content"]
        db.session.commit()
        return redirect("/dashboard")
    return render_template("edit_post.html", post=post)

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return redirect("/dashboard")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # create default admin
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password="admin")
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
