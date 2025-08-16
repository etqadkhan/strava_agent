import matplotlib.pyplot as plt
import pandas as pd
import io
import contextlib
import os
from typing import Optional
from datetime import datetime


class PlottingAgent:
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            # Default to new_bot/plots directory
            import os

            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "plots"
            )
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Ensure output directory exists"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_plot(
        self, df: pd.DataFrame, user_question: str, llm_response: str, llm_client
    ) -> Optional[str]:
        """Generate plot using AI-generated code"""
        if df.empty:
            return None

        # Extract actual run names from the DataFrame
        actual_run_names = df["run_name"].unique().tolist()
        run_names_str = ", ".join([f'"{name}"' for name in actual_run_names])

        # Prepare dataframe description for LLM
        df_description = f"""
You are given a pandas dataframe 'df' with per-KM run data:
Columns:
- date: datetime of run
- run_name: name of the run (Unique to Each Run)
- run_type: type (Long, Easy, Tempo, etc.)
- km: KM number during split (int) (1, 2, 5 etc.)
- pace: pace in min/km for each split(float) (8.2, 9.1 etc.)
- hr: heart rate bpm per split (float) (155.1, 160.3 etc.)
- power: power W generated per split (float)
- elevation_gain: elevation gain in meters for split (int)
- distance: total run distance km (float) (12,0, 8.1 etc.)
- avg_hr: average HR for entire run (float) 
- avg_pace: average pace for entire run (float) 
- total_elevation: total elevation for entire run (float) 

Available run names in the data: [{run_names_str}]
IMPORTANT: Use these exact run names when filtering data. Do not modify or guess run names.
"""

        # Get plotting code from LLM
        ai_code = llm_client.get_plotting_code(
            df_description, user_question, llm_response
        )

        if not ai_code:
            return None

        print("=== AI Generated Code ===\n", ai_code)

        # Fix common issues in AI-generated code
        ai_code = ai_code.replace("plt.show()", "")  # Remove plt.show() calls
        ai_code = ai_code.replace("plt.show", "")  # Remove plt.show references
        ai_code = ai_code.replace("exit()", "pass")  # Replace exit() with pass
        ai_code = ai_code.replace("sys.exit()", "pass")  # Replace sys.exit() with pass
        ai_code = ai_code.replace(
            "return", "# return"
        )  # Comment out return statements outside functions

        # Execute the code safely
        try:
            local_env = {"plt": plt, "pd": pd, "df": df}

            # Capture stdout to avoid printing during execution
            with contextlib.redirect_stdout(io.StringIO()) as f:
                exec(ai_code, {}, local_env)

            # Get the current figure
            if plt.get_fignums():
                # Generate unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"plot_{timestamp}.png"
                filepath = os.path.join(self.output_dir, filename)

                # Save the plot
                plt.savefig(filepath, dpi=300, bbox_inches="tight")
                plt.close()  # Close to free memory

                print(f"✅ Plot saved to {filepath}")
                return filepath
            else:
                print("⚠️ No plot generated")
                return None

        except SystemExit:
            print("⚠️ AI code tried to exit - prevented crash")
            return None
        except Exception as e:
            print(f"❌ Error executing plotting code: {e}")
            return None

    def create_simple_plot(self, df: pd.DataFrame, user_question: str) -> Optional[str]:
        """Create a simple fallback plot if AI plotting fails"""
        if df.empty:
            return None

        try:
            # Create a simple multi-panel plot
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f"Run Analysis: {user_question}", fontsize=16)

            # Plot 1: Pace vs KM
            for run_name in df["run_name"].unique():
                run_data = df[df["run_name"] == run_name].sort_values(by="km")
                axes[0, 0].plot(
                    run_data["km"], run_data["pace"], label=run_name, marker="o"
                )
            axes[0, 0].set_xlabel("Kilometer")
            axes[0, 0].set_ylabel("Pace (min/km)")
            axes[0, 0].set_title("Pace vs. Kilometer")
            axes[0, 0].legend()
            axes[0, 0].grid(True)

            # Plot 2: Heart Rate vs KM
            for run_name in df["run_name"].unique():
                run_data = df[df["run_name"] == run_name].sort_values(by="km")
                axes[0, 1].plot(
                    run_data["km"], run_data["hr"], label=run_name, marker="s"
                )
            axes[0, 1].set_xlabel("Kilometer")
            axes[0, 1].set_ylabel("Heart Rate (bpm)")
            axes[0, 1].set_title("Heart Rate vs. Kilometer")
            axes[0, 1].legend()
            axes[0, 1].grid(True)

            # Plot 3: Elevation vs KM
            for run_name in df["run_name"].unique():
                run_data = df[df["run_name"] == run_name].sort_values(by="km")
                axes[1, 0].plot(
                    run_data["km"],
                    run_data["elevation_gain"],
                    label=run_name,
                    marker="^",
                )
            axes[1, 0].set_xlabel("Kilometer")
            axes[1, 0].set_ylabel("Elevation Gain (m)")
            axes[1, 0].set_title("Elevation Gain vs. Kilometer")
            axes[1, 0].legend()
            axes[1, 0].grid(True)

            # Plot 4: Summary stats
            summary_data = (
                df.groupby("run_name")
                .agg({"avg_pace": "mean", "avg_hr": "mean", "total_elevation": "mean"})
                .reset_index()
            )

            axes[1, 1].bar(summary_data["run_name"], summary_data["avg_pace"])
            axes[1, 1].set_xlabel("Run")
            axes[1, 1].set_ylabel("Average Pace (min/km)")
            axes[1, 1].set_title("Average Pace by Run")
            axes[1, 1].tick_params(axis="x", rotation=45)
            axes[1, 1].grid(True)

            plt.tight_layout()

            # Save the plot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simple_plot_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)

            plt.savefig(filepath, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"✅ Simple plot saved to {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Error creating simple plot: {e}")
            return None
