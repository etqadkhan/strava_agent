import os
import json
import re
from typing import Optional, Dict, Any


class TokenManager:
    """Manages Strava refresh tokens for multiple users"""

    def __init__(self, env_file_path: str = ".env"):
        self.env_file_path = env_file_path

    def update_refresh_token(self, user_id: str, new_refresh_token: str) -> bool:
        """Update refresh token for a specific user in the .env file"""
        try:
            if not os.path.exists(self.env_file_path):
                print(f"⚠️ .env file not found at {self.env_file_path}")
                return False

            # Read the current .env file
            with open(self.env_file_path, "r") as file:
                content = file.read()

            # Parse the USERS JSON string
            users_match = re.search(r"USERS=({.*})", content, re.DOTALL)
            if not users_match:
                print("⚠️ USERS configuration not found in .env file")
                return False

            try:
                users_json = users_match.group(1)
                users = json.loads(users_json)
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing USERS JSON: {e}")
                return False

            # Update the refresh token for the specific user
            if user_id in users:
                users[user_id]["strava_refresh_token"] = new_refresh_token
                print(f"✅ Updated refresh token for user {user_id}")
            else:
                print(f"⚠️ User {user_id} not found in USERS configuration")
                return False

            # Reconstruct the .env content with updated USERS
            new_users_json = json.dumps(users, separators=(",", ":"))
            new_content = re.sub(
                r"USERS=({.*})", f"USERS={new_users_json}", content, flags=re.DOTALL
            )

            # Write the updated .env file
            with open(self.env_file_path, "w") as file:
                file.write(new_content)

            print(f"✅ Refresh token for user {user_id} saved to .env file")
            return True

        except Exception as e:
            print(f"❌ Error updating refresh token for user {user_id}: {e}")
            return False

    def get_refresh_token(self, user_id: str) -> Optional[str]:
        """Get refresh token for a specific user from the .env file"""
        try:
            if not os.path.exists(self.env_file_path):
                return None

            with open(self.env_file_path, "r") as file:
                content = file.read()

            # Parse the USERS JSON string
            users_match = re.search(r"USERS=({.*})", content, re.DOTALL)
            if not users_match:
                return None

            try:
                users_json = users_match.group(1)
                users = json.loads(users_json)
            except json.JSONDecodeError:
                return None

            if user_id in users:
                return users[user_id].get("strava_refresh_token")

            return None

        except Exception as e:
            print(f"❌ Error reading refresh token for user {user_id}: {e}")
            return None

    def list_users(self) -> Dict[str, Any]:
        """Get all users and their configurations from the .env file"""
        try:
            if not os.path.exists(self.env_file_path):
                return {}

            with open(self.env_file_path, "r") as file:
                content = file.read()

            # Parse the USERS JSON string
            users_match = re.search(r"USERS=({.*})", content, re.DOTALL)
            if not users_match:
                return {}

            try:
                users_json = users_match.group(1)
                return json.loads(users_json)
            except json.JSONDecodeError:
                return {}

        except Exception as e:
            print(f"❌ Error reading users from .env: {e}")
            return {}
