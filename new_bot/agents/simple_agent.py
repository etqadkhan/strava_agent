import re
from typing import Dict, Any


class SimpleAgent:
    """Simple agent to handle basic greetings and non-fitness questions"""

    def __init__(self):
        # Define patterns for simple greetings and non-fitness questions
        self.greeting_patterns = [
            r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b",
            r"\b(how are you|how\'s it going|what\'s up)\b",
            r"\b(thanks|thank you|thx)\b",
            r"\b(bye|goodbye|see you)\b",
            r"\b(yes|no|ok|okay|sure)\b",
        ]

        # Define patterns for non-fitness questions
        self.non_fitness_patterns = [
            r"\b(weather|temperature|rain|sunny)\b",
            r"\b(time|date|day|week)\b",
            r"\b(joke|funny|humor)\b",
            r"\b(help|support|assist)\b",
            r"\b(what can you do|capabilities|features)\b",
        ]

        # Compile patterns for efficiency
        self.greeting_regex = re.compile(
            "|".join(self.greeting_patterns), re.IGNORECASE
        )
        self.non_fitness_regex = re.compile(
            "|".join(self.non_fitness_patterns), re.IGNORECASE
        )

    def should_handle_simply(self, message: str) -> bool:
        """Check if the message should be handled by the simple agent"""
        message_lower = message.lower().strip()

        # Check for greetings
        if self.greeting_regex.search(message_lower):
            return True

        # Check for non-fitness questions
        if self.non_fitness_regex.search(message_lower):
            return True

        # Check for very short messages (likely greetings)
        if len(message_lower.split()) <= 3:
            return True

        return False

    def get_simple_response(self, message: str) -> str:
        """Generate a simple response for basic messages"""
        message_lower = message.lower().strip()

        # Greeting responses
        if re.search(r"\b(hi|hello|hey)\b", message_lower):
            return "👋 Hi there! I'm your Strava running coach. How can I help you with your running data today?"

        if re.search(r"\b(good morning|good afternoon|good evening)\b", message_lower):
            return "👋 Hello! I'm your Strava running coach. Ready to analyze your runs?"

        if re.search(r"\b(how are you|how\'s it going|what\'s up)\b", message_lower):
            return "I'm doing great! Ready to help you with your running analysis. What would you like to know about your runs?"

        if re.search(r"\b(thanks|thank you|thx)\b", message_lower):
            return "You're welcome! 😊 Let me know if you need anything else about your running data."

        if re.search(r"\b(bye|goodbye|see you)\b", message_lower):
            return "👋 Goodbye! Keep up the great running! 🏃‍♂️"

        if re.search(r"\b(yes|no|ok|okay|sure)\b", message_lower):
            return "Got it! What would you like to know about your running data?"

        # Non-fitness responses
        if re.search(r"\b(weather|temperature|rain|sunny)\b", message_lower):
            return "I'm focused on your running data! For weather info, try asking about how weather might have affected your recent runs."

        if re.search(r"\b(time|date|day|week)\b", message_lower):
            return "I can help you analyze your runs by time periods! Try asking something like 'Show me my runs from last week' or 'Compare my runs from this month vs last month'."

        if re.search(r"\b(joke|funny|humor)\b", message_lower):
            return "😄 I'm more of a data nerd than a comedian! But I can definitely help you find the humor in your running stats. Want to see your fastest mile?"

        if re.search(r"\b(help|support|assist)\b", message_lower):
            return "I'm here to help! I can analyze your running data, compare runs, show trends, and provide coaching insights. Try asking about your runs, pace, heart rate, or training patterns!"

        if re.search(r"\b(what can you do|capabilities|features)\b", message_lower):
            return "🏃‍♂️ I'm your Strava running coach! I can:\n• Analyze your running performance\n• Compare different runs\n• Show trends over time\n• Provide coaching insights\n• Generate visualizations\n\nTry asking about your runs, pace, heart rate, or training patterns!"

        # Default response for short messages
        if len(message_lower.split()) <= 3:
            return "👋 Hi! I'm your Strava running coach. I can help you analyze your running data, compare runs, and provide insights. What would you like to know about your runs?"

        # Fallback
        return "I'm your Strava running coach! I can help you analyze your running data, compare runs, and provide insights. What would you like to know about your runs?"
