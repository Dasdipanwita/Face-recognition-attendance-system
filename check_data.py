import pickle
import os

# Check names
with open('data/names.pkl', 'rb') as f:
    names = pickle.load(f)
    print("Registered names:", list(names))

# Check roles
with open('data/roles.pkl', 'rb') as f:
    roles = pickle.load(f)
    print("User roles:", roles)

# Check allowed users in recognizer
import recognizer
print("Allowed users:", recognizer._ALLOWED_USERS)
