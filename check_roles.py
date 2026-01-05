import pickle
import os

data_dir = 'data'
roles_path = os.path.join(data_dir, 'roles.pkl')

print("\n--- roles.pkl ---")
if os.path.exists(roles_path):
    try:
        with open(roles_path, 'rb') as f:
            roles = pickle.load(f)
            print(roles)
    except Exception as e:
        print(f"Error reading roles.pkl: {e}")
else:
    print("roles.pkl does not exist")
