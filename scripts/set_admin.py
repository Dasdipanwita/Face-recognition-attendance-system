import os
import json
import pickle
import argparse
from werkzeug.security import generate_password_hash

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT, 'data')
CONFIG_DIR = os.path.join(ROOT, 'config')
ADMIN_FILE = os.path.join(CONFIG_DIR, 'admin_credentials.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

def load_admins():
    if os.path.exists(ADMIN_FILE):
        try:
            with open(ADMIN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'admins': {}}
    return {'admins': {}}

def save_admins(data):
    with open(ADMIN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def ensure_name_and_role(username):
    roles_path = os.path.join(DATA_DIR, 'roles.pkl')

    # roles.pkl
    roles = {}
    if os.path.exists(roles_path):
        try:
            with open(roles_path, 'rb') as f:
                roles = pickle.load(f)
        except Exception:
            roles = {}
    roles[username] = 'admin'
    with open(roles_path, 'wb') as f:
        pickle.dump(roles, f)

def main():
    parser = argparse.ArgumentParser(description='Create or update an admin user for the face-attendance app')
    parser.add_argument('--username', '-u', required=True, help='Admin username')
    parser.add_argument('--password', '-p', required=True, help='Admin password')
    args = parser.parse_args()

    data = load_admins()
    pw_hash = generate_password_hash(args.password)
    data.setdefault('admins', {})
    data['admins'][args.username] = {
        'password_hash': pw_hash,
        'last_updated': ''
    }
    save_admins(data)
    ensure_name_and_role(args.username)
    print(f"Admin '{args.username}' created/updated. Restart the app and log in with the new credentials.")

if __name__ == '__main__':
    main()
