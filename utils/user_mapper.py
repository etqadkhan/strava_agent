from config import USERS
from typing import Optional, Dict, Any


class UserMapper:
    """Maps Telegram chat IDs to usernames and manages user configuration"""

    @staticmethod
    def get_username_by_chat_id(chat_id: str) -> Optional[str]:
        """Get username by Telegram chat ID"""
        try:
            chat_id_int = int(chat_id)
            for username, user_config in USERS.items():
                if user_config.get("chat_id") == chat_id_int:
                    return username
            return None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def get_user_config_by_chat_id(chat_id: str) -> Optional[Dict[str, Any]]:
        """Get user configuration by Telegram chat ID"""
        username = UserMapper.get_username_by_chat_id(chat_id)
        if username:
            return USERS.get(username)
        return None

    @staticmethod
    def get_strava_token_by_chat_id(chat_id: str) -> Optional[str]:
        """Get Strava refresh token by Telegram chat ID"""
        user_config = UserMapper.get_user_config_by_chat_id(chat_id)
        if user_config:
            return user_config.get("strava_refresh_token")
        return None

    @staticmethod
    def get_strava_client_id_by_chat_id(chat_id: str) -> Optional[str]:
        """Get Strava client ID by Telegram chat ID"""
        user_config = UserMapper.get_user_config_by_chat_id(chat_id)
        if user_config:
            return user_config.get("strava_client_id")
        return None

    @staticmethod
    def get_strava_client_secret_by_chat_id(chat_id: str) -> Optional[str]:
        """Get Strava client secret by Telegram chat ID"""
        user_config = UserMapper.get_user_config_by_chat_id(chat_id)
        if user_config:
            return user_config.get("strava_client_secret")
        return None

    @staticmethod
    def list_all_users() -> Dict[str, Dict[str, Any]]:
        """Get all users and their configurations"""
        return USERS.copy()

    @staticmethod
    def is_user_configured(chat_id: str) -> bool:
        """Check if a user is properly configured"""
        user_config = UserMapper.get_user_config_by_chat_id(chat_id)
        if not user_config:
            return False

        # Check if user has both chat_id and strava_refresh_token
        return (
            user_config.get("chat_id") is not None
            and user_config.get("strava_refresh_token") is not None
        )
