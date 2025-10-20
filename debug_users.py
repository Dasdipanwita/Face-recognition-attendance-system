import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

try:
    import pickle

    # Check names
    if os.path.exists('data/names.pkl'):
        with open('data/names.pkl', 'rb') as f:
            names = pickle.load(f)
        print(f"Registered names: {list(names)}")
    else:
        print("ERROR: data/names.pkl not found")

    # Check roles
    if os.path.exists('data/roles.pkl'):
        with open('data/roles.pkl', 'rb') as f:
            roles = pickle.load(f)
        print(f"User roles: {roles}")
    else:
        print("ERROR: data/roles.pkl not found")

    # Check allowed users in recognizer
    try:
        import recognizer
        print(f"Allowed users: {recognizer._ALLOWED_USERS}")
        print(f"All allowed users (including admins): {recognizer._get_allowed_users()}")
    except Exception as e:
        print(f"ERROR importing recognizer: {e}")

except Exception as e:
    print(f"ERROR: {e}")
