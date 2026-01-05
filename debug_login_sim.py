import pickle
import os

names_path = 'data/names.pkl'
roles_path = 'data/roles.pkl'

# Simulate login
username = 'admin'
print(f"Attempting to login as: '{username}'")

if os.path.isfile(names_path):
    with open(names_path, 'rb') as f:
        registered_names = list(set(pickle.load(f)))
    print(f"\nTotal registered names (unique): {len(registered_names)}")
    print(f"Last 10 names: {registered_names[-10:]}")
    
    # Check if admin is in the list
    print(f"\n'admin' in registered_names: {'admin' in registered_names}")
    
    # Case-insensitive lookup
    print(f"\nSearching for case-insensitive match for '{username}'...")
    matched_name = None
    for name in registered_names:
        if name.lower().strip() == username.lower().strip():
            matched_name = name
            print(f"  MATCH FOUND: '{name}'")
            break
    
    if not matched_name:
        print(f"  NO MATCH FOUND")
        print(f"\nDebug info:")
        print(f"  username.lower().strip() = '{username.lower().strip()}'")
        lower_set = {n.lower().strip() for n in registered_names}
        print(f"  lower_set contains 'admin': {'admin' in lower_set}")
        print(f"  Sample of lower_set: {list(lower_set)[:10]}")
    else:
        # Check role
        print(f"\nLoading role for '{matched_name}'...")
        if os.path.isfile(roles_path):
            roles = pickle.load(open(roles_path, 'rb'))
            user_role = roles.get(matched_name, 'user')
            print(f"  Role: '{user_role}'")
        else:
            print(f"  roles.pkl not found")
else:
    print("names.pkl not found!")
