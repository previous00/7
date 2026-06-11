from functools import wraps

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app import db
from app.admin import admin_bp
from app.models import User, Survey, Response, Answer, Question


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_required
def dashboard():
    user_count = User.query.count()
    survey_count = Survey.query.count()
    response_count = Response.query.count()
    return render_template('admin/dashboard.html',
                           user_count=user_count,
                           survey_count=survey_count,
                           response_count=response_count)


@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    pagination = User.query.order_by(User.created_at.desc()) \
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', pagination=pagination, users=pagination.items)


@admin_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能修改自己的管理员状态', 'warning')
        return redirect(url_for('admin.users'))
    user.is_admin = not user.is_admin
    db.session.commit()
    status = '管理员' if user.is_admin else '普通用户'
    flash(f'已将 {user.username} 设为{status}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能删除自己的账号', 'warning')
        return redirect(url_for('admin.users'))
    # Delete user's surveys (cascades to questions, options, responses, answers)
    for survey in user.surveys.all():
        db.session.delete(survey)
    db.session.delete(user)
    db.session.commit()
    flash(f'已删除用户 {user.username}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/surveys')
@admin_required
def surveys():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Survey.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    pagination = query.order_by(Survey.created_at.desc()) \
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/surveys.html', pagination=pagination,
                           surveys=pagination.items, status_filter=status_filter)


@admin_bp.route('/surveys/<int:survey_id>/delete', methods=['POST'])
@admin_required
def delete_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    title = survey.title
    db.session.delete(survey)
    db.session.commit()
    flash(f'已删除问卷「{title}」', 'success')
    return redirect(url_for('admin.surveys'))


@admin_bp.route('/surveys/<int:survey_id>/close', methods=['POST'])
@admin_required
def close_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    survey.status = 'closed'
    db.session.commit()
    flash(f'已关闭问卷「{survey.title}」', 'success')
    return redirect(url_for('admin.surveys'))


@admin_bp.route('/surveys/<int:survey_id>/publish', methods=['POST'])
@admin_required
def publish_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if survey.questions.count() == 0:
        flash('该问卷没有题目，无法发布', 'warning')
        return redirect(url_for('admin.surveys'))
    survey.status = 'published'
    db.session.commit()
    flash(f'已发布问卷「{survey.title}」', 'success')
    return redirect(url_for('admin.surveys'))
