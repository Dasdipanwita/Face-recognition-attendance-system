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

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
