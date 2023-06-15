from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Select, update, Delete, create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship, Session
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CreateUserForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

engine = create_engine('sqlite:///blog.db')
login_mgr = LoginManager(app=app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id          = Column(Integer,       primary_key=True)
    name        = Column(String(100),   nullable=False)
    email       = Column(String(100),   nullable=False)
    password    = Column(String(256),   nullable=False)
    posts       = relationship('BlogPost',  back_populates='author')
    comments    = relationship('Comment',   back_populates='commenter')

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id          = db.Column(Integer,        primary_key=True) 
    title       = db.Column(String(250),    unique=True,        nullable=False)
    subtitle    = db.Column(String(250),    nullable=False)
    date        = db.Column(String(250),    nullable=False)
    body        = db.Column(Text,           nullable=False)
    img_url     = db.Column(String(250),    nullable=False)
    author_id   = db.Column(String(250),    ForeignKey('users.id'))
    author      = relationship('User',      back_populates='posts')
    comments    = relationship('Comment',   back_populates='blog')

class Comment(db.Model):
    __tablename__ = "comments"
    id              = Column(Integer,       primary_key=True)
    comment         = Column(String(500),   nullable=False)
    commenter_id    = Column(Integer,       ForeignKey("users.id"))
    commenter       = relationship('User',  back_populates='comments')
    blog_id         = Column(Integer,       ForeignKey("blog_posts.id"))
    blog            = relationship('BlogPost', back_populates='comments')

with app.app_context():
    db.create_all()
# db.session.commit()


@login_mgr.user_loader
def load_user(user_id):
    with Session(engine) as session:
        query = Select(User).where(User.id == user_id)
        user = session.scalars(query).first()
        return user


@app.route('/')
def get_all_posts():
    with Session(engine) as session:
        query = Select(BlogPost)
        posts = session.scalars(query).fetchall()
        return render_template("index.html", all_posts=posts)


@app.route('/register', methods = ["POST", "GET"])
def register():
    form = CreateUserForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        hash = generate_password_hash(password=password, method="pbkdf2", salt_length=16)
        with Session(engine) as session:
            query = Select(User).where(User.email == email)
            result = session.scalars(query).first()
            if result:
                flash ("That email is already registered. Try logging in.", "error")
                return redirect(url_for('login'))
            else:
                new_user = User(email = email, password = hash, name=name)
                session.add(new_user)
                session.commit()
                login_user(new_user)
                return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods = ["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        with Session(engine) as session:
            query = Select(User).where(User.email == email)
            user = session.scalars(query).first()
            if user:
                hash = generate_password_hash(password=password, method="pbkdf2", salt_length=16)
                print (password)
                print (user.password)
                print (hash)
                if check_password_hash(password=password, pwhash=user.password):
                    login_user(user)
                    return redirect(url_for('get_all_posts'))
                else:
                    flash("Wrong password", "error")
            else:
                flash ("Invalid email", "error")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

@login_required
@app.route("/post/<int:post_id>", methods = ["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    with Session(engine) as session:
        query = Select(BlogPost).where(BlogPost.id == post_id)
        post = session.scalars(query).first()
        query = Select(Comment).where(Comment.blog_id == post_id)
        comments = session.scalars(query).all()
        if form.validate_on_submit():
            comment = form.comment.data
            new_comment = Comment(comment=comment,
                                    commenter_id =current_user.id,
                                    blog_id =post_id)
            session.add(new_comment)
            session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        return render_template("post.html", post=post, comments=comments, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@login_required
@app.route("/new-post", methods = ["POST", "GET"])
def add_new_post():
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
        with Session(engine) as session:
            session.add(new_post)
            session.commit()
            return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@login_required
@app.route("/edit-post/<int:post_id>", methods = ["POST", "GET"])
def edit_post(post_id):
    with Session(engine) as session:
        query = Select(BlogPost).where(BlogPost.id == post_id)
        post = session.scalars(query).first()
        edit_form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.img_url,
            body=post.body
        )
        if edit_form.validate_on_submit():
                query = update(BlogPost).where(BlogPost.id ==post_id).values(
                                                                    title = edit_form.title.data,
                                                                    subtitle = edit_form.subtitle.data,
                                                                    img_url = edit_form.img_url.data,
                                                                    body = edit_form.body.data)
                session.execute(query)
                session.commit()
                return redirect(url_for("show_post", post_id=post.id))

        return render_template("make-post.html", form=edit_form)


@login_required
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    with Session(engine) as session:
        query = Delete(BlogPost).where(BlogPost.id ==post_id)
        session.execute(query)
        session.commit()
        return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
