from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from typing import List
import json
from datetime import datetime


class LLMClient:
    def __init__(self, api_key: str, model_name: str, embed_model: str):
        self.llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=embed_model, google_api_key=api_key
        )

        # Prompt for converting JSON to text documents
        self.summary_prompt = PromptTemplate(
            input_variables=["json_data"],
            template=r"""
You are a sports activity summarizer. Your only task is to convert the given running activity JSON
into a **clear, verbose, factual, and precise** human-readable summary.

Rules:
- Include ONLY: Run name, timestamp, distance, run type, average heart rate, average cadence, average power, elevation gain.
- Then include a per-KM breakdown with pace, heart rate, power, and elevation gain.
- Keep it short, factual, relevant to the run.
- Do NOT add advice, opinions, or unrelated information.
- Drop any null or missing fields silently.

JSON:
{json_data}

Example Output Format:
Run Name: Tempo Run - 2
Timestamp: 2025-07-31 06:08:32
Distance: 7.0 kms
Run Type: Tempo
Average Heart Rate: 162.78 bpm
Average Pace: 9.24 min/km
Average Power: 163.15 W
Elevation Gain: 15.6 m

Per-KM Breakdown:
KM 1: Pace 8.725 min/km, HR 146.248 bpm, Power 170 W, Elevation Gain 2.2 m
KM 2: Pace 7.909 min/km, HR 166.694 bpm, Power 165 W, Elevation Gain 2.6 m

Output the final result as plain text with exact formatting as mentioned here.
""",
        )

        # Prompt for query interpretation
        self.interpreter_prompt = PromptTemplate(
            input_variables=["user_text"],
            template=r"""
You are an expert sports data interpreter. Your task is to convert a user's natural language query
about their running activities into a **strict JSON object** matching this schema:

{{
  "type": str or null, #Permissible Values ['Long', 'Easy', 'Tempo', 'Interval']
  "min_avg_hr": float or null,
  "max_avg_hr": float or null,
  "start_date": "YYYY-MM-DD" or null,
  "end_date": "YYYY-MM-DD" or null,
  "last_n_runs": int or null,
  "distance_km": float or null,
  "metric_filter": str or null,
  "run_names": list or null # List of specific run names to find (e.g., ["Tempo Run - 1", "Tempo Run - 2"])
}}

Rules:
- Only include keys present in the user's request, others must be null.
- Convert relative time expressions like "last 30 days" into actual dates.
- Use exact JSON syntax, no extra commentary or explanations.
- Be precise, never assume extra filters.
- If user asks for specific run names (e.g., "Tempo Run 1 and 2"), set run_names to the list of names and set last_n_runs to null.
- If user asks for "last N runs", only then set last_n_runs and set run_names to null.
- For run names, use the exact format that appears in Strava (e.g., "Tempo Run - 1" not "Tempo Run 1").
- When user asks for "Tempo Run 1 and 2", interpret as ["Tempo Run - 1", "Tempo Run - 2"] (with dashes).
- When user asks for "Easy Run 5", interpret as ["Easy Run - 5"] (with dash).

User Query:
"{user_text}"

Output JSON:
""",
        )

        # Prompt for coach responses
        self.coach_prompt = PromptTemplate(
            input_variables=["run_data", "question", "chat_context"],
            template="""
You are a Strava analytics assistant and my personal running coach. Give concise, actionable insights based on the questions asked.
If a user asks for a plan, use your own knowledge and experience as a personal coach to 
analyse user's existing run data and create a plan. Make sure it is logical and achievable.

Chat Context (user's personal info, preferences, etc.):
{chat_context}

Here is the user's run data:
{run_data}

Answer the following question based on this data and chat context:
{question}

IMPORTANT GUIDELINES:
- Keep responses concise and 
- Use simple bullet points (•) instead of markdown formatting
- Focus on 5-7 key insights maximum, and make sure they are relevant and not vague
- Be specific and actionable
- Keep it detailed and comprehensive yet concise in the range of <=4000 characters
- Mention the Positives and the Improvements that the user can make
- Avoid over-analysis
- Use clear, readable text without special characters
- If the response would be too long, prioritize the most important points

Provide actionable insights and recommendations based on the data.
""",
        )

        # Prompt for plotting
        self.plotting_prompt = PromptTemplate(
            input_variables=["df_description", "user_question", "llm_response"],
            template="""
You are an AI Strava Visualisation assistant. Your aim is to generate plots for the relevant user questions.
The schema of the dataframe supplied to you is as follows:
{df_description}

User Question: {user_question}
Coach Response: {llm_response}

Before generating code, look at the dataframe, try to visualise it internally, understand the various columns and
the values they have, understand their data types and value counts. Then go onto to generate code.

Instructions for generating code:
- Produce Python code that directly uses the supplied 'df' DataFrame.
- Do not define additional example functions or call them.
- Do not include any example usage comments.
- Produce simple matplotlib plots relevant to the question.
- Handle missing/null values gracefully.
- Dynamically select runs based on the question.
- CRITICAL: Use ONLY the exact run names provided in the df_description. Do not modify, guess, or create new run names.
- If filtering by run name, use the exact names from the "Available run names" list.
- Only provide the code inside a Python code block (```python ... ```).
- Code should be executable as-is in the supplied environment.
- IMPORTANT: Do NOT use plt.show() - this will cause errors in the environment.
- IMPORTANT: Do NOT use exit(), sys.exit(), or any other exit functions - this will crash the bot.
- IMPORTANT: Do NOT use return statements outside of functions.
- Create plots that can be saved with plt.savefig().
- Handle errors gracefully with try-except blocks instead of exiting.
- If no data is found, create an informative plot message instead of exiting.
""",
        )

    def create_documents(self, json_list: List[str]) -> List[Document]:
        """Convert JSON list to Document objects with rich metadata"""
        docs = []

        for i, run_json in enumerate(json_list):
            run_data = json.loads(run_json)[0]  # extract first (and only) run object

            # Generate the run summary text
            prompt_text = self.summary_prompt.format(json_data=run_json)

            try:
                summary = self.llm.invoke(prompt_text).content
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    # Rate limited - wait and retry
                    import time

                    wait_time = 60  # Wait 1 minute
                    print(f"⚠️ Rate limited, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    summary = self.llm.invoke(prompt_text).content
                else:
                    raise e

            # Build rich metadata
            try:
                run_date = datetime.strptime(run_data["DateTime"], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                run_date = None

            metadata = {
                "source": run_data.get("Name", "Unknown Run"),
                "name": run_data.get("Name", "Unknown Run"),
                "type": run_data.get("Run_Type", "Unknown Type"),
                "distance": run_data.get("Distance", None),
                "date": run_data.get("DateTime", None),
                "year": run_date.year if run_date else None,
                "month": run_date.month if run_date else None,
                "week": run_date.isocalendar()[1] if run_date else None,
                "pace": run_data.get("Avg_Pace"),
                "avg_hr": run_data.get("Avg_HR"),
                "avg_cadence": run_data.get("Avg_Cadence"),
                "avg_power": run_data.get("Avg_Power"),
                "elevation_gain": run_data.get("Elevation_Gain_m"),
            }

            docs.append(Document(page_content=summary.strip(), metadata=metadata))

            # Add delay between requests to avoid rate limiting
            if i < len(json_list) - 1:  # Don't delay after the last one
                import time

                time.sleep(2)  # 2 second delay between requests

        return docs

    def interpret_query(self, user_text: str) -> dict:
        """Convert user text to structured query"""
        prompt_text = self.interpreter_prompt.format(user_text=user_text)
        response = self.llm.invoke(prompt_text).content.strip()

        # Remove any markdown / ```json fences
        import re

        response = re.sub(r"^```json\s*|```$", "", response, flags=re.MULTILINE).strip()

        # Parse JSON safely
        try:
            query_dict = json.loads(response)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse Gemini output as JSON:\n{response}")

        return query_dict

    def get_coach_response(
        self, run_data: str, question: str, chat_context: str = ""
    ) -> str:
        """Get coaching response based on run data and question"""
        prompt_text = self.coach_prompt.format(
            run_data=run_data, question=question, chat_context=chat_context
        )
        response = self.llm.invoke(prompt_text)
        return response.content

    def get_plotting_code(
        self, df_description: str, user_question: str, llm_response: str
    ) -> str:
        """Get plotting code from LLM"""
        prompt_text = self.plotting_prompt.format(
            df_description=df_description,
            user_question=user_question,
            llm_response=llm_response,
        )
        response = self.llm.invoke(prompt_text)
        ai_code = response.content.strip()

        # Clean up the code
        if ai_code.startswith("```"):
            ai_code = "\n".join(ai_code.splitlines()[1:-1])

        return ai_code
