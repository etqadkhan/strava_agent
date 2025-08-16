import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class ChatContextManager:
    def __init__(self, storage_dir: str = "./chat_contexts"):
        self.storage_dir = storage_dir
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        """Ensure storage directory exists"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def _get_user_file(self, user_id: str) -> str:
        """Get file path for user's chat context"""
        return os.path.join(self.storage_dir, f"{user_id}_context.json")

    def get_user_context(self, user_id: str) -> Dict:
        """Get user's chat context and preferences"""
        file_path = self._get_user_file(user_id)

        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Return default context
        return {
            "user_id": user_id,
            "preferences": {},
            "chat_history": [],
            "personal_info": {},
            "last_updated": datetime.now().isoformat(),
        }

    def update_user_context(self, user_id: str, updates: Dict):
        """Update user's context with new information"""
        current_context = self.get_user_context(user_id)

        # Update context
        for key, value in updates.items():
            if key == "chat_history":
                # Append to chat history
                if "chat_history" not in current_context:
                    current_context["chat_history"] = []
                current_context["chat_history"].extend(value)
                # Keep only last 50 messages
                current_context["chat_history"] = current_context["chat_history"][-50:]
            elif key == "preferences" or key == "personal_info":
                # Merge dictionaries
                if key not in current_context:
                    current_context[key] = {}
                current_context[key].update(value)
            else:
                current_context[key] = value

        current_context["last_updated"] = datetime.now().isoformat()

        # Save to file
        file_path = self._get_user_file(user_id)
        with open(file_path, "w") as f:
            json.dump(current_context, f, indent=2)

    def add_chat_message(
        self, user_id: str, message: str, response: str, is_user: bool = True
    ):
        """Add a chat message to user's history"""
        chat_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "response": response,
            "is_user": is_user,
        }

        self.update_user_context(user_id, {"chat_history": [chat_entry]})

    def get_chat_summary(self, user_id: str) -> str:
        """Get a summary of user's chat context for LLM"""
        context = self.get_user_context(user_id)

        summary_parts = []

        # Personal info
        if context.get("personal_info"):
            personal = context["personal_info"]
            if personal.get("height") or personal.get("weight") or personal.get("age"):
                summary_parts.append("Personal Information:")
                if personal.get("height"):
                    summary_parts.append(f"- Height: {personal['height']}")
                if personal.get("weight"):
                    summary_parts.append(f"- Weight: {personal['weight']}")
                if personal.get("age"):
                    summary_parts.append(f"- Age: {personal['age']}")
                if personal.get("injuries"):
                    summary_parts.append(f"- Injuries/Health: {personal['injuries']}")
                if personal.get("training_plan"):
                    summary_parts.append(
                        f"- Current Training Plan: {personal['training_plan']}"
                    )

        # Preferences
        if context.get("preferences"):
            prefs = context["preferences"]
            if prefs:
                summary_parts.append("Preferences:")
                for key, value in prefs.items():
                    summary_parts.append(f"- {key}: {value}")

        # Recent chat context (last 5 messages)
        if context.get("chat_history"):
            recent = context["chat_history"][-5:]
            if recent:
                summary_parts.append("Recent Conversation Context:")
                for entry in recent:
                    if entry.get("is_user"):
                        summary_parts.append(f"- You asked: {entry['message']}")
                    else:
                        summary_parts.append(
                            f"- Coach responded: {entry['response'][:100]}..."
                        )

        return (
            "\n".join(summary_parts)
            if summary_parts
            else "No personal context available."
        )

    def ask_for_personal_info(self, user_id: str) -> List[str]:
        """Get list of questions to ask user for personal context"""
        context = self.get_user_context(user_id)
        personal = context.get("personal_info", {})

        questions = []

        if not personal.get("height"):
            questions.append("What's your height? (e.g., 5'10\", 175cm)")
        if not personal.get("weight"):
            questions.append("What's your current weight? (e.g., 70kg, 154lbs)")
        if not personal.get("age"):
            questions.append("What's your age?")
        if not personal.get("injuries"):
            questions.append(
                "Do you have any current injuries or health conditions I should know about?"
            )
        if not personal.get("training_plan"):
            questions.append(
                "What's your current training plan or goal? (e.g., marathon training, general fitness)"
            )

        return questions

    def update_personal_info(self, user_id: str, info_type: str, value: str):
        """Update specific personal information"""
        current_context = self.get_user_context(user_id)
        if "personal_info" not in current_context:
            current_context["personal_info"] = {}

        current_context["personal_info"][info_type] = value
        self.update_user_context(user_id, current_context)

    def clear_chat_history(self, user_id: str):
        """Clear user's chat history"""
        self.update_user_context(user_id, {"chat_history": []})

    def get_all_users(self) -> List[str]:
        """Get list of all user IDs"""
        users = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith("_context.json"):
                user_id = filename.replace("_context.json", "")
                users.append(user_id)
        return users
