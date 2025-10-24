from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, URLField, PasswordField, BooleanField
from wtforms.validators import DataRequired, URL, Length, Optional, Email, EqualTo, ValidationError

class ProjectForm(FlaskForm):
    name = StringField('Proje Adı', validators=[DataRequired(), Length(min=1, max=200)])
    url = StringField('Proje URL\'si', validators=[DataRequired(), URL()])
    description = TextAreaField('Açıklama', validators=[Length(max=500)])
    
    # Login bilgileri
    login_enabled = BooleanField('Bu proje için login gerekli')
    login_username = StringField('Kullanıcı Adı', validators=[Optional(), Length(max=200)],
                                render_kw={'placeholder': 'örn: kullanici@domain.com'})
    login_password = PasswordField('Şifre', validators=[Optional(), Length(max=200)],
                                  render_kw={'placeholder': 'Şifrenizi girin'})
    
    submit = SubmitField('Kaydet')

class TestPromptForm(FlaskForm):
    name = StringField('Prompt Adı', validators=[DataRequired(), Length(min=1, max=200)])
    content = TextAreaField('Prompt İçeriği', validators=[DataRequired()], 
                           render_kw={"rows": 10, "placeholder": "Test senaryonuz için prompt içeriğini buraya yazın..."})
    submit = SubmitField('Kaydet')

class RunTestForm(FlaskForm):
    project_id = SelectField('Proje', coerce=int, validators=[DataRequired()], choices=[])
    prompt_id = SelectField('Test Promptu', coerce=int, validators=[DataRequired()], choices=[])
    submit = SubmitField('Testi Çalıştır')

class RunSingleTestForm(FlaskForm):
    project_url = URLField('Proje URL', validators=[DataRequired(), URL()], 
                          render_kw={'placeholder': 'https://example.com'})
    submit = SubmitField('Testi Çalıştır')

class LoginForm(FlaskForm):
    username_or_email = StringField('Kullanıcı Adı veya Email', 
                                   validators=[DataRequired()],
                                   render_kw={'placeholder': 'kullanici@email.com veya kullaniciadi'})
    password = PasswordField('Şifre', 
                           validators=[DataRequired()],
                           render_kw={'placeholder': 'Şifrenizi girin'})
    remember_me = BooleanField('Beni hatırla')
    submit = SubmitField('Giriş Yap')

class RegisterForm(FlaskForm):
    username = StringField('Kullanıcı Adı', 
                          validators=[DataRequired(), Length(min=3, max=80)],
                          render_kw={'placeholder': 'Kullanıcı adınızı girin'})
    email = StringField('Email', 
                       validators=[DataRequired(), Email(), Length(min=6, max=120)],
                       render_kw={'placeholder': 'email@example.com'})
    password = PasswordField('Şifre', 
                           validators=[DataRequired(), Length(min=6, max=50)],
                           render_kw={'placeholder': 'En az 6 karakter'})
    confirm_password = PasswordField('Şifre Tekrar', 
                                   validators=[DataRequired(), EqualTo('password', message='Şifreler eşleşmiyor!')],
                                   render_kw={'placeholder': 'Şifrenizi tekrar girin'})
    submit = SubmitField('Kayıt Ol')

class UserProfileForm(FlaskForm):
    username = StringField('Kullanıcı Adı', 
                          validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', 
                       validators=[DataRequired(), Length(min=6, max=120)])
    current_password = PasswordField('Mevcut Şifre', 
                                   validators=[Optional()],
                                   render_kw={'placeholder': 'Şifre değiştirmek için gerekli'})
    new_password = PasswordField('Yeni Şifre', 
                               validators=[Optional(), Length(min=6, max=50)],
                               render_kw={'placeholder': 'Boş bırakılırsa değişmez'})
    confirm_new_password = PasswordField('Yeni Şifre Tekrar', 
                                       validators=[Optional()],
                                       render_kw={'placeholder': 'Yeni şifreyi tekrar girin'})
    submit = SubmitField('Güncelle')