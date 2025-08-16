from langchain_chroma import Chroma
from langchain.schema import Document
from typing import List, Dict, Any
import os
import json
from datetime import datetime


class ChromaManager:
    def __init__(self, db_dir: str, embeddings):
        self.db_dir = db_dir
        self.embeddings = embeddings
        self.vectorstore = None
        self._load_or_create_db()

    def _load_or_create_db(self):
        """Load existing ChromaDB or create new one"""
        if os.path.exists(self.db_dir):
            self.vectorstore = Chroma(
                persist_directory=self.db_dir, embedding_function=self.embeddings
            )
        else:
            # Create new empty vectorstore - newer ChromaDB versions automatically persist
            self.vectorstore = Chroma(
                embedding_function=self.embeddings, persist_directory=self.db_dir
            )

    def add_documents(self, docs: List[Document]):
        """Add documents to ChromaDB"""
        if not docs:
            return

        # Add documents - newer ChromaDB versions automatically persist
        self.vectorstore.add_documents(docs)

        print(f"✅ Added {len(docs)} documents to ChromaDB")

    def get_existing_run_names(self) -> List[str]:
        """Get list of existing run names to avoid duplicates"""
        if not self.vectorstore:
            return []

        # Get all documents and extract run names
        all_docs = self.vectorstore.get()
        if not all_docs or not all_docs["documents"]:
            return []

        run_names = []
        for metadata in all_docs["metadatas"]:
            if metadata and "name" in metadata:
                run_names.append(metadata["name"])

        return run_names

    def retrieve_runs(self, query: Dict[str, Any], top_k: int = 20) -> List[Document]:
        """Retrieve runs based on structured query"""
        if not self.vectorstore:
            return []

        # 1. Decide primary filter for Chroma
        primary_filter = None
        if query.get("type") and query["type"] is not None:
            primary_filter = {"type": query["type"]}

        # 2. Get initial docs
        if primary_filter:
            retriever = self.vectorstore.as_retriever(
                search_kwargs={"filter": primary_filter, "k": top_k * 3}
            )
        else:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": top_k * 3})

        # 3. Get initial docs
        docs = retriever.invoke("")

        # 4. Post-filter based on all interpreter fields
        filtered_docs = []
        for doc in docs:
            meta = doc.metadata

            if (
                query.get("type")
                and query["type"] is not None
                and meta.get("type") != query["type"]
            ):
                continue
            if (
                query.get("min_avg_hr")
                and query["min_avg_hr"] is not None
                and meta.get("avg_hr", 0) < query["min_avg_hr"]
            ):
                continue
            if (
                query.get("max_avg_hr")
                and query["max_avg_hr"] is not None
                and meta.get("avg_hr", 9999) > query["max_avg_hr"]
            ):
                continue
            if (
                query.get("distance_km")
                and query["distance_km"] is not None
                and meta.get("distance") < query["distance_km"]
            ):
                continue
            if (
                query.get("start_date")
                and query["start_date"] is not None
                and meta.get("date") < query["start_date"]
            ):
                continue
            if (
                query.get("end_date")
                and query["end_date"] is not None
                and meta.get("date") > query["end_date"]
            ):
                continue

            # Check if specific run names are requested
            if query.get("run_names") and query["run_names"] is not None:
                run_name = meta.get("name", "")
                if not any(
                    name.lower() in run_name.lower() for name in query["run_names"]
                ):
                    continue

            filtered_docs.append(doc)

        # 5. If last_n_runs is set, take the most recent
        if query.get("last_n_runs") and query["last_n_runs"] is not None:
            filtered_docs.sort(key=lambda x: x.metadata.get("date", ""), reverse=True)
            filtered_docs = filtered_docs[: query["last_n_runs"]]

        return filtered_docs[:top_k]

    def get_runs_by_names(self, run_names: List[str]) -> List[Document]:
        """Get runs by specific names for better performance"""
        if not self.vectorstore:
            return []

        # Get all documents
        all_docs = self.vectorstore.get()
        if not all_docs or not all_docs["documents"]:
            return []

        # Convert to Document objects
        docs = []
        for i, content in enumerate(all_docs["documents"]):
            doc = Document(
                page_content=content,
                metadata=all_docs["metadatas"][i] if all_docs["metadatas"] else {},
            )
            docs.append(doc)

        # Filter by run names (case-insensitive partial matching)
        matching_docs = []
        for doc in docs:
            run_name = doc.metadata.get("name", "")
            if any(name.lower() in run_name.lower() for name in run_names):
                matching_docs.append(doc)

        return matching_docs

    def get_latest_runs(self, n: int = 5) -> List[Document]:
        """Get the latest N runs when no documents match query"""
        if not self.vectorstore:
            return []

        # Get all documents
        all_docs = self.vectorstore.get()
        if not all_docs or not all_docs["documents"]:
            return []

        # Convert to Document objects
        docs = []
        for i, content in enumerate(all_docs["documents"]):
            doc = Document(
                page_content=content,
                metadata=all_docs["metadatas"][i] if all_docs["metadatas"] else {},
            )
            docs.append(doc)

        # Sort by date and return latest N
        # Handle date sorting more robustly
        def get_date_key(doc):
            date_str = doc.metadata.get("date", "")
            try:
                # Try to parse the date string
                from datetime import datetime

                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                # If parsing fails, use the string as is (will sort alphabetically)
                return date_str

        docs.sort(key=get_date_key, reverse=True)
        return docs[:n]

    def docs_to_context(
        self, docs: List[Document], include_per_km: bool = False
    ) -> str:
        """Convert list of Document objects to a string context for the LLM"""
        if not docs:
            return "No run data available."

        context_lines = []
        for doc in docs:
            meta = doc.metadata
            line = (
                f"\n{meta.get('date')} | {meta.get('name')} | "
                f"Distance: {meta.get('distance')} km | "
                f"Pace: {meta.get('pace')} min/km | "
                f"Avg HR: {meta.get('avg_hr')} bpm | "
                f"Elevation: {meta.get('elevation_gain')} m | "
                f"Type: {meta.get('type')}"
            )
            context_lines.append(line)

            if include_per_km:
                # append the per-KM breakdown from page_content
                km_data = "\n".join(
                    doc.page_content.split("\n")[8:]
                )  # skips first summary lines
                context_lines.append(km_data)

        return "\n".join(context_lines)

    def context_to_dataframe(self, context: str) -> "pd.DataFrame":
        """Convert context string to pandas DataFrame for plotting"""
        import pandas as pd
        import re

        rows = []
        current_run = {}

        for line in context.splitlines():
            line = line.strip()
            if not line:
                continue

            # Header line: date | run_name | Distance | Pace | Avg HR | Elevation | Type
            if re.match(r"^\d{4}-\d{2}-\d{2}", line):
                parts = line.split("|")
                if len(parts) >= 7:
                    current_run = {
                        "date": parts[0].strip(),
                        "run_name": parts[1].strip(),
                        "distance": float(re.findall(r"[\d.]+", parts[2])[0])
                        if re.findall(r"[\d.]+", parts[2])
                        else 0,
                        "avg_pace": float(re.findall(r"[\d.]+", parts[3])[0])
                        if re.findall(r"[\d.]+", parts[3])
                        else 0,
                        "avg_hr": float(re.findall(r"[\d.]+", parts[4])[0])
                        if re.findall(r"[\d.]+", parts[4])
                        else 0,
                        "total_elevation": float(re.findall(r"[\d.]+", parts[5])[0])
                        if re.findall(r"[\d.]+", parts[5])
                        else 0,
                        "run_type": parts[6].strip().replace("Type: ", ""),
                    }
                continue

            # Per-KM breakdown: KM 1: Pace 8.409 min/km, HR 142.024 bpm, Power 175.074 W, Elevation Gain 8.4 m
            if line.startswith("KM"):
                try:
                    km_num = int(re.findall(r"KM (\d+)", line)[0])
                    pace = (
                        float(re.findall(r"Pace ([\d.]+)", line)[0])
                        if re.findall(r"Pace ([\d.]+)", line)
                        else 0
                    )
                    hr = (
                        float(re.findall(r"HR ([\d.]+)", line)[0])
                        if re.findall(r"HR ([\d.]+)", line)
                        else 0
                    )
                    power = (
                        float(re.findall(r"Power ([\d.]+)", line)[0])
                        if re.findall(r"Power ([\d.]+)", line)
                        else 0
                    )
                    elevation_gain = (
                        float(re.findall(r"Elevation Gain ([\d.]+)", line)[0])
                        if re.findall(r"Elevation Gain ([\d.]+)", line)
                        else 0
                    )

                    rows.append(
                        {
                            "date": current_run.get("date", ""),
                            "run_name": current_run.get("run_name", ""),
                            "run_type": current_run.get("run_type", ""),
                            "km": km_num,
                            "pace": pace,
                            "hr": hr,
                            "power": power,
                            "elevation_gain": elevation_gain,
                            "distance": current_run.get("distance", 0),
                            "avg_hr": current_run.get("avg_hr", 0),
                            "avg_pace": current_run.get("avg_pace", 0),
                            "total_elevation": current_run.get("total_elevation", 0),
                        }
                    )
                except (IndexError, ValueError):
                    continue

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])

        return df
