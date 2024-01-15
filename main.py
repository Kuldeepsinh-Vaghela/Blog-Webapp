from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, g
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor

# from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import bleach
import os



app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
#8BYkEfBA6O6donzWlSihBXox7C0sKR6b

ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login


# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
db = SQLAlchemy()
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.relationship('User', back_populates='posts')
    author_id = db.Column(db.Integer, db.ForeignKey('User_Data.id'))
    img_url = db.Column(db.String(250), nullable=False)
    comment = db.relationship("Comment", back_populates='posts')




# TODO: Create a User table for all your registered users. 
class User(db.Model, UserMixin):
    __tablename__ = "User_Data"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200),unique=True, nullable=False)
    password = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(200),unique=True, nullable=False)
    posts = db.relationship("BlogPost",back_populates='author')
    comment = db.relationship("Comment", back_populates='author')

# Creating a Comment table to store all the comments
class Comment(db.Model):
    __tablename__ = "Comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.relationship("User", back_populates='comment')
    author_id = db.Column(db.Integer, db.ForeignKey('User_Data.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    posts = db.relationship("BlogPost",back_populates='comment')


with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    result = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
    return result



# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        user_data = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user_data:
            flash("The email already exist, please try to log in")
            return redirect(url_for('login'))
        else:
            new_row = User(name=name,email=email,password=hashed_password)
            db.session.add(new_row)
            db.session.commit()
            login_user(new_row)
            return redirect(url_for('get_all_posts'))

    return render_template("register.html", form= form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET','POST'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        req_user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if req_user:
            if check_password_hash(req_user.password, password):
                login_user(req_user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("The password is incorrect")
                return redirect(url_for('login'))
        else:
            flash("The email is not registered, please check again")
            return redirect(url_for('login'))


    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    author_name = {}
    for post in posts:
        author_id = post.id
        author_info = db.session.execute(db.select(User).where(User.id == author_id)).scalar()
        author_name[author_id] = author_info.name

    if current_user.is_authenticated:
        return render_template("index.html", all_posts=posts, logged_in = current_user.is_authenticated, id= current_user.id, author_name = author_name)
    else:
        return render_template("index.html", all_posts=posts, logged_in = current_user.is_authenticated, id = 0, author_name = author_name)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET","POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    author_id = requested_post.id
    author_info = db.session.execute(db.select(User).where(User.id == author_id)).scalar()
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            text = comment_form.comment.data
            cleaned_text = bleach.clean(text, strip=True)
            author = current_user
            posts = requested_post
            new_row = Comment(text = cleaned_text, author = author, posts = posts)
            db.session.add(new_row)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash("Please log in before commenting on any post")
            return redirect(url_for('login'))
    comments = db.session.execute(db.select(Comment)).scalars()
    if current_user.is_authenticated:
        return render_template("post.html", post=requested_post, id= current_user.id, author_name = author_info.name, comment_form = comment_form, comments = comments)
    else:
        return render_template("post.html", post=requested_post, id= 0, author_name = author_info.name, comment_form = comment_form, comments = comments)

    

def adminonly(function):
    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.id == 1:
            return function(*args, **kwargs)
        else:
            abort(403)
    return wrapper


# TODO: Use a decorator so only an admin user can create a new post

@app.route("/new-post", methods=["GET", "POST"])
@adminonly
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in = current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can edit a post

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@adminonly
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True,  logged_in = current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can delete a post

@app.route("/delete/<int:post_id>")
@adminonly
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html", logged_in = current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in = current_user.is_authenticated)


if __name__ == "__main__":
    app.run(debug=False, port=5002)
