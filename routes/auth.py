import os
from flask import (Blueprint, render_template, redirect,
                   url_for, flash, request, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import User, Student, Company

auth_bp = Blueprint('auth', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}.dashboard'))
    

    return render_template('index.html')


@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html') 
   
        if not user.active:
            flash('Your account has been suspended. Contact admin.', 'danger')
            return render_template('auth/login.html')

        if user.role == 'company':
            company = user.company_profile
            if company.approval_status == 'pending':
                flash('Your registration is pending admin approval.', 'warning')
                return render_template('auth/login.html')
            if company.approval_status == 'rejected':
                flash('Your registration was rejected by admin.', 'danger')
                return render_template('auth/login.html')
        login_user(user)
        flash(f'Welcome back, {user.username}!', 'success')

        return redirect(url_for(f'{user.role}.dashboard'))
    return render_template('auth/login.html')


@auth_bp.route('/register/stuent', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        roll_no = request.form.get('roll_no', '').strip()
        branch = request.form.get('branch', '').strip()
        cgpa = request.form.get('cgpa', '').strip()
        phone = request.form.get('phone', '').strip()
        skills = request.form.get('skills', '').strip()

        if password != confirm:
            flash('Password do not match.', 'danger')
            return render_template('auth/register_student.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register_student.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('auth/register_student.html')
        
        if Student.query.filter_by(roll_no=roll_no).first():
            flash('Roll number already registered.', 'danger')
            return render_template('auth/register_student.html')
    resume_path = None
    if 'resume' in request.files:
        file = request.files['resume']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{roll_no}_{file.filename}")
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            resume_path = filename
            

    try:
        user = User(username = username, email= email , role = 'student')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id= user.id,
            name = name,
            roll_no=roll_no,
            branch=branch,
            cgpa=float(cgpa) if cgpa else None,
            phone=phone,
            skills=skills,
            resume_path = resume_path
        )
        db.session.add(student)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    except Exception as e:
        db.session.rollback()
        flash(f'Registration failed: {e}', 'danger')

    return render_template('auth/register_student.html')


@auth_bp.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}.dashboard'))

    if request.method == 'POST':
        username    = request.form.get('username', '').strip()
        email       = request.form.get('email', '').strip().lower()
        password    = request.form.get('password', '')
        confirm     = request.form.get('confirm_password', '')
        name        = request.form.get('name', '').strip()
        industry    = request.form.get('industry', '').strip()
        website     = request.form.get('website', '').strip()
        description = request.form.get('description', '').strip()
        location    = request.form.get('location', '').strip()

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_company.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register_company.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('auth/register_company.html')

        try:
            user = User(username=username, email=email, role='company')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            company = Company(
                user_id=user.id,
                name=name,
                industry=industry,
                website=website,
                description=description,
                location=location
            )
            db.session.add(company)
            db.session.commit()
            flash('Registration submitted! Awaiting admin approval.', 'info')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {e}', 'danger')

    return render_template('auth/register_company.html')




@auth_bp.route('/logout')
@login_required

def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))












