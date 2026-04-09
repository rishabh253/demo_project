from datetime import datetime, timezone
from functools import wraps
from flask import (Blueprint, render_template, redirect,
                   url_for, flash, request)
from flask_login import login_required, current_user
from extensions import db
from models import Company, JobPosition, Application, Student, Notification

company_bp = Blueprint('company', __name__)

def company_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if current_user.role != 'company':
            flash('Company access required.', 'danger')
            return redirect(url_for('auth.login'))
        
        company = current_user.company_profile

        if company.approval_status != 'approved':
            flash('Your account is not yet approved by admin.', 'warning')
            return redirect(url_for('auth.login'))

        if company.is_blacklisted:
            flash('Your company has been blacklisted.', 'danger')
            return redirect(url_for('auth.logout'))

        return f(*args, **kwargs)
    return wrapped

@company_bp.route('/dashboard')
@login_required
@company_required
def dashboard():
    company = current_user.company_profile
    jobs = company.jobs.order_by(JobPosition.created_at.desc()).all()
    total_apps = sum(j.applications.count() for j in jobs)
    active_jobs = company.jobs.filter_by(status='active').count()
    placed = Application.query.join(JobPosition).filter(
                JobPosition.company_id == company.id,
                Application.status == 'placed'
             ).count()
    recent_apps = Application.query.join(JobPosition).filter(JobPosition.company_id == company.id).order_by(Application.applied_at.desc()).limit(10).all()
    return render_template('company/dashboard.html',company=company,jobs=jobs,total_apps=total_apps,active_jobs=active_jobs,placed=placed,recent_apps=recent_apps)

@company_bp.route('/post-job', methods=['GET', 'POST'])
@login_required
@company_required
def post_job():
    company = current_user.company_profile
    if request.method == 'POST':
        title           = request.form.get('title', '').strip()
        description     = request.form.get('description', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        experience      = request.form.get('experience', '').strip()
        salary_min      = request.form.get('salary_min', '').strip()
        salary_max      = request.form.get('salary_max', '').strip()
        location        = request.form.get('location', '').strip()
        deadline_str    = request.form.get('deadline', '').strip()
        if not title:
                flash('Job title is required.', 'danger')
                return render_template('company/post_job.html')
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid deadline format.', 'danger')
                return render_template('company/post_job.html')
        job = JobPosition(
            company_id=company.id,
            title=title,
            description=description,
            required_skills=required_skills,
            experience=experience,
            salary_min=float(salary_min) if salary_min else None,
            salary_max=float(salary_max) if salary_max else None,
            location=location,
            deadline=deadline)
        db.session.add(job)
        db.session.commit()
        flash('Job posted successfully! Awaiting admin approval.', 'success')
        return redirect(url_for('company.dashboard'))
    return render_template('company/post_job.html')  

@company_bp.route('/edit-job/<int:job_id>', methods=['GET', 'POST'])
@login_required
@company_required
def edit_job(job_id):
    company = current_user.company_profile
    job = JobPosition.query.filter_by(id=job_id,company_id=company.id).first_or_404()
    if request.method == 'POST':
        job.title           = request.form.get('title', '').strip()
        job.description     = request.form.get('description', '').strip()
        job.required_skills = request.form.get('required_skills', '').strip()
        job.experience      = request.form.get('experience', '').strip()
        job.location        = request.form.get('location', '').strip()
        job.status          = request.form.get('status', 'active')

        salary_min = request.form.get('salary_min', '').strip()
        salary_max = request.form.get('salary_max', '').strip()
        job.salary_min = float(salary_min) if salary_min else None
        job.salary_max = float(salary_max) if salary_max else None
        deadline_str = request.form.get('deadline', '').strip()
        if deadline_str:
            try:
                job.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid deadline format.', 'danger')
                return render_template('company/edit_job.html', job=job)
        db.session.commit()
        flash('Job updated successfully.', 'success')
        return redirect(url_for('company.dashboard'))
    return render_template('company/edit_job.html', job=job)

@company_bp.route('/job/<int:job_id>/applications')
@login_required
@company_required
def job_applications(job_id):
    company = current_user.company_profile

    job = JobPosition.query.filter_by(id=job_id,company_id=company.id).first_or_404()
    apps = job.applications.order_by(Application.applied_at.desc()).all()
    return render_template('company/job_applications.html',job=job,applications=apps)

@company_bp.route('/application/<int:app_id>/update', methods=['POST'])
@login_required
@company_required
def update_application(app_id):
    company     = current_user.company_profile
    application = Application.query.get_or_404(app_id)
    if application.job.company_id != company.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('company.dashboard'))
    new_status = request.form.get('status')
    notes      = request.form.get('notes', '').strip()
    valid_statuses = ['applied', 'shortlisted', 'interview', 'rejected', 'placed']
    if new_status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('company.job_applications', job_id=application.job_id))
    old_status         = application.status
    application.status = new_status
    application.notes  = notes
    application.updated_at = datetime.now(timezone.utc)
    if old_status != new_status:
        msg = (f'Your application for "{application.job.title}" at '
               f'"{company.name}" has been updated to: {new_status.upper()}.')
        notif = Notification(
            student_id=application.student_id,
            message=msg
        )
        db.session.add(notif)
    db.session.commit()
    flash('Application status updated.', 'success')
    return redirect(url_for('company.job_applications', job_id=application.job_id))


@company_bp.route('/student/<int:student_id>')
@login_required
@company_required
def student_profile(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('company/student_profile.html', student=student)