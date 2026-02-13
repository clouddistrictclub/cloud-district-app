#!/usr/bin/env python3
"""
One-time script to promote specific user to admin
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'cloud_district_club')

def promote_to_admin(email):
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Find user first
        user = db.users.find_one({"email": email})
        
        if not user:
            print(f"❌ User {email} not found in database")
            return False
        
        # Check if already admin
        if user.get("isAdmin", False):
            print(f"✅ User {email} is already an admin")
            return True
        
        # Update user to admin
        result = db.users.update_one(
            {"email": email},
            {"$set": {"isAdmin": True}}
        )
        
        if result.modified_count > 0:
            print(f"✅ Successfully promoted {email} to admin")
            print(f"   - User ID: {user['_id']}")
            print(f"   - Name: {user.get('firstName', '')} {user.get('lastName', '')}")
            return True
        else:
            print(f"❌ Failed to update user")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    email = "jkaatz@gmail.com"
    print(f"Promoting {email} to admin...")
    print("-" * 50)
    promote_to_admin(email)
