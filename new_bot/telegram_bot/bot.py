import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from typing import Dict, Any, List
import os
import json

from config import TELEGRAM_TOKEN

print("🔧 Importing workflow_graph...")
from agents.workflow import workflow_graph

print(f"✅ Workflow imported: {type(workflow_graph)}")

from agents.simple_agent import SimpleAgent
from utils.chat_context import ChatContextManager
from utils.chroma_manager import ChromaManager
from llm.client import LLMClient
from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL, CHROMA_DB_DIR

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class StravaBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_manager = ChatContextManager()
        self.llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        self.simple_agent = SimpleAgent()

        # Initialize the agentic workflow
        print("🔧 Assigning workflow to bot...")
        self.workflow = workflow_graph
        print(f"✅ Workflow assigned to bot: {type(self.workflow)}")

        # Initialize bot
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup bot command and message handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("sync", self.sync_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("info", self.info_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(
            CommandHandler("reset_all", self.reset_all_command)
        )

        # Message handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "User"

        # Check if user needs to provide personal info
        questions = self.chat_manager.ask_for_personal_info(user_id)

        if questions:
            welcome_msg = (
                f"👋 Welcome {username}! I'm your personal Strava running coach.\n\n"
            )
            welcome_msg += "Before we start, I need some information to provide better coaching:\n\n"

            for i, question in enumerate(questions, 1):
                welcome_msg += f"{i}. {question}\n"

            welcome_msg += "\nPlease provide this information one by one, or use /info to set it all at once."
        else:
            # Check if user has data in ChromaDB
            from utils.chroma_manager import ChromaManager
            from llm.client import LLMClient
            from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL

            try:
                llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
                # Ensure chroma stores are in the new_bot directory
                import os

                chroma_dir = os.path.join("./chroma_stores", str(user_id))
                chroma_manager = ChromaManager(chroma_dir, llm_client.embeddings)
                existing_runs = chroma_manager.get_existing_run_names()

                if existing_runs:
                    welcome_msg = f"👋 Welcome back {username}! I'm your personal Strava running coach.\n\n"
                    welcome_msg += (
                        f"📊 You have {len(existing_runs)} runs in your database.\n\n"
                    )
                    welcome_msg += (
                        "Ask me anything about your running data! For example:\n"
                    )
                    welcome_msg += "• 'Compare my last two long runs'\n"
                    welcome_msg += "• 'How did my easy runs perform in August?'\n"
                    welcome_msg += "• 'Show me my fastest 10K'\n\n"
                    welcome_msg += (
                        "Use /sync to update your Strava data, /help for more commands."
                    )
                else:
                    welcome_msg = f"👋 Welcome back {username}! I'm your personal Strava running coach.\n\n"
                    welcome_msg += "📊 No running data found. Let's sync your Strava data first!\n\n"
                    welcome_msg += "Use /sync to import your runs from Strava."
            except Exception as e:
                welcome_msg = f"👋 Welcome back {username}! I'm your personal Strava running coach.\n\n"
                welcome_msg += "📊 Let's sync your Strava data first!\n\n"
                welcome_msg += "Use /sync to import your runs from Strava."

        await update.message.reply_text(welcome_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **Strava Running Coach Bot - Help**

**Commands:**
/start - Start the bot and get personal info questions
/help - Show this help message
/sync - Sync your latest Strava data
/clear - Clear your chat history
/info - Set your personal information
/reset - Reset your chat context and personal info
/reset_all - Complete reset (including all Strava data)

**Example Questions:**
• "Compare my last two long runs"
• "How did my easy runs perform in August?"
• "Show me my fastest 10K"
• "Analyze my heart rate trends"
• "What's my average pace for tempo runs?"

**Features:**
• 📊 Automatic data visualization
• 🏃‍♂️ Personalized coaching insights
• 📈 Performance trend analysis
• 💬 Chat context memory
• 🔄 Automatic Strava sync

The bot will analyze your running data and provide insights with visualizations!
        """

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def sync_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sync command to sync Strava data"""
        user_id = str(update.effective_user.id)

        # Send initial message
        status_message = await update.message.reply_text(
            "🔄 Starting Strava data sync..."
        )

        try:
            # Progress updates
            await status_message.edit_text("🔄 Step 1/4: Fetching runs from Strava...")

            # Run the workflow to sync data
            initial_state = {
                "user_id": user_id,
                "user_message": "sync_data",
                "strava_data": [],
                "json_list": [],
                "documents": [],
                "query": {},
                "retrieved_docs": [],
                "context": "",
                "coach_response": "",
                "plot_path": "",
                "final_response": "",
                "error": "",
                "needs_personal_info": False,
                "personal_info_questions": [],
                "skip_to_end": False,
            }

            # Run the workflow
            await status_message.edit_text("🔄 Step 2/4: Processing run data...")
            result = self.workflow.invoke(initial_state)

            if result.get("error"):
                await status_message.edit_text(
                    f"❌ Error syncing data: {result['error']}"
                )
                return

            # Check what was actually synced
            if result.get("strava_data"):
                runs_count = len(result["strava_data"])
                await status_message.edit_text(
                    f"🔄 Step 3/4: Synced {runs_count} runs from Strava..."
                )
            else:
                await status_message.edit_text(
                    "🔄 Step 3/4: Processing existing data..."
                )

            if result.get("documents"):
                docs_count = len(result["documents"])
                await status_message.edit_text(
                    f"🔄 Step 4/4: Storing {docs_count} runs in vector database..."
                )
            else:
                await status_message.edit_text("🔄 Step 4/4: Finalizing...")

            # Success message with details
            if result.get("strava_data") and result.get("documents"):
                runs_count = len(result["strava_data"])
                docs_count = len(result["documents"])
                success_msg = f"✅ **Strava Sync Complete!**\n\n"
                success_msg += f"📊 **Synced {runs_count} new runs** from Strava\n"
                success_msg += f"💾 **Stored {docs_count} runs** in vector database\n\n"
                success_msg += "🎯 **You can now ask questions like:**\n"
                success_msg += "• 'Compare my last two long runs'\n"
                success_msg += "• 'How did my easy runs perform in August?'\n"
                success_msg += "• 'Show me my fastest 10K'\n"
                success_msg += "• 'Analyze my heart rate trends'"

                await status_message.edit_text(success_msg, parse_mode="Markdown")
            elif not result.get("strava_data") and not result.get("documents"):
                success_msg = f"✅ **Sync Complete!**\n\n"
                success_msg += (
                    f"📊 **No new runs found** - all your data is up to date!\n\n"
                )
                success_msg += "🎯 **You can ask questions like:**\n"
                success_msg += "• 'Compare my last two long runs'\n"
                success_msg += "• 'How did my easy runs perform in August?'\n"
                success_msg += "• 'Show me my fastest 10K'\n"
                success_msg += "• 'Analyze my heart rate trends'"

                await status_message.edit_text(success_msg, parse_mode="Markdown")
            else:
                await status_message.edit_text(
                    "✅ Strava data sync completed! You can now ask questions about your runs."
                )

        except Exception as e:
            logger.error(f"Error in sync command: {e}")
            # Don't show technical errors to users
            await status_message.edit_text(
                "❌ **Sync Failed**\n\nSomething went wrong during the sync. Please try again in a few minutes."
            )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command to clear chat history"""
        user_id = str(update.effective_user.id)

        self.chat_manager.clear_chat_history(user_id)
        await update.message.reply_text("🗑️ Chat history cleared successfully!")

    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /info command to set personal information"""
        user_id = str(update.effective_user.id)

        questions = self.chat_manager.ask_for_personal_info(user_id)

        if not questions:
            await update.message.reply_text(
                "✅ You've already provided all your personal information!"
            )
            return

        info_text = "📝 **Personal Information Setup**\n\n"
        info_text += "Please provide the following information:\n\n"

        for i, question in enumerate(questions, 1):
            info_text += f"{i}. {question}\n"

        info_text += "\nReply with your answers one by one, or send them all in one message separated by newlines."

        await update.message.reply_text(info_text, parse_mode="Markdown")

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command to reset chat context only"""
        user_id = str(update.effective_user.id)

        # Clear all user data
        self.chat_manager.clear_chat_history(user_id)

        # Reset personal info
        current_context = self.chat_manager.get_user_context(user_id)
        current_context["personal_info"] = {}
        current_context["preferences"] = {}
        self.chat_manager.update_user_context(user_id, current_context)

        await update.message.reply_text(
            "🔄 Your chat context has been reset! Use /start to begin again."
        )

    async def reset_all_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /reset_all command to completely reset everything including ChromaDB"""
        user_id = str(update.effective_user.id)

        try:
            # Clear all user data
            self.chat_manager.clear_chat_history(user_id)

            # Reset personal info
            current_context = self.chat_manager.get_user_context(user_id)
            current_context["personal_info"] = {}
            current_context["preferences"] = {}
            self.chat_manager.update_user_context(user_id, current_context)

            # Clear ChromaDB data
            import shutil
            import os

            chroma_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "chroma_stores",
                str(user_id),
            )
            if os.path.exists(chroma_path):
                shutil.rmtree(chroma_path)
                print(f"🗑️ Deleted ChromaDB for user {user_id}")

            # Clear plots
            import os

            plots_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "plots", str(user_id)
            )
            if os.path.exists(plots_path):
                shutil.rmtree(plots_path)
                print(f"🗑️ Deleted plots for user {user_id}")

            await update.message.reply_text(
                "💥 Complete reset! All data including Strava runs have been cleared. Use /start to begin fresh."
            )

        except Exception as e:
            logger.error(f"Error in reset_all: {e}")
            await update.message.reply_text(
                "❌ Error during complete reset. Please try again."
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_id = str(update.effective_user.id)
        user_message = update.message.text

        print(f"\n🚀 ===== NEW MESSAGE RECEIVED =====")
        print(f"🔍 Telegram Update Debug:")
        print(f"   effective_user.id: {update.effective_user.id}")
        print(f"   effective_user.username: {update.effective_user.username}")
        print(f"   effective_user.first_name: {update.effective_user.first_name}")
        print(f"   effective_user.last_name: {update.effective_user.last_name}")
        print(f"   message.chat.id: {update.message.chat.id}")
        print(f"   message.from_user.id: {update.message.from_user.id}")
        print(f"   message.from_user.username: {update.message.from_user.username}")
        print(f"   message.from_user.first_name: {update.message.from_user.first_name}")
        print(f"   message.from_user.last_name: {update.message.from_user.last_name}")
        print(f"   Extracted user_id: {user_id}")
        print(f"   Message: {user_message}")

        # Check if this user is configured in the system
        from utils.user_mapper import UserMapper

        # Debug logging
        print(f"🔍 Bot received message from user_id: {user_id}")
        print(f"🔍 User ID type: {type(user_id)}")
        print(f"🔍 Is user configured: {UserMapper.is_user_configured(user_id)}")

        if not UserMapper.is_user_configured(user_id):
            print(f"❌ User {user_id} not configured - sending error message")
            await update.message.reply_text(
                "❌ **User Not Configured**\n\n"
                "This Telegram account is not configured to use the Strava bot.\n"
                "Please contact the bot administrator to set up your account."
            )
            return

        print(f"✅ User {user_id} is configured - proceeding with message handling")

        # Check if this is a personal info response
        print(f"🔍 Checking if message is personal info response...")
        if await self._handle_personal_info(user_id, user_message, update):
            print(f"✅ Message handled as personal info response")
            return

        print(f"🔍 Message is not personal info - proceeding to agentic workflow")

        # Check if user needs to provide personal info first
        questions = self.chat_manager.ask_for_personal_info(user_id)
        if questions:
            # TEMPORARY: Skip personal info check for wife's user ID
            if user_id == "1088864531":
                print(f"🔧 Skipping personal info check for wife's user ID")
            else:
                await update.message.reply_text(
                    "⚠️ Please provide your personal information first using /info command."
                )
                return

        # Check if this is a simple message that should be handled by the simple agent
        if self.simple_agent.should_handle_simply(user_message):
            simple_response = self.simple_agent.get_simple_response(user_message)
            await update.message.reply_text(simple_response)

            # Update chat context for simple responses too
            self.chat_manager.add_chat_message(
                user_id, user_message, simple_response, is_user=True
            )
            return

        # Check if user has any data in ChromaDB
        from utils.chroma_manager import ChromaManager
        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL

        try:
            llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
            # Ensure chroma stores are in the new_bot directory
            import os

            chroma_dir = os.path.join("./chroma_stores", str(user_id))
            chroma_manager = ChromaManager(chroma_dir, llm_client.embeddings)
            existing_runs = chroma_manager.get_existing_run_names()

            if not existing_runs:
                await update.message.reply_text(
                    "📊 No Strava data found. Use /sync to import your runs first."
                )
                return
        except Exception as e:
            # If ChromaDB check fails, assume no data
            await update.message.reply_text(
                "📊 No Strava data found. Use /sync to import your runs first."
            )
            return

        # Process the user's question
        await update.message.reply_text(
            "🤔 Processing your question... This may take a moment."
        )

        print(f"🚀 Starting agentic workflow for user {user_id}")
        print(f"🔍 User message: {user_message}")

        try:
            # Run the workflow
            print(f"🔍 Creating workflow state...")
            initial_state = {
                "user_id": user_id,
                "user_message": user_message,
                "strava_data": [],
                "json_list": [],
                "documents": [],
                "query": {},
                "retrieved_docs": [],
                "context": "",
                "coach_response": "",
                "plot_path": "",
                "final_response": "",
                "error": "",
                "needs_personal_info": False,
                "personal_info_questions": [],
                "skip_to_end": False,
            }

            # Run the workflow
            print(f"🔍 Invoking self.workflow.invoke()...")
            print(f"🔍 Workflow state: {initial_state}")
            print(f"🔍 Workflow object type: {type(self.workflow)}")

            result = self.workflow.invoke(initial_state)
            print(f"✅ Workflow completed successfully!")
            print(f"🔍 Workflow result: {result}")

            if result.get("error"):
                print(f"❌ Workflow returned error: {result['error']}")
                await update.message.reply_text(f"❌ Error: {result['error']}")
            else:
                # Send the response as plain text (no markdown formatting)
                try:
                    # Check if message is too long
                    if len(result["final_response"]) > 4000:
                        # Split into multiple messages
                        messages = self._split_long_message(result["final_response"])
                        for msg in messages:
                            await update.message.reply_text(msg)
                    else:
                        await update.message.reply_text(result["final_response"])
                except Exception as e:
                    logger.warning(f"Error sending response: {e}")
                    await update.message.reply_text(
                        "❌ Sorry, I encountered an error sending the response. Please try again."
                    )

                # Send plot if available
                if result.get("plot_path") and os.path.exists(result["plot_path"]):
                    with open(result["plot_path"], "rb") as photo:
                        await update.message.reply_photo(
                            photo=photo, caption="📊 Your run analysis visualization"
                        )

                # Update chat context
                self.chat_manager.add_chat_message(
                    user_id, user_message, result["final_response"], is_user=True
                )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Don't show technical errors to users
            await update.message.reply_text(
                "❌ Sorry, I encountered an error processing your question. Please try again or use /sync to refresh your data."
            )

    async def _handle_personal_info(
        self, user_id: str, message: str, update: Update
    ) -> bool:
        """Handle personal information responses"""
        # TEMPORARY: Skip personal info handling for wife's user ID
        if user_id == "1088864531":
            print(f"🔧 Skipping personal info handling for wife's user ID")
            return False

        questions = self.chat_manager.ask_for_personal_info(user_id)

        if not questions:
            return False

        # Check if message contains multiple answers (separated by newlines)
        lines = [line.strip() for line in message.split("\n") if line.strip()]

        if len(lines) == 1 and len(questions) == 1:
            # Single answer for single question
            self.chat_manager.update_personal_info(user_id, "general", lines[0])
            await update.message.reply_text(
                "✅ Thank you! Your information has been saved."
            )
            return True

        elif len(lines) >= len(questions):
            # Multiple answers - try to map them
            info_mapping = {
                "height": ["height", "tall", "cm", "feet", "inch", "'", "ft"],
                "weight": ["weight", "kg", "lbs", "pound", "lb"],
                "age": ["age", "years old", "year", "old"],
                "injuries": [
                    "injury",
                    "injuries",
                    "health",
                    "condition",
                    "pain",
                    "none",
                    "no",
                ],
                "training_plan": [
                    "training",
                    "plan",
                    "goal",
                    "marathon",
                    "fitness",
                    "5k",
                    "10k",
                    "half",
                ],
            }

            # Track what was successfully mapped
            mapped_info = set()

            for line in lines:
                line_lower = line.lower()
                mapped = False

                for info_type, keywords in info_mapping.items():
                    if any(keyword in line_lower for keyword in keywords):
                        self.chat_manager.update_personal_info(user_id, info_type, line)
                        mapped_info.add(info_type)
                        mapped = True
                        break

                if not mapped:
                    # Try to guess based on content
                    if any(char.isdigit() for char in line):
                        if "'" in line or "ft" in line or "cm" in line:
                            self.chat_manager.update_personal_info(
                                user_id, "height", line
                            )
                            mapped_info.add("height")
                        elif "kg" in line or "lbs" in line or "lb" in line:
                            self.chat_manager.update_personal_info(
                                user_id, "weight", line
                            )
                            mapped_info.add("weight")
                        elif "year" in line or int(line) < 100:
                            self.chat_manager.update_personal_info(user_id, "age", line)
                            mapped_info.add("age")

            await update.message.reply_text(
                "✅ Thank you! Your information has been saved."
            )

            # Check if all info is now collected
            remaining_questions = self.chat_manager.ask_for_personal_info(user_id)
            if not remaining_questions:
                await update.message.reply_text(
                    "🎉 All personal information collected! Now let's sync your Strava data. Use /sync to get started."
                )
            else:
                await update.message.reply_text(
                    f"📝 Still need: {', '.join(remaining_questions)}"
                )

            return True

        return False

    def _split_long_message(self, message: str, max_length: int = 4000) -> List[str]:
        """Split a long message into multiple parts"""
        if len(message) <= max_length:
            return [message]

        parts = []
        current_part = ""

        # Split by paragraphs first
        paragraphs = message.split("\n\n")

        for paragraph in paragraphs:
            # If adding this paragraph would exceed limit, start new part
            if len(current_part) + len(paragraph) + 2 > max_length and current_part:
                parts.append(current_part.strip())
                current_part = paragraph
            else:
                if current_part:
                    current_part += "\n\n" + paragraph
                else:
                    current_part = paragraph

        # Add the last part
        if current_part:
            parts.append(current_part.strip())

        # If any part is still too long, split by sentences
        final_parts = []
        for part in parts:
            if len(part) <= max_length:
                final_parts.append(part)
            else:
                # Split by sentences
                sentences = part.split(". ")
                current_sentence_part = ""
                for sentence in sentences:
                    if (
                        len(current_sentence_part) + len(sentence) + 2 > max_length
                        and current_sentence_part
                    ):
                        final_parts.append(current_sentence_part.strip() + ".")
                        current_sentence_part = sentence
                    else:
                        if current_sentence_part:
                            current_sentence_part += ". " + sentence
                        else:
                            current_sentence_part = sentence

                if current_sentence_part:
                    final_parts.append(current_sentence_part.strip())

        return final_parts

    def run(self):
        """Run the bot"""
        logger.info("Starting Strava Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = StravaBot()
    bot.run()
