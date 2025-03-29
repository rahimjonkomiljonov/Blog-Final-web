# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, URL, Length
from flask_ckeditor import CKEditorField

class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=250)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=250)])
    password = PasswordField('Create password', validators=[DataRequired(), Length(min=6, max=250)])
    sign_up = SubmitField('Sign me up!')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=250)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=250)])
    login = SubmitField('Let me in.')

class CommentForm(FlaskForm):
    comment_text = StringField('Comment', validators=[DataRequired()])
    submit = SubmitField('Submit Comment')