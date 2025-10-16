from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, URLField, PasswordField, BooleanField
from wtforms.validators import DataRequired, URL, Length, Optional

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
    submit = SubmitField('Windows Kullanıcısı ile Giriş Yap')