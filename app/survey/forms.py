from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class SurveyForm(FlaskForm):
    title = StringField('问卷标题', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('问卷描述', validators=[Optional(), Length(max=2000)])
    start_time = DateTimeLocalField('开始时间', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    end_time = DateTimeLocalField('结束时间', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    submit = SubmitField('保存')
