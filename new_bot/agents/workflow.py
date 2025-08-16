from langgraph.graph import StateGraph, END
from typing import Dict, List, Any, TypedDict
from pydantic import BaseModel
import json


# State definition
class WorkflowState(TypedDict):
    user_id: str
    user_message: str
    strava_data: List[Any]
    json_list: List[str]
    documents: List[Any]
    query: Dict[str, Any]
    retrieved_docs: List[Any]
    context: str
    coach_response: str
    plot_path: str
    final_response: str
    error: str
    needs_personal_info: bool
    personal_info_questions: List[str]
    skip_to_end: bool


# Agent functions
def data_availability_check_agent(state: WorkflowState) -> WorkflowState:
    """Agent to check if user has data available before processing queries"""
    print(f"🔍 [data_availability_check] Starting for user: {state.get('user_id')}")
    print(f"🔍 [data_availability_check] Message: {state.get('user_message')}")

    try:
        # Skip this check for sync operations
        if state["user_message"] == "sync_data":
            print(f"🔍 [data_availability_check] Sync operation - skipping check")
            return state

        from utils.chroma_manager import ChromaManager
        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL

        # Check if user has any data in ChromaDB
        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        print(f"🔍 [data_availability_check] LLM client initialized")

        # Ensure chroma stores are in the new_bot directory
        import os

        chroma_dir = os.path.join("./chroma_stores", str(state["user_id"]))
        print(f"🔍 [data_availability_check] ChromaDB directory: {chroma_dir}")

        chroma_manager = ChromaManager(chroma_dir, llm_client.embeddings)
        existing_runs = chroma_manager.get_existing_run_names()

        print(
            f"🔍 [data_availability_check] Existing runs found: {len(existing_runs) if existing_runs else 0}"
        )

        if not existing_runs:
            print(f"🔍 [data_availability_check] No runs found - skipping to end")
            return {
                **state,
                "error": "No Strava data found. Use /sync to import your runs first.",
                "final_response": "📊 No Strava data found. Use /sync to import your runs first.",
                "skip_to_end": True,  # Flag to skip processing
            }

        print(f"🔍 [data_availability_check] Runs found - proceeding with workflow")
        return state

    except Exception as e:
        print(f"❌ [data_availability_check] Error: {e}")
        return {
            **state,
            "error": f"Data availability check error: {str(e)}",
            "final_response": "📊 No Strava data found. Use /sync to import your runs first.",
            "skip_to_end": True,  # Flag to skip processing
        }


def strava_agent(state: WorkflowState) -> WorkflowState:
    """Agent to fetch Strava data - ONLY for sync operations"""
    try:
        # Only run this agent for sync operations
        if state["user_message"] != "sync_data":
            return {**state, "strava_data": [], "json_list": []}

        from strava.client import StravaClient
        from config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET

        # Get user's Strava token
        telegram_chat_id = state["user_id"]

        # Use UserMapper to get user configuration
        from utils.user_mapper import UserMapper

        username = UserMapper.get_username_by_chat_id(telegram_chat_id)
        if not username:
            return {
                **state,
                "error": f"No user found for Telegram chat ID {telegram_chat_id}. Please set up your Strava connection.",
            }

        strava_token = UserMapper.get_strava_token_by_chat_id(telegram_chat_id)
        if not strava_token:
            return {
                **state,
                "error": f"No Strava refresh token found for user {username}. Please set up your Strava connection.",
            }

        # Get user-specific Strava credentials if available, otherwise use global ones
        user_client_id = (
            UserMapper.get_strava_client_id_by_chat_id(telegram_chat_id)
            or STRAVA_CLIENT_ID
        )
        user_client_secret = (
            UserMapper.get_strava_client_secret_by_chat_id(telegram_chat_id)
            or STRAVA_CLIENT_SECRET
        )

        # Initialize Strava client with user-specific credentials
        strava_client = StravaClient(
            user_client_id, user_client_secret, strava_token, username
        )

        # Check existing runs in vector store first
        from utils.chroma_manager import ChromaManager
        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL

        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        # Ensure chroma stores are in the new_bot directory
        import os

        chroma_dir = os.path.join("./chroma_stores", str(telegram_chat_id))
        chroma_manager = ChromaManager(chroma_dir, llm_client.embeddings)

        existing_runs = chroma_manager.get_existing_run_names()
        print(f"📊 Found {len(existing_runs)} existing runs in vector store")

        # Fetch only new runs from Strava
        print("🔄 Fetching new runs from Strava...")
        try:
            dfs = strava_client.fetch_all_runs()  # Fetch all runs
        except Exception as fetch_error:
            print(f"⚠️ Error fetching runs from Strava: {fetch_error}")
            # Return empty data instead of failing completely
            return {
                **state,
                "strava_data": [],
                "json_list": [],
                "error": f"Failed to fetch Strava data: {str(fetch_error)}",
            }

        # Filter out existing runs
        new_dfs = []
        for df in dfs:
            try:
                run_name = df["Activity_Name"].iloc[0] if not df.empty else ""
                if run_name not in existing_runs:
                    new_dfs.append(df)
                    print(f"🆕 New run found: {run_name}")
                else:
                    print(f"✅ Run already exists: {run_name}")
            except Exception as filter_error:
                print(f"⚠️ Error processing run data: {filter_error}")
                continue

        # Convert to JSON
        json_list = []
        if new_dfs:
            try:
                json_list = strava_client.convert_to_json_list(new_dfs)
            except Exception as json_error:
                print(f"⚠️ Error converting to JSON: {json_error}")
                # Continue with empty JSON list

        return {**state, "strava_data": new_dfs, "json_list": json_list}
    except Exception as e:
        print(f"❌ Strava agent error: {str(e)}")
        return {**state, "error": f"Strava agent error: {str(e)}"}


def document_creator_agent(state: WorkflowState) -> WorkflowState:
    """Agent to create documents from JSON data - ONLY for sync operations"""
    try:
        # Only run this agent for sync operations
        if state["user_message"] != "sync_data":
            return {**state, "documents": []}

        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL

        # Initialize LLM client
        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)

        # Create documents only if there are new runs
        if state["json_list"]:
            documents = llm_client.create_documents(state["json_list"])
            print(f"📝 Created {len(documents)} new documents")
        else:
            documents = []
            print("✅ No new runs to process")

        return {**state, "documents": documents}
    except Exception as e:
        return {**state, "error": f"Document creator error: {str(e)}"}


def document_storage_agent(state: WorkflowState) -> WorkflowState:
    """Agent to store documents in vector store - ONLY for sync operations"""
    try:
        # Only run this agent for sync operations
        if state["user_message"] != "sync_data":
            return {**state, "storage_status": "skipped"}

        # Only store if there are new documents
        if not state.get("documents"):
            return {**state, "storage_status": "no_new_documents"}

        from utils.chroma_manager import ChromaManager
        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL, CHROMA_DB_DIR

        # Initialize components
        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        # Use absolute path to ensure correct ChromaDB access
        import os

        chroma_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "chroma_stores",
            str(state["user_id"]),
        )
        chroma_manager = ChromaManager(chroma_dir, llm_client.embeddings)

        # Store documents
        chroma_manager.add_documents(state["documents"])

        return {
            **state,
            "storage_status": f"stored_{len(state['documents'])}_documents",
        }
    except Exception as e:
        return {**state, "error": f"Document storage error: {str(e)}"}


def query_interpreter_agent(state: WorkflowState) -> WorkflowState:
    """Agent to interpret user query"""
    print(f"🔍 [query_interpreter] Starting for user: {state.get('user_id')}")
    print(f"🔍 [query_interpreter] Message: {state.get('user_message')}")

    try:
        # Skip query interpretation for sync_data message
        if state["user_message"] == "sync_data":
            print(f"🔍 [query_interpreter] Sync operation - skipping interpretation")
            return {**state, "query": {"type": "sync", "action": "sync_data"}}

        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL

        # Initialize LLM client
        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        print(f"🔍 [query_interpreter] LLM client initialized")

        # Interpret query
        print(f"🔍 [query_interpreter] Interpreting query...")
        query = llm_client.interpret_query(state["user_message"])
        print(f"🔍 [query_interpreter] Query interpreted: {query}")

        return {**state, "query": query}
    except Exception as e:
        print(f"❌ [query_interpreter] Error: {e}")
        return {**state, "error": f"Query interpreter error: {str(e)}"}


def document_retriever_agent(state: WorkflowState) -> WorkflowState:
    """Agent to retrieve relevant documents"""
    print(f"🔍 [document_retriever] Starting for user: {state.get('user_id')}")
    print(f"🔍 [document_retriever] Query: {state.get('query')}")

    try:
        # Handle sync_data case
        if state["query"].get("type") == "sync":
            print(f"🔍 [document_retriever] Sync operation - skipping retrieval")
            return {
                **state,
                "retrieved_docs": [],
                "context": "Data sync in progress...",
            }

        from utils.chroma_manager import ChromaManager
        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL, CHROMA_DB_DIR

        # Initialize components
        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        print(f"🔍 [document_retriever] LLM client initialized")

        # Use absolute path to ensure correct ChromaDB access
        import os

        chroma_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "chroma_stores",
            str(state["user_id"]),
        )
        chroma_manager = ChromaManager(chroma_dir, llm_client.embeddings)
        print(f"🔍 [document_retriever] ChromaManager initialized")

        # Retrieve documents based on query
        # If specific run names are requested, use optimized method
        if state["query"].get("run_names"):
            retrieved_docs = chroma_manager.get_runs_by_names(
                state["query"]["run_names"]
            )
            print(f"🔍 Searching for specific runs: {state['query']['run_names']}")
        else:
            retrieved_docs = chroma_manager.retrieve_runs(state["query"])

        # If no documents found, get latest 5 runs filtered by date
        if not retrieved_docs:
            retrieved_docs = chroma_manager.get_latest_runs(5)
            print(
                f"⚠️ No specific runs found, returning latest {len(retrieved_docs)} runs"
            )

            # Add context about using latest runs
            if retrieved_docs:
                context = chroma_manager.docs_to_context(
                    retrieved_docs, include_per_km=True
                )
                context = f"📊 No specific runs found for your query. Here are your latest 5 runs for context:\n\n{context}"
            else:
                context = "No run data available."
        else:
            print(f"📊 Found {len(retrieved_docs)} relevant runs")
            context = chroma_manager.docs_to_context(
                retrieved_docs, include_per_km=True
            )

        # Print document retrieval info for debugging
        print(f"\n📚 DOCUMENT RETRIEVAL:")
        print(f"Query: {state['query']}")
        print(f"Retrieved {len(retrieved_docs)} documents")
        for i, doc in enumerate(retrieved_docs[:3]):  # Show first 3 docs
            print(
                f"  {i+1}. {doc.metadata.get('name', 'Unknown')} - {doc.metadata.get('date', 'No date')}"
            )
        if len(retrieved_docs) > 3:
            print(f"  ... and {len(retrieved_docs) - 3} more documents")
        print(f"Context length: {len(context)} characters")

        return {**state, "retrieved_docs": retrieved_docs, "context": context}
    except Exception as e:
        return {**state, "error": f"Document retriever error: {str(e)}"}


def coach_agent(state: WorkflowState) -> WorkflowState:
    """Agent to provide coaching response"""
    print(f"🔍 [coach_agent] Starting for user: {state.get('user_id')}")
    print(f"🔍 [coach_agent] Query: {state.get('query')}")
    print(f"🔍 [coach_agent] Context: {state.get('context', '')[:100]}...")

    try:
        # Handle sync_data case
        if state["query"].get("type") == "sync":
            print(f"🔍 [coach_agent] Sync operation - skipping coaching")
            return {**state, "coach_response": "Data sync completed successfully!"}

        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL
        from utils.chroma_manager import ChromaManager

        # Initialize LLM client
        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        print(f"🔍 [coach_agent] LLM client initialized")

        # Get chat context
        from utils.chat_context import ChatContextManager

        chat_manager = ChatContextManager()
        chat_context = chat_manager.get_chat_summary(state["user_id"])
        print(
            f"🔍 [coach_agent] Chat context retrieved: {len(chat_context) if chat_context else 0} chars"
        )

        # Get coaching response
        print(f"🔍 [coach_agent] Getting coaching response...")
        coach_response = llm_client.get_coach_response(
            state["context"], state["user_message"], chat_context
        )
        print(
            f"🔍 [coach_agent] Coaching response generated: {len(coach_response) if coach_response else 0} chars"
        )

        # Print the Fitness Coach's output for debugging
        print("\n" + "=" * 80)
        print("🏃‍♂️ FITNESS COACH RESPONSE:")
        print("=" * 80)
        print(coach_response)
        print("=" * 80 + "\n")

        return {**state, "coach_response": coach_response}
    except Exception as e:
        print(f"❌ [coach_agent] Error: {e}")
        return {**state, "error": f"Coach agent error: {str(e)}"}


def plotting_agent(state: WorkflowState) -> WorkflowState:
    """Agent to generate plots"""
    try:
        # Handle sync_data case - no plots needed
        if state["query"].get("type") == "sync":
            return {**state, "plot_path": ""}

        # Always try to generate plots for every scenario
        # The plotting agent will handle failures gracefully

        from utils.plotting_agent import PlottingAgent
        from utils.chroma_manager import ChromaManager
        from llm.client import LLMClient
        from config import GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL

        # Initialize components
        llm_client = LLMClient(GOOGLE_API_KEY, MODEL_NAME, EMBED_MODEL)
        # Ensure plots are saved to the new_bot/plots directory
        import os

        plots_dir = os.path.join("./plots", str(state["user_id"]))
        plotting_agent = PlottingAgent(plots_dir)

        # Convert context to DataFrame
        chroma_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "chroma_stores",
            str(state["user_id"]),
        )
        chroma_manager = ChromaManager(chroma_dir, llm_client.embeddings)
        df = chroma_manager.context_to_dataframe(state["context"])

        # Skip if DataFrame is empty
        if df.empty:
            return {**state, "plot_path": ""}

        # Generate plot
        print(f"\n📊 Attempting to generate plot for: {state['user_message']}")
        plot_path = ""

        try:
            plot_path = plotting_agent.generate_plot(
                df,
                state["user_message"],
                state["coach_response"],  # Add the missing llm_response parameter
                llm_client,
            )
            if plot_path:
                print(f"✅ AI plot generated successfully: {plot_path}")
            else:
                print("⚠️ AI plot generation returned no path")
        except Exception as e:
            print(f"⚠️ AI plotting failed: {e}, falling back to simple plot")
            try:
                plot_path = plotting_agent.create_simple_plot(df, state["user_message"])
                if plot_path:
                    print(f"✅ Simple plot fallback generated: {plot_path}")
            except Exception as fallback_error:
                print(f"❌ Simple plot fallback also failed: {fallback_error}")
                plot_path = ""

        # If still no plot, try one more time with simple plot
        if not plot_path:
            print("🔄 Final attempt with simple plot...")
            try:
                plot_path = plotting_agent.create_simple_plot(df, state["user_message"])
                if plot_path:
                    print(f"✅ Final simple plot generated: {plot_path}")
                else:
                    print("❌ No plot could be generated")
            except Exception as final_error:
                print(f"❌ Final plot attempt failed: {final_error}")
                plot_path = ""

        print(f"📊 Final plot path: {plot_path or 'None'}")

        return {**state, "plot_path": plot_path or ""}
    except Exception as e:
        return {**state, "error": f"Plotting agent error: {str(e)}"}


def response_formatter_agent(state: WorkflowState) -> WorkflowState:
    """Agent to format final response"""
    print(f"🔍 [response_formatter] Starting for user: {state.get('user_id')}")
    print(
        f"🔍 [response_formatter] Coach response: {state.get('coach_response', '')[:100]}..."
    )
    print(f"🔍 [response_formatter] Plot path: {state.get('plot_path', 'None')}")

    try:
        # Format the final response
        response_parts = []

        # Always include the coach response
        if state.get("coach_response"):
            coach_response = state["coach_response"]
            print(
                f"🔍 [response_formatter] Processing coach response: {len(coach_response)} chars"
            )

            # Clean up the response - remove problematic markdown and make it readable
            import re

            # Remove markdown formatting that causes issues
            coach_response = re.sub(
                r"\*\*(.*?)\*\*", r"\1", coach_response
            )  # Remove bold
            coach_response = re.sub(
                r"\*(.*?)\*", r"\1", coach_response
            )  # Remove italic
            coach_response = re.sub(
                r"_(.*?)_", r"\1", coach_response
            )  # Remove underline

            # Replace problematic characters with simple alternatives
            coach_response = coach_response.replace("\\", "")  # Remove backslashes
            coach_response = coach_response.replace("`", "'")  # Replace backticks

            # Ensure bullet points are simple
            coach_response = re.sub(r"[-*]\s+", "• ", coach_response)

            # Truncate if too long (Telegram limit is ~4096 characters)
            if len(coach_response) > 3000:  # Leave more buffer
                # Try to truncate at a sentence boundary
                sentences = coach_response.split(". ")
                truncated = ""
                for sentence in sentences:
                    if len(truncated + sentence + ". ") <= 3000:
                        truncated += sentence + ". "
                    else:
                        break
                coach_response = (
                    truncated.strip() + "\n\n... (response truncated for readability)"
                )
                print(
                    f"🔍 [response_formatter] Response truncated to {len(coach_response)} chars"
                )

            response_parts.append(coach_response)

        # Add plot information if available
        if state.get("plot_path"):
            response_parts.append(
                "📊 I've generated a visualization for you. Check the attached image!"
            )
            print(f"🔍 [response_formatter] Plot info added to response")
        else:
            # If no plot was generated, inform the user
            response_parts.append("📊 No visualization available for this analysis.")
            print(f"🔍 [response_formatter] No plot info added to response")

        # If no coach response, provide a fallback
        if not response_parts:
            response_parts.append(
                "I couldn't generate a response for your question. Please try rephrasing it."
            )
            print(f"🔍 [response_formatter] Using fallback response")

        final_response = "\n\n".join(response_parts)
        print(
            f"🔍 [response_formatter] Final response length: {len(final_response)} chars"
        )

        return {**state, "final_response": final_response}
    except Exception as e:
        print(f"❌ [response_formatter] Error: {e}")
        return {**state, "error": f"Response formatter error: {str(e)}"}


def personal_info_checker(state: WorkflowState) -> WorkflowState:
    """Check if user needs to provide personal information"""
    print(f"🔍 [personal_info_checker] Starting for user: {state.get('user_id')}")

    try:
        from utils.chat_context import ChatContextManager

        chat_manager = ChatContextManager()
        questions = chat_manager.ask_for_personal_info(state["user_id"])

        needs_info = len(questions) > 0
        print(f"🔍 [personal_info_checker] User needs info: {needs_info}")
        print(f"🔍 [personal_info_checker] Questions: {questions}")

        result = {
            **state,
            "needs_personal_info": needs_info,
            "personal_info_questions": questions,
        }

        print(f"✅ [personal_info_checker] Completed successfully")
        return result

    except Exception as e:
        print(f"❌ [personal_info_checker] Error: {e}")
        return {**state, "error": f"Personal info checker error: {str(e)}"}


# Create the workflow
def create_workflow():
    """Create the LangGraph workflow"""

    print("🔧 Creating LangGraph workflow...")

    # Create the graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    print("🔧 Adding workflow nodes...")
    workflow.add_node("data_availability_check", data_availability_check_agent)
    workflow.add_node("strava_agent", strava_agent)
    workflow.add_node("document_creator", document_creator_agent)
    workflow.add_node("document_storage", document_storage_agent)
    workflow.add_node("query_interpreter", query_interpreter_agent)
    workflow.add_node("document_retriever", document_retriever_agent)
    workflow.add_node("coach_agent", coach_agent)
    workflow.add_node("plotting_agent", plotting_agent)
    workflow.add_node("response_formatter", response_formatter_agent)
    workflow.add_node("personal_info_checker", personal_info_checker)

    # Define the flow
    print("🔧 Setting workflow flow...")
    workflow.set_entry_point("personal_info_checker")

    # Main flow
    workflow.add_edge("personal_info_checker", "data_availability_check")

    # Conditional routing based on data availability
    def should_skip_to_end(state):
        return state.get("skip_to_end", False)

    workflow.add_conditional_edges(
        "data_availability_check",
        should_skip_to_end,
        {True: "response_formatter", False: "strava_agent"},
    )

    workflow.add_edge("strava_agent", "document_creator")
    workflow.add_edge("document_creator", "document_storage")
    workflow.add_edge("document_storage", "query_interpreter")
    workflow.add_edge("query_interpreter", "document_retriever")
    workflow.add_edge("document_retriever", "coach_agent")
    workflow.add_edge("coach_agent", "plotting_agent")
    workflow.add_edge("plotting_agent", "response_formatter")
    workflow.add_edge("response_formatter", END)

    print("🔧 Compiling workflow...")
    compiled_workflow = workflow.compile()
    print("✅ Workflow compiled successfully!")

    return compiled_workflow


# Create the workflow instance
print("🚀 Creating workflow instance...")
workflow_graph = create_workflow()
print("✅ Workflow instance created successfully!")
print(f"🔍 Workflow type: {type(workflow_graph)}")
print(
    f"🔍 Workflow methods: {[m for m in dir(workflow_graph) if not m.startswith('_')]}"
)
