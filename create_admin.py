# -*- coding: utf-8 -*-
"""Create the initial admin user."""
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print('Admin user already exists.')
        admin.is_admin = True
        db.session.commit()
        print('Ensured admin flag is set.')
    else:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully.')
        print(f'  Username: admin')
        print(f'  Password: admin123')
        print(f'  Please change the password after first login!')
