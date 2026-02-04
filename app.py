import os
import math
import markdown
import sqlalchemy
from datetime import datetime, timezone
from flask import Flask, render_template, redirect, url_for, request, flash
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
# Secure: Use environment variable for secret key on Railway
app.secret_key = os.environ.get("SECRET_KEY", "secret123")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False 

# --- Folder Configurations ---
UPLOAD_FOLDER = 'static/post_pics'
PROFILE_FOLDER = 'static/profile_pics'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_FOLDER'] = PROFILE_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# --- OAuth Configuration (Only Google remains) ---
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'PASTE_YOUR_GOOGLE_CLIENT_ID_HERE'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'PASTE_YOUR_GOOGLE_CLIENT_SECRET_HERE'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True) 
    mobile = db.Column(db.String(20), nullable=True)
    profile_pic = db.Column(db.String(100), nullable=False, default='default.jpg')
    language = db.Column(db.String(50), default='English')
    date_joined = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General')
    image_file = db.Column(db.String(100), nullable=True)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    author = db.relationship('User', backref='user_comments', lazy=True)

class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date_subscribed = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Helper Functions & Filters ---
def estimate_reading_time(text):
    words_per_minute = 200
    words = len(text.split())
    minutes = math.ceil(words / words_per_minute)
    return minutes

@app.template_filter('markdown')
def render_markdown(text):
    return Markup(markdown.markdown(text, extensions=['extra', 'nl2br']))

@app.context_processor
def inject_categories():
    categories = db.session.query(Post.category).distinct().all()
    category_list = [c[0] for c in categories]
    return dict(all_categories=category_list)

# --- Google Auth Routes ---
@app.route('/login/google')
def google_login():
    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if user_info:
        email = user_info['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                username=user_info.get('name', user_info.get('given_name')),
                email=email,
                password="google_oauth_managed",
                profile_pic=user_info.get('picture', 'default.jpg')
            )
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        flash(f"Logged in via Google as {user.username}", "success")
    return redirect(url_for('index'))

# --- Public Routes ---
@app.route("/")
def index():
    cat = request.args.get('category')
    posts = Post.query.filter_by(category=cat).order_by(Post.date.desc()).all() if cat else Post.query.order_by(Post.date.desc()).all()
    return render_template("index.html", posts=posts)

@app.route("/post/<int:id>")
def post(id):
    post_data = Post.query.get_or_404(id)
    related_posts = Post.query.filter(Post.category == post_data.category, Post.id != id).order_by(Post.date.desc()).limit(3).all()
    read_time = estimate_reading_time(post_data.content)
    return render_template("post.html", post=post_data, related_posts=related_posts, read_time=read_time)

# --- Interaction Routes ---
@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    post_obj = Post.query.get_or_404(post_id)
    post_obj.likes += 1
    db.session.commit()
    return redirect(url_for('post', id=post_id))

@app.route("/post/<int:post_id>/dislike", methods=["POST"])
@login_required
def dislike_post(post_id):
    post_obj = Post.query.get_or_404(post_id)
    post_obj.dislikes += 1
    db.session.commit()
    return redirect(url_for('post', id=post_id))

@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.form.get("content")
    if content:
        new_comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
        db.session.add(new_comment)
        db.session.commit()
        flash("Your comment has been posted!", "success")
    return redirect(url_for('post', id=post_id))

@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email")
    if email:
        existing = Newsletter.query.filter_by(email=email).first()
        if not existing:
            new_sub = Newsletter(email=email)
            db.session.add(new_sub)
            db.session.commit()
            flash("Successfully joined the newsletter!", "success")
        else:
            flash("This email is already subscribed.", "info")
    return redirect(url_for('index'))

# --- Auth Routes ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        language = request.form.get("language")

        if username.lower() == 'admin':
            flash("This username is reserved.", "danger")
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('register'))
        if email and User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password, language=language)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard") if user.username == 'admin' else url_for("index"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("index"))

# --- Profile ---
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        new_email = request.form.get("email")
        if new_email != current_user.email and User.query.filter_by(email=new_email).first():
            flash("That email is already taken.", "danger")
            return redirect(url_for('profile'))
        
        file = request.files.get('profile_img')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filename = f"user_{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
            current_user.profile_pic = filename
            
        current_user.email = new_email
        current_user.mobile = request.form.get("mobile")
        current_user.language = request.form.get("language")
        db.session.commit()
        flash("Profile updated successfully!", "success")
    return render_template("profile.html")

# --- Admin Routes ---
@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    search = request.args.get('search')
    posts = Post.query.filter(Post.title.contains(search)).order_by(Post.date.desc()).all() if search else Post.query.order_by(Post.date.desc()).all()
    subscribers = Newsletter.query.order_by(Newsletter.date_subscribed.desc()).all()
    user_count = User.query.filter(User.username != 'admin').count()
    return render_template("dashboard.html", posts=posts, subscribers=subscribers, user_count=user_count)

@app.route("/add_post", methods=["GET", "POST"])
@login_required
def add_post():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    if request.method == "POST":
        title, content = request.form["title"], request.form["content"]
        category = request.form.get("category", "General")
        file = request.files.get('image')
        filename = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_post = Post(title=title, content=content, category=category, image_file=filename)
        db.session.add(new_post)
        db.session.commit()
        flash("New post published!", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_post.html")

@app.route("/edit_post/<int:id>", methods=["GET", "POST"])
@login_required
def edit_post(id):
    if current_user.username != 'admin': 
        return redirect(url_for('index'))
    post_item = Post.query.get_or_404(id)
    if request.method == "POST":
        post_item.title, post_item.content = request.form["title"], request.form["content"]
        post_item.category = request.form.get("category", post_item.category)
        file = request.files.get('image')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post_item.image_file = filename
        db.session.commit()
        flash("Post updated!", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit_post.html", post=post_item)

@app.route("/delete_post/<int:id>")
@login_required
def delete_post(id):
    if current_user.username != 'admin': 
        return redirect(url_for('index'))
    post_item = Post.query.get_or_404(id)
    db.session.delete(post_item)
    db.session.commit()
    flash("Post deleted.", "danger")
    return redirect(url_for("dashboard"))

# --- RAILWAY STARTUP LOGIC ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin_user = User(username="admin", password="admin", email="admin@gmail.com", language="English")
            db.session.add(admin_user)
            db.session.commit()
    
    # Railway assigns a port via the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)