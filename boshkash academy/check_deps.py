try:
    from werkzeug.security import generate_password_hash, check_password_hash
    print("Werkzeug security import OK")
except ImportError as e:
    print(f"Werkzeug security import FAILED: {e}")

try:
    import flask
    print(f"Flask version: {flask.__version__}")
except ImportError as e:
    print(f"Flask import FAILED: {e}")
