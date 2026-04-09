from flask import (Blueprint, render_template, redirect,
                   url_for, flash, request)
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import User, Student, Company, JobPosition, Application

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login first.', 'danger')
            return redirect(url_for('auth.login'))
        
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    stats = {
        'total_companies': Company.query.count(),
        'pending_companies': Company.query.filter_by(approval_status='pending').count(),
        'approved_companies': Company.query.filter_by(approval_status='approved').count(),
        'total_students': Student.query.count(),
        'total_jobs': JobPosition.query.count(),
        'pending_job': JobPosition.query.filter_by(is_approved=False).count(),
        'total_applications': Application.query.count(),
        'placed_students': Application.query.filter_by(status='placed').count(),
    }
    recent_companies = Company.query.order_by(Company.created_at.desc()).limit(5).all()

    recent_jobs = JobPosition.query.order_by(JobPosition.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html', stats = stats, recent_companies = recent_companies, recent_jobs = recent_jobs)


@admin_bp.route('/companies')
@login_required
@admin_required
def companies():
    search = request.args.get('search', '').strip()

    query = Company.query

    if search:

        query = query.filter(
            db.or_(Company.name.ilike(f'%{search}%')), Company.industry.ilike(f'%{search}%')
        )

    companies = query.order_by(Company.created_at.desc()).all()
    return render_template('admin/companies.html', companies=companies, search=search)


@admin_bp.route('/company/<int:company_id>')
@login_required
@admin_required
def company_detail(company_id):
    company = Company.query.get_or_404(company_id)
    jobs = company.jobs.order_by(JobPosition.created_at.desc()).all()
    return render_template('admin/company_detail.html', company=company, jobs=jobs)

@admin_bp.route('/company/<int:company_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'approved'

    db.session.commit()

    flash(f'Company "{company.name}" has been approved.', 'success')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/company/<int:company_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'rejected'
    db.session.commit()
    flash(f'Company "{company.name}" has been rejected.', 'warning')
    return redirect(url_for('admin.companies'))

@admin_bp.route('/company/<int:company_id>/blacklist', methods=['POST'])
@login_required
@admin_required
def blacklist_company(company_id):
    company = Company.query.get_or_404(company_id)

    company.is_blacklisted = not company.is_blacklisted

    company.user.active = not company.is_blacklisted

    db.session.commit()
    state = 'blacklisted' if company.is_blacklisted else 'un-blacklisted'
    flash(f'Company "{company.name}" has been {state}.', 'info')
    return redirect(url_for('admin.companies'))

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    search = request.args.get('search', '').strip()
    query = Student.query
    
    if search:
        query = query.filter(
            db.or_(Student.name.ilike(f'%{search}%'),
            Student.roll_no.ilike(f'%{search}%'),
            Student.phone.ilike(f'%{search}%')
            )
        )
    students= query.order_by(Student.name).all()
    return render_template('admin/students.html',
                           students=students,
                           search=search)

@admin_bp.route('/student/<int:student_id>')
@login_required
@admin_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    applications = student.applications.order_by(Application.applied_at.desc()).all()
    return render_template('admin/studet_detail.html',
                           student=student,
                           applicatios=applications)

@admin_bp.route('/student/<int:student_id>/blacklist', methods=['POST'])
@login_required
@admin_required
def blacklist_student(student_id):
    student = Student.query.get_or_404(student_id)

    state = 'deactivated' if not student.user.active else 'activated'
    flash(f'Student "{student.name}" has been {state}.', 'info')
    return redirect(url_for(('admin.students')))

@admin_bp.route('/jobs')
@login_required
@admin_required
def jobs():
    jobs = JobPosition.query.order_by(JobPosition.created_at.desc()).all()
    return render_template('admin/jobs.html', jobs = jobs)

@admin_bp.route('/job/<int:job_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_job(job_id):
    job = JobPosition.query.get_or_404(job_id)
    job.is_approved = True
    db.session.commit()
    flash(f'Job "{job.title}" has been approved.', 'success')
    return redirect(url_for('admin.jobs'))

@admin_bp.route('/job/<int:job_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_job(job_id):
    job = JobPosition.query.get_or_404(job_id)
    job.is_approved = False
    job.status = 'closed'
    db.session.commit()
    flash(f'Job "{job.title}" has been rejected.', 'warning')
    return redirect(url_for('admin.jobs'))


@admin_bp.route('/applications')
@login_required
@admin_required
def applications():
    applications = Application.query.order_by(Application.applied_at.desc()).all()
    return render_template('admin/applications.html', applications = applications)







