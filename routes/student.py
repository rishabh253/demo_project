import os
from functools import wraps
from flask import (Blueprint, render_template, redirect, url_for, flash, request, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import Student, JobPosition, Application, Company, Notification

student_bp = Blueprint('student', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def student_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('auth.login'))
        if not current_user.active:
            flash('Your account has been suspended.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return wrapped


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student = current_user.student_profile
    applications = student.applications.order_by(Application.applied_at.desc()).limit(5).all()
    notifications = student.notifications.filter_by(is_read=False)\
        .order_by(Notification.created_at.desc()).all()
    
    for n in notifications:
        n.is_read = True
    db.session.commit()
    stats = {
        'total':       student.applications.count(),
        'shortlisted': student.applications.filter_by(status='shortlisted').count(),
        'placed':      student.applications.filter_by(status='placed').count(),
        'rejected':    student.applications.filter_by(status='rejected').count(),
    }
    return render_template('student/dashboard.html',student=student,applications=applications,notifications=notifications,stats=stats)

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@student_required
def profile():
    student = current_user.student_profile
    if request.method == 'POST':
        student.name     = request.form.get('name', '').strip()
        student.branch   = request.form.get('branch', '').strip()
        student.phone    = request.form.get('phone', '').strip()
        student.skills   = request.form.get('skills', '').strip()
        student.linkedin = request.form.get('linkedin', '').strip()
        student.about    = request.form.get('about', '').strip()
        cgpa = request.form.get('cgpa', '').strip()
        student.cgpa = float(cgpa) if cgpa else None
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and allowed_file(file.filename):
                filename  = secure_filename(f"{student.roll_no}_{file.filename}")
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                student.resume_path = filename
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student.profile'))
    return render_template('student/profile.html', student=student)



@student_bp.route('/jobs')
@login_required
@student_required
def jobs():
    search    = request.args.get('search', '').strip()
    skill_f   = request.args.get('skill', '').strip()
    company_f = request.args.get('company', '').strip()

    query = JobPosition.query.join(Company).filter(JobPosition.is_approved == True,JobPosition.status == 'active',Company.approval_status == 'approved',Company.is_blacklisted == False)
    if search:
        query = query.filter(
            db.or_(JobPosition.title.ilike(f'%{search}%'),
                   JobPosition.description.ilike(f'%{search}%')))
    if skill_f:
        query = query.filter(
            JobPosition.required_skills.ilike(f'%{skill_f}%'))
    if company_f:
        query = query.filter(
            Company.name.ilike(f'%{company_f}%'))
    jobs = query.order_by(JobPosition.created_at.desc()).all()
    student     = current_user.student_profile
    applied_ids = {a.job_id for a in student.applications.all()}
    return render_template('student/jobs.html',jobs=jobs,search=search,skill_f=skill_f,company_f=company_f,applied_ids=applied_ids)


@student_bp.route('/job/<int:job_id>')
@login_required
@student_required
def job_detail(job_id):
    job     = JobPosition.query.get_or_404(job_id)
    student = current_user.student_profile
    already_applied = Application.query.filter_by(
                        student_id=student.id,
                        job_id=job_id
                      ).first() is not None
    return render_template('student/job_detail.html',
                           job=job,
                           already_applied=already_applied)

@student_bp.route('/job/<int:job_id>/apply', methods=['POST'])
@login_required
@student_required
def apply_job(job_id):
    student = current_user.student_profile
    job     = JobPosition.query.get_or_404(job_id)
    if not job.is_approved or job.status != 'active':
        flash('This job is not available.', 'danger')
        return redirect(url_for('student.jobs'))
    existing = Application.query.filter_by(
                 student_id=student.id,
                 job_id=job_id
               ).first()
    if existing:
        flash('You have already applied for this job.', 'warning')
        return redirect(url_for('student.my_applications'))
    application = Application(student_id=student.id, job_id=job_id)
    db.session.add(application)
    db.session.commit()
    flash(f'Successfully applied for "{job.title}"!', 'success')
    return redirect(url_for('student.my_applications'))

@student_bp.route('/my-applications')
@login_required
@student_required
def my_applications():
    student      = current_user.student_profile
    applications = student.applications.order_by(
                    Application.applied_at.desc()).all()
    return render_template('student/my_applications.html',student=student,applications=applications)




