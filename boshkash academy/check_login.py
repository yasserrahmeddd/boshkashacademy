try:
    import flask_login
    print(f"Flask-Login imported OK. Version: {flask_login.__version__}")
except ImportError as e:
    print(f"Flask-Login import FAILED: {e}")
except Exception as e:
    print(f"Flask-Login ERROR: {e}")
