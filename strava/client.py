import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
import json
import os


class StravaClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        user_id: str = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.access_token = None
        self.token_expires_at = None

        # Initialize token manager for persistent storage
        if user_id:
            from utils.token_manager import TokenManager

            self.token_manager = TokenManager()
        else:
            self.token_manager = None

    def refresh_access_token(self) -> str:
        """Refresh the access token using refresh token"""
        url = "https://www.strava.com/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(url, data=payload)
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        new_refresh_token = data["refresh_token"]  # Get new refresh token
        self.token_expires_at = data["expires_at"]

        # Update the refresh token in memory
        self.refresh_token = new_refresh_token

        # Persist the new refresh token to .env file
        if self.token_manager and self.user_id:
            # Use TokenManager for user-specific token storage
            success = self.token_manager.update_refresh_token(
                self.user_id, new_refresh_token
            )
            if success:
                print(
                    f"🔄 Access token refreshed successfully. New refresh token saved for user {self.user_id}"
                )
            else:
                print(f"⚠️ Failed to save refresh token for user {self.user_id}")
        else:
            # Fallback to global token update (for backward compatibility)
            self._update_env_refresh_token(new_refresh_token)

        return self.access_token

    def _update_env_refresh_token(self, new_refresh_token: str):
        """Update the global refresh token in the .env file (fallback method)"""
        try:
            # Read the current .env file
            env_path = ".env"
            if not os.path.exists(env_path):
                print("⚠️ .env file not found, cannot update refresh token")
                return

            with open(env_path, "r") as file:
                lines = file.readlines()

            # Find and update the STRAVA_REFRESH_TOKEN line
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("STRAVA_REFRESH_TOKEN="):
                    lines[i] = f"STRAVA_REFRESH_TOKEN={new_refresh_token}\n"
                    updated = True
                    break

            if not updated:
                print("⚠️ STRAVA_REFRESH_TOKEN not found in .env file")
                return

            # Write the updated .env file
            with open(env_path, "w") as file:
                file.writelines(lines)

            print(f"✅ Global refresh token updated in .env file")

        except Exception as e:
            print(f"❌ Error updating refresh token in .env: {e}")
            # Don't fail the token refresh if .env update fails

    def get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary"""
        if not self.access_token or (
            self.token_expires_at and time.time() >= self.token_expires_at
        ):
            return self.refresh_access_token()
        return self.access_token

    def get_activities(self, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
        """Get activities from Strava"""
        url = "https://www.strava.com/api/v3/athlete/activities"
        headers = {"Authorization": f"Bearer {self.get_access_token()}"}
        params = {"per_page": per_page, "page": page}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 429:
            print("⚠️ Rate limit hit. Waiting 15 minutes...")
            time.sleep(15 * 60)
            return self.get_activities(page, per_page)

        response.raise_for_status()
        return response.json()

    def get_activity_streams(self, activity_id: int) -> Dict[str, Any]:
        """Get detailed streams for an activity"""
        url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
        headers = {"Authorization": f"Bearer {self.get_access_token()}"}
        params = {
            "keys": "distance,heartrate,cadence,watts,velocity_smooth,altitude",
            "key_by_type": "true",
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 429:
            print("⚠️ Rate limit hit. Waiting 15 minutes...")
            time.sleep(15 * 60)
            return self.get_activity_streams(activity_id)

        # Handle 404 errors gracefully (manual runs don't have stream data)
        if response.status_code == 404:
            print(
                f"⚠️ No stream data available for activity {activity_id} (likely a manual entry)"
            )
            return {}

        # Handle other errors
        if response.status_code != 200:
            print(
                f"⚠️ Error fetching streams for activity {activity_id}: {response.status_code}"
            )
            return {}

        return response.json()

    def safe_array(self, data: List) -> np.ndarray:
        """Convert a list to a numpy array, replace None with np.nan."""
        if not data:
            return np.array([])
        return np.array([np.nan if v is None else v for v in data], dtype=float)

    def km_wise_data(self, streams: Dict[str, Any]) -> pd.DataFrame:
        """Convert activity streams to per-kilometer data"""
        # Check if we have any stream data
        if not streams:
            print("⚠️ No stream data available - creating fallback data structure")
            return pd.DataFrame()

        dist = self.safe_array(streams.get("distance", {}).get("data", []))
        hr = self.safe_array(streams.get("heartrate", {}).get("data", []))
        cad = self.safe_array(streams.get("cadence", {}).get("data", []))
        watts = self.safe_array(streams.get("watts", {}).get("data", []))
        pace = self.safe_array(streams.get("velocity_smooth", {}).get("data", []))
        alt = self.safe_array(streams.get("altitude", {}).get("data", []))

        if dist.size == 0:
            return pd.DataFrame()

        km_segments = int(dist[-1] // 1000)
        rows = []

        for km in range(1, km_segments + 1):
            mask = (dist >= (km - 1) * 1000) & (dist < km * 1000)
            if mask.sum() == 0:
                continue

            rows.append(
                {
                    "KM": km,
                    "Avg_HR": np.nanmean(hr[mask]) if hr.size else None,
                    "Avg_Cadence": np.nanmean(cad[mask]) if cad.size else None,
                    "Avg_Power": np.nanmean(watts[mask]) if watts.size else None,
                    "Avg_Pace_min_per_km": (1000 / np.nanmean(pace[mask])) / 60
                    if pace.size
                    else None,
                    "Elevation_Gain_m": np.nanmax(alt[mask]) - np.nanmin(alt[mask])
                    if alt.size
                    else None,
                }
            )

        return pd.DataFrame(rows)

    def fetch_all_runs(self, limit: int = None) -> List[pd.DataFrame]:
        """Fetch running activities and convert to dataframes"""
        print("🏃 Fetching running activities from Strava...")

        dfs = []
        page = 1

        while True:
            print(f"📄 Fetching page {page}...")
            activities = self.get_activities(page=page, per_page=30)

            if not activities:
                break

            for act in activities:
                if act["type"] in ["Run", "Trail Run", "Virtual Run"]:
                    print(f"🏃 {act['name']} ({act['start_date_local']})")

                    try:
                        streams = self.get_activity_streams(act["id"])
                        df = self.km_wise_data(streams)

                        # If we have stream data, use it
                        if not df.empty:
                            df["Activity_Name"] = act["name"]
                            df["DateTime"] = pd.to_datetime(act["start_date_local"])
                            df["total_distance"] = df["KM"].max()
                            df["run_type"] = (
                                df["Activity_Name"].str.split(" Run").str[0]
                            )
                            dfs.append(df)
                        else:
                            # Create fallback data for manual runs without stream data
                            print(
                                f"📝 Creating fallback data for manual run: {act['name']}"
                            )
                            fallback_df = self.create_fallback_data(act)
                            if fallback_df is not None:
                                dfs.append(fallback_df)

                        # Check if we've reached the limit
                        if limit and len(dfs) >= limit:
                            print(f"✅ Reached limit of {limit} runs.")
                            return dfs

                    except Exception as e:
                        print(f"⚠️ Error processing activity {act['id']}: {e}")
                        # Try to create fallback data even if there's an error
                        try:
                            fallback_df = self.create_fallback_data(act)
                            if fallback_df is not None:
                                dfs.append(fallback_df)
                        except Exception as fallback_error:
                            print(f"❌ Failed to create fallback data: {fallback_error}")

                    time.sleep(1)  # avoid rate limit

            page += 1
            time.sleep(2)  # pause between pages

        print(f"✅ Collected {len(dfs)} runs.")
        return dfs

    def convert_to_json_list(self, dfs: List[pd.DataFrame]) -> List[str]:
        """Convert dataframes to JSON list format"""
        json_list = []

        for df in dfs:
            result = []
            for activity_name, group in df.groupby("Activity_Name"):
                DateTime = group["DateTime"].iloc[0].strftime("%Y-%m-%d %H:%M:%S")
                Distance = group["total_distance"].iloc[0].astype(float)
                run_type = group["run_type"].iloc[0]

                # Handle missing data gracefully and ensure JSON serializable types
                avg_hr = group["Avg_HR"].mean()
                if pd.notna(avg_hr):
                    avg_hr = float(round(avg_hr, 2))
                else:
                    avg_hr = None

                avg_cadence = group["Avg_Cadence"].mean()
                if pd.notna(avg_cadence):
                    avg_cadence = float(round(avg_cadence, 2))
                else:
                    avg_cadence = None

                avg_power = group["Avg_Power"].mean()
                if pd.notna(avg_power):
                    avg_power = float(round(avg_power, 2))
                else:
                    avg_power = None

                avg_pace = group["Avg_Pace_min_per_km"].mean()
                if pd.notna(avg_pace):
                    avg_pace = float(round(avg_pace, 2))
                else:
                    avg_pace = None

                total_elev_gain = group["Elevation_Gain_m"].sum()
                if pd.notna(total_elev_gain):
                    total_elev_gain = float(round(total_elev_gain, 1))
                else:
                    total_elev_gain = 0.0

                # Create splits with proper handling of missing data
                splits = []
                for _, row in group.iterrows():
                    split_data = {
                        "KM": int(float(row["KM"])) if pd.notna(row["KM"]) else 1,
                        "Avg_HR": float(round(row["Avg_HR"], 2))
                        if pd.notna(row["Avg_HR"])
                        else None,
                        "Avg_Cadence": float(round(row["Avg_Cadence"], 2))
                        if pd.notna(row["Avg_Cadence"])
                        else None,
                        "Avg_Power": float(round(row["Avg_Power"], 2))
                        if pd.notna(row["Avg_Power"])
                        else None,
                        "Avg_Pace_min_per_km": float(
                            round(row["Avg_Pace_min_per_km"], 2)
                        )
                        if pd.notna(row["Avg_Pace_min_per_km"])
                        else None,
                        "Elevation_Gain_m": float(round(row["Elevation_Gain_m"], 1))
                        if pd.notna(row["Elevation_Gain_m"])
                        else 0.0,
                    }
                    splits.append(split_data)

                result.append(
                    {
                        "Name": activity_name,
                        "DateTime": DateTime,
                        "Distance": Distance,
                        "Run_Type": run_type,
                        "Avg_HR": avg_hr,
                        "Avg_Pace": avg_pace,
                        "Avg_Cadence": avg_cadence,
                        "Avg_Power": avg_power,
                        "Elevation_Gain_m": total_elev_gain,
                        "Splits": splits,
                    }
                )

            json_output = json.dumps(result, indent=2)
            json_list.append(json_output)

        return json_list

    def create_fallback_data(self, activity: Dict[str, Any]) -> pd.DataFrame:
        """Create fallback data structure for manual runs without stream data"""
        try:
            # Extract basic activity information
            name = activity.get("name", "Unknown Run")
            distance = activity.get("distance", 0) / 1000  # Convert meters to km
            moving_time = activity.get("moving_time", 0)  # seconds
            total_elevation_gain = activity.get("total_elevation_gain", 0)
            average_heartrate = activity.get("average_heartrate")
            average_speed = activity.get("average_speed", 0)  # m/s

            # Calculate average pace from speed
            avg_pace_min_per_km = (
                (distance * 1000) / average_speed / 60 if average_speed > 0 else None
            )

            # Create a single row representing the entire run
            fallback_data = {
                "KM": [1],  # Single kilometer segment
                "Avg_HR": [average_heartrate] if average_heartrate else [None],
                "Avg_Cadence": [None],  # No cadence data for manual runs
                "Avg_Power": [None],  # No power data for manual runs
                "Avg_Pace_min_per_km": [avg_pace_min_per_km],
                "Elevation_Gain_m": [total_elevation_gain],
                "Activity_Name": [name],
                "DateTime": [pd.to_datetime(activity.get("start_date_local"))],
                "total_distance": [distance],
                "run_type": [name.split(" Run")[0] if " Run" in name else "Unknown"],
            }

            df = pd.DataFrame(fallback_data)
            print(
                f"✅ Created fallback data for {name}: {distance:.1f}km, {moving_time//60}min"
            )
            return df

        except Exception as e:
            print(f"❌ Error creating fallback data: {e}")
            return None
