from app import create_app, db
from app.models import TestResult

app = create_app()

with app.app_context():
    tests = TestResult.query.all()
    for test in tests:
        print(f"Test ID: {test.id}")
        print(f"Status: {test.status}")
        print(f"Project: {test.project.name if test.project else 'N/A'}")
        print(f"Created: {test.created_at}")
        print(f"Completed: {test.completed_at}")
        print("---")