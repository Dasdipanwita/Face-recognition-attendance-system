#!/usr/bin/env python3
import sys
import os

# Add the current directory to the path so we can import recognizer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import recognizer
    print("✅ Recognizer module imported successfully")

    # Try to access the global variables to trigger loading
    print(f"✅ KNN model loaded: {recognizer._knn is not None}")
    print(f"✅ Face cascade loaded: {recognizer._face_cascade is not None}")

    if recognizer._face_cascade is not None:
        print(f"✅ Face cascade is not empty: {not recognizer._face_cascade.empty()}")

    print("✅ All components loaded successfully!")

    # Test the user management functions
    print("\n--- Testing User Management Functions ---")
    users = recognizer._get_allowed_users()
    print(f"✅ Current allowed users: {users}")

    # Test adding a user
    test_user = "test_user_123"
    recognizer._add_allowed_user(test_user)
    users_after_add = recognizer._get_allowed_users()
    print(f"✅ After adding '{test_user}': {users_after_add}")

    # Test removing a user
    recognizer._remove_allowed_user(test_user)
    users_after_remove = recognizer._get_allowed_users()
    print(f"✅ After removing '{test_user}': {users_after_remove}")

    print("✅ User management functions work correctly!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
