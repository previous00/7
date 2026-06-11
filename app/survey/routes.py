from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user

from app import db
from app.survey import survey_bp
from app.survey.forms import SurveyForm
from app.models import Survey, Question, Option


def validate_survey_time(start_time, end_time):
    """Validate start/end time. Returns error message or None."""
    if start_time and start_time < datetime.now():
        return '开始时间不能早于当前时间'
    if start_time and end_time and end_time <= start_time:
        return '结束时间必须晚于开始时间'
    if end_time and not start_time and end_time < datetime.now():
        return '结束时间不能早于当前时间'
    return None


def parse_questions_from_form(form_data):
    questions = []
    i = 0
    while f'questions[{i}][text]' in form_data:
        q_text = form_data.get(f'questions[{i}][text]', '').strip()
        q_type = form_data.get(f'questions[{i}][type]', 'text')
        q_required = f'questions[{i}][required]' in form_data
        options = []
        j = 0
        while f'questions[{i}][options][{j}]' in form_data:
            opt_text = form_data.get(f'questions[{i}][options][{j}]', '').strip()
            if opt_text:
                options.append(opt_text)
            j += 1
        if q_text:
            questions.append({
                'text': q_text,
                'type': q_type,
                'required': q_required,
                'options': options
            })
        i += 1
    return questions


@survey_bp.route('/list')
def list_surveys():
    page = request.args.get('page', 1, type=int)
    pagination = Survey.query.filter_by(status='published') \
        .order_by(Survey.created_at.desc()) \
        .paginate(page=page, per_page=current_app.config['SURVEYS_PER_PAGE'], error_out=False)
    return render_template('survey/list.html', pagination=pagination, surveys=pagination.items)


@survey_bp.route('/my')
@login_required
def my_surveys():
    page = request.args.get('page', 1, type=int)
    pagination = Survey.query.filter_by(user_id=current_user.id) \
        .order_by(Survey.created_at.desc()) \
        .paginate(page=page, per_page=current_app.config['SURVEYS_PER_PAGE'], error_out=False)
    return render_template('survey/my_surveys.html', pagination=pagination, surveys=pagination.items)


@survey_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = SurveyForm()
    if form.validate_on_submit():
        time_error = validate_survey_time(form.start_time.data, form.end_time.data)
        if time_error:
            flash(time_error, 'danger')
            return render_template('survey/create.html', form=form)

        questions_data = parse_questions_from_form(request.form)
        if not questions_data:
            flash('请至少添加一个题目', 'warning')
            return render_template('survey/create.html', form=form)

        survey = Survey(
            title=form.title.data,
            description=form.description.data,
            user_id=current_user.id,
            start_time=form.start_time.data,
            end_time=form.end_time.data
        )
        db.session.add(survey)
        db.session.flush()

        for idx, q_data in enumerate(questions_data):
            question = Question(
                survey_id=survey.id,
                question_text=q_data['text'],
                question_type=q_data['type'],
                order=idx,
                required=q_data['required']
            )
            db.session.add(question)
            db.session.flush()

            if q_data['type'] in ('single', 'multiple'):
                for opt_idx, opt_text in enumerate(q_data['options']):
                    option = Option(
                        question_id=question.id,
                        option_text=opt_text,
                        order=opt_idx
                    )
                    db.session.add(option)

        db.session.commit()
        flash('问卷创建成功', 'success')
        return redirect(url_for('survey.my_surveys'))
    return render_template('survey/create.html', form=form)


@survey_bp.route('/<int:survey_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.user_id != current_user.id:
        abort(403)
    if survey.status != 'draft':
        flash('只能编辑草稿状态的问卷', 'warning')
        return redirect(url_for('survey.my_surveys'))

    form = SurveyForm(obj=survey)
    if form.validate_on_submit():
        time_error = validate_survey_time(form.start_time.data, form.end_time.data)
        if time_error:
            flash(time_error, 'danger')
            return render_template('survey/edit.html', form=form, survey=survey)

        questions_data = parse_questions_from_form(request.form)
        if not questions_data:
            flash('请至少添加一个题目', 'warning')
            return render_template('survey/edit.html', form=form, survey=survey)

        survey.title = form.title.data
        survey.description = form.description.data
        survey.start_time = form.start_time.data
        survey.end_time = form.end_time.data

        # Delete old questions and recreate
        Question.query.filter_by(survey_id=survey.id).delete()
        db.session.flush()

        for idx, q_data in enumerate(questions_data):
            question = Question(
                survey_id=survey.id,
                question_text=q_data['text'],
                question_type=q_data['type'],
                order=idx,
                required=q_data['required']
            )
            db.session.add(question)
            db.session.flush()

            if q_data['type'] in ('single', 'multiple'):
                for opt_idx, opt_text in enumerate(q_data['options']):
                    option = Option(
                        question_id=question.id,
                        option_text=opt_text,
                        order=opt_idx
                    )
                    db.session.add(option)

        db.session.commit()
        flash('问卷已更新', 'success')
        return redirect(url_for('survey.my_surveys'))

    return render_template('survey/edit.html', form=form, survey=survey)


@survey_bp.route('/<int:survey_id>/delete', methods=['POST'])
@login_required
def delete(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.user_id != current_user.id:
        abort(403)
    db.session.delete(survey)
    db.session.commit()
    flash('问卷已删除', 'success')
    return redirect(url_for('survey.my_surveys'))


@survey_bp.route('/<int:survey_id>/publish', methods=['POST'])
@login_required
def publish(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.user_id != current_user.id:
        abort(403)
    if survey.questions.count() == 0:
        flash('问卷至少需要一个题目才能发布', 'warning')
        return redirect(url_for('survey.my_surveys'))
    survey.status = 'published'
    db.session.commit()
    flash('问卷已发布', 'success')
    return redirect(url_for('survey.my_surveys'))


@survey_bp.route('/<int:survey_id>/close', methods=['POST'])
@login_required
def close(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.user_id != current_user.id:
        abort(403)
    survey.status = 'closed'
    db.session.commit()
    flash('问卷已关闭', 'success')
    return redirect(url_for('survey.my_surveys'))
