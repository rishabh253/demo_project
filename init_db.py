from app import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    db.create_all()
    print("All tables created successfully.")

    if not User.query.filter_by(role='admin').first():
        admin = User(
            username='admin',
            email='admin@placement.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
        print("Email    : admin@placement.com")
        print("Password : admin123")
    else:
        print("Admin already exists.")