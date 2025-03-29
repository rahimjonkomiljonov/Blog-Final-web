from datetime import date
from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import os
import smtplib

app = Flask(__name__)
app.config['SECRET_KEY'] = "8BYkEfBA6O6donzWlSihBXox7C0sKR6b"
ckeditor = CKEditor(app)
Bootstrap5(app)
my_email = os.environ.get('MY_EMAIL')
my_password = os.environ.get('MY_PASSWORD')

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@app.context_processor
def inject_gravatar():
    return dict(gravatar=gravatar)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# CREATE DATABASE
Base = declarative_base()
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
db = SQLAlchemy(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(Integer, primary_key=True)
    title = db.Column(String(250), unique=True, nullable=False)
    subtitle = db.Column(String(250), nullable=False)
    date = db.Column(String(250), nullable=False)
    body = db.Column(Text, nullable=False)
    img_url = db.Column(String(250), nullable=False)
    author_id = db.Column(Integer, ForeignKey('users.id'), nullable=False)
    author = relationship('User', back_populates='posts')
    comments = relationship('Comment', back_populates='parent_post')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(250))
    email = db.Column(String(250), unique=True)
    password = db.Column(String(250))
    posts = relationship('BlogPost', back_populates='author')
    comments = relationship('Comment', back_populates='commenter')


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(Integer, primary_key=True)
    author_id = db.Column(Integer, ForeignKey('users.id'))
    commenter = relationship('User', back_populates='comments')
    post_id = db.Column(Integer, ForeignKey('blog_posts.id'))
    parent_post = relationship('BlogPost', back_populates="comments")
    text = db.Column(Text, nullable=False)
    date = db.Column(String(250), nullable=False)


with app.app_context():
    db.create_all()


@app.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('get_all_posts'))

    if request.method == 'GET':
        session.pop('_flashes', None)

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('This email already exists.', 'error')
            return redirect(url_for('login'))
        hash_password = generate_password_hash(
            form.password.data,
            method='scrypt',
            salt_length=16
        )
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hash_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(url_for('get_all_posts'))
    else:
        if request.method == 'POST':
            flash('Form validation failed. Please check your inputs.', 'error')
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Error in {field}: {error}", 'error')
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('get_all_posts'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('You were successfully logged in', 'success')
            return redirect(url_for('get_all_posts'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        session.clear()
        flash("You have been logged out", 'success')
    return redirect(url_for('login'))


@app.route('/')
def get_all_posts():
    posts = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:post_id>")
def show_post(post_id):
    requested_post = BlogPost.query.get_or_404(post_id)
    comment_form = CommentForm()
    return render_template("post.html", post=requested_post, form=comment_form)


@app.route("/post/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):
    if not current_user.is_authenticated:
        flash("You need to log in to comment.", "error")
        return redirect(url_for("login"))

    post = BlogPost.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        new_comment = Comment(
            text=form.comment_text.data,  # Changed from form.comment.data to form.comment_text.data
            author_id=current_user.id,
            post_id=post.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_comment)
        db.session.commit()
        flash("Comment added successfully!", "success")
    else:
        flash("Comment cannot be empty.", "error")
    return redirect(url_for("show_post", post_id=post.id))


@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    if not current_user.is_authenticated:
        flash("You need to log in to create a post.", "error")
        return redirect(url_for("login"))

    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        flash("Post created successfully!", "success")
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if not current_user.is_authenticated:
        flash("You need to log in to edit a post.", "error")
        return redirect(url_for("login"))

    post = BlogPost.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash("You can only edit your own posts.", "error")
        return redirect(url_for("show_post", post_id=post.id))

    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        flash("Post updated successfully!", "success")
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    if not current_user.is_authenticated:
        flash("You need to log in to delete a post.", "error")
        return redirect(url_for("login"))

    post_to_delete = BlogPost.query.get_or_404(post_id)
    if post_to_delete.author_id != current_user.id:
        flash("You can only delete your own posts.", "error")
        return redirect(url_for("get_all_posts"))

    db.session.delete(post_to_delete)
    db.session.commit()
    flash("Post deleted successfully!", "success")
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["POST", "PUT", "GET"])
def contact():
    if request.method == "POST":
        data = request.form
        print(data["name"])
        print(data["email"])
        print(data["phone"])
        print(data["message"])
        connection = smtplib.SMTP('smtp.gmail.com')
        connection.starttls()
        connection.login(user=my_email, password=my_password)
        connection.sendmail(
            from_addr=my_email,
            to_addrs="rahimjon4753@gmail.com",
            msg=f"Subject:Contact Information\n\nName: {data['name']}\nEmail: {data['email']}\nPhone: {data['phone']}\nMessage: {data['message']}"
        )
        connection.close()
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


if __name__ == "__main__":
    app.run(debug=True, port=5002, use_reloader=False)
