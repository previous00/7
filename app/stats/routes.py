import csv
import io
import json

from flask import render_template, request, abort, send_file, make_response
from flask_login import login_required, current_user
from openpyxl import Workbook

from app.stats import stats_bp
from app.models import Survey, Question, Answer, Response, Option, User


@stats_bp.route('/<int:survey_id>/view')
@login_required
def view(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    total_responses = survey.responses.count()
    questions = survey.questions.order_by(Question.order).all()
    stats = []

    for question in questions:
        answers = Answer.query.filter_by(question_id=question.id).all()
        q_stat = {
            'question': question,
            'type': question.question_type,
            'total': len(answers)
        }

        if question.question_type == 'text':
            q_stat['texts'] = [a.answer_text for a in answers if a.answer_text]
        else:
            option_counts = {}
            for opt in question.options:
                option_counts[opt.id] = {'text': opt.option_text, 'count': 0}

            for a in answers:
                if a.selected_options:
                    for opt_id in json.loads(a.selected_options):
                        if opt_id in option_counts:
                            option_counts[opt_id]['count'] += 1

            q_stat['option_counts'] = option_counts

        stats.append(q_stat)

    return render_template('stats/view.html', survey=survey,
                           total_responses=total_responses, stats=stats)


@stats_bp.route('/<int:survey_id>/export')
@login_required
def export(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    fmt = request.args.get('format', 'csv')
    questions = survey.questions.order_by(Question.order).all()
    responses = survey.responses.order_by(Response.created_at).all()

    headers = ['序号', '提交时间', '填写者']
    for q in questions:
        headers.append(q.question_text)

    rows = [headers]
    for idx, resp in enumerate(responses, 1):
        if resp.user_id:
            user = User.query.get(resp.user_id)
            respondent = user.username if user else '未知'
        else:
            respondent = '匿名'

        row = [idx, resp.created_at.strftime('%Y-%m-%d %H:%M:%S'), respondent]

        for q in questions:
            answer = Answer.query.filter_by(response_id=resp.id, question_id=q.id).first()
            if not answer:
                row.append('')
            elif q.question_type == 'text':
                row.append(answer.answer_text or '')
            else:
                if answer.selected_options:
                    option_ids = json.loads(answer.selected_options)
                    option_texts = []
                    for oid in option_ids:
                        opt = Option.query.get(oid)
                        if opt:
                            option_texts.append(opt.option_text)
                    row.append('; '.join(option_texts))
                else:
                    row.append('')
        rows.append(row)

    if fmt == 'xlsx':
        wb = Workbook()
        ws = wb.active
        ws.title = '问卷结果'
        for row in rows:
            ws.append(row)
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name=f'{survey.title}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        for row in rows:
            writer.writerow(row)
        resp = make_response(output.getvalue())
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        resp.headers['Content-Disposition'] = f'attachment; filename={survey.title}.csv'
        return resp
