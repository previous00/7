import json

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app import db
from app.response import response_bp
from app.models import Survey, Question, Response, Answer


@response_bp.route('/<int:survey_id>/fill', methods=['GET', 'POST'])
def fill(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if not survey.is_active():
        flash('该问卷当前不可填写', 'warning')
        return redirect(url_for('survey.list_surveys'))

    questions = survey.questions.order_by(Question.order).all()

    if request.method == 'POST':
        errors = []
        answers_data = []

        for question in questions:
            if question.question_type == 'text':
                text_val = request.form.get(f'question_{question.id}', '').strip()
                if question.required and not text_val:
                    errors.append(f'请回答：{question.question_text}')
                answers_data.append({
                    'question_id': question.id,
                    'answer_text': text_val,
                    'selected_options': None
                })
            elif question.question_type == 'single':
                selected = request.form.get(f'question_{question.id}')
                if question.required and not selected:
                    errors.append(f'请回答：{question.question_text}')
                option_ids = [int(selected)] if selected else []
                answers_data.append({
                    'question_id': question.id,
                    'answer_text': None,
                    'selected_options': json.dumps(option_ids)
                })
            elif question.question_type == 'multiple':
                selected_list = request.form.getlist(f'question_{question.id}')
                if question.required and not selected_list:
                    errors.append(f'请回答：{question.question_text}')
                option_ids = [int(x) for x in selected_list]
                answers_data.append({
                    'question_id': question.id,
                    'answer_text': None,
                    'selected_options': json.dumps(option_ids)
                })

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('response/fill.html', survey=survey, questions=questions)

        response = Response(
            survey_id=survey.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            respondent_ip=request.remote_addr
        )
        db.session.add(response)
        db.session.flush()

        for ans_data in answers_data:
            answer = Answer(
                response_id=response.id,
                question_id=ans_data['question_id'],
                answer_text=ans_data['answer_text'],
                selected_options=ans_data['selected_options']
            )
            db.session.add(answer)

        db.session.commit()
        return redirect(url_for('response.success', survey_id=survey.id))

    return render_template('response/fill.html', survey=survey, questions=questions)


@response_bp.route('/<int:survey_id>/success')
def success(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    return render_template('response/success.html', survey=survey)
