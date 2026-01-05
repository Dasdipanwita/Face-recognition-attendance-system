import os
import pickle

BASE = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE, 'data')

os.makedirs(DATA_DIR, exist_ok=True)

names_path = os.path.join(DATA_DIR, 'names.pkl')
roles_path = os.path.join(DATA_DIR, 'roles.pkl')

# Ensure names.pkl contains 'demo'
names = []
if os.path.isfile(names_path):
    try:
        with open(names_path, 'rb') as f:
            names = pickle.load(f)
    except Exception as e:
        print('Could not load existing names.pkl:', e)

if 'demo' not in names:
    names.append('demo')
    with open(names_path, 'wb') as f:
        pickle.dump(names, f)
    print('Added "demo" to names.pkl')
else:
    print('"demo" already present in names.pkl')

# Ensure roles.pkl maps 'demo' -> 'admin'
roles = {}
if os.path.isfile(roles_path):
    try:
        with open(roles_path, 'rb') as f:
            roles = pickle.load(f)
    except Exception as e:
        print('Could not load existing roles.pkl:', e)

if roles.get('demo') != 'admin':
    roles['demo'] = 'admin'
    with open(roles_path, 'wb') as f:
        pickle.dump(roles, f)
    print('Set role of "demo" to admin in roles.pkl')
else:
    print('"demo" already has admin role in roles.pkl')

print('Done')
