import pickle
import os

# Mocking the environment
base_dir = os.path.dirname(os.path.abspath(__file__))
names_path = os.path.join(base_dir, 'data', 'names.pkl')
roles_path = os.path.join(base_dir, 'data', 'roles.pkl')

username = "admin"

print(f"Testing login logic for username: '{username}'")

if os.path.isfile(names_path):
    with open(names_path, 'rb') as f:
        registered_names = list(set(pickle.load(f)))
else:
    registered_names = []

print(f"Registered names count: {len(registered_names)}")
print(f"'admin' in registered_names: {'admin' in registered_names}")

# Case-insensitive username lookup
matched_name = None
for name in registered_names:
    try:
        if name.lower().strip() == username.lower().strip():
            matched_name = name
            print(f"[LOGIN DEBUG] matched_name='{matched_name}'")
            break
    except Exception:
        continue

print(f"After names check, matched_name: {matched_name}")

# If not found in names.pkl, check if it's an admin in roles.pkl
if not matched_name and os.path.isfile(roles_path):
    try:
        with open(roles_path, 'rb') as f:
            roles = pickle.load(f)
            print(f"[LOGIN DEBUG] Checking roles.pkl for admin user '{username}'")
            for role_name, role_value in roles.items():
                # print(f"[LOGIN DEBUG] Checking role: {role_name} -> {role_value}")
                if str(role_name).lower().strip() == username.lower().strip() and str(role_value) == 'admin':
                    matched_name = role_name
                    print(f"[LOGIN DEBUG] matched_name (from roles)='{matched_name}'")
                    break
    except Exception as e:
        print(f"[LOGIN DEBUG] Error reading roles.pkl: {e}")
        pass

print(f"Final matched_name: {matched_name}")

if matched_name:
    print("SUCCESS: User found")
else:
    print("FAILURE: User not registered")
