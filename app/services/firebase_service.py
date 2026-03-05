import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load .env from the backend root (two levels up from this file)
_backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_backend_root, ".env"))


class FirebaseHistoryService:
    def __init__(self):
        self.db = None
        self.enabled = False

        try:
            cred = self._build_credentials()
            if cred is not None:
                # Avoid re-initialization if app already initialized
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.enabled = True
                print("Firebase Firestore initialized successfully.")
            else:
                print("ALERT: No Firebase credentials found.")
                print("Please configure your .env file with Firebase credentials.")
                print("See .env.example for reference.")
                self.enabled = False
        except Exception as e:
            print(f"CRITICAL: Error initializing Firebase: {str(e)}")
            self.enabled = False

    @staticmethod
    def _build_credentials():
        """
        Build Firebase credentials from environment variables.

        Priority:
        1. Inline env vars (FIREBASE_PROJECT_ID + FIREBASE_PRIVATE_KEY + ...)
        2. FIREBASE_KEY_PATH env var pointing to a JSON key file
        3. Legacy fallback: firebase-key.json in app/resources/
        """

        # --- Option 1: Inline credentials from env vars ---
        project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        private_key = os.getenv("FIREBASE_PRIVATE_KEY", "").strip()
        client_email = os.getenv("FIREBASE_CLIENT_EMAIL", "").strip()

        if project_id and private_key and client_email:
            # Fix escaped newlines (common when pasting from .env files)
            private_key = private_key.replace("\\n", "\n")

            cert_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID", ""),
                "private_key": private_key,
                "client_email": client_email,
                "client_id": os.getenv("FIREBASE_CLIENT_ID", ""),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": os.getenv(
                    "FIREBASE_AUTH_PROVIDER_CERT_URL",
                    "https://www.googleapis.com/oauth2/v1/certs"
                ),
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL", ""),
            }
            print("Using inline Firebase credentials from environment variables.")
            return credentials.Certificate(cert_dict)

        # --- Option 2: Key file path from env var ---
        key_path_env = os.getenv("FIREBASE_KEY_PATH", "").strip()
        if key_path_env:
            # Resolve relative paths from the backend root
            if not os.path.isabs(key_path_env):
                key_path_env = os.path.join(_backend_root, key_path_env)
            if os.path.exists(key_path_env):
                print(f"Using Firebase key file from FIREBASE_KEY_PATH: {key_path_env}")
                return credentials.Certificate(key_path_env)
            else:
                print(f"WARNING: FIREBASE_KEY_PATH is set but file not found: {key_path_env}")

        # --- Option 3: Legacy fallback ---
        legacy_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "resources", "firebase-key.json"
        )
        if os.path.exists(legacy_path):
            print(f"Using legacy Firebase key file: {legacy_path}")
            return credentials.Certificate(legacy_path)

        return None

    def save_history(self, record: Dict[str, Any]) -> str:
        """Saves a validation report to Firestore"""
        if not self.enabled:
            return None
        
        # Convert timestamp to native Firestore timestamp if it's a datetime
        if "timestamp" not in record:
            record["timestamp"] = datetime.now(timezone.utc)
        elif isinstance(record["timestamp"], str):
            # Parse ISO string if needed
            try:
                record["timestamp"] = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
            except:
                record["timestamp"] = datetime.now(timezone.utc)
            
        doc_ref = self.db.collection("validation_history").document(record["validation_id"])
        doc_ref.set(record)
        return record["validation_id"]

    def get_history(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves history records from Firestore"""
        if not self.enabled:
            return []
            
        try:
            query = self.db.collection("validation_history") \
                          .order_by("timestamp", direction=firestore.Query.DESCENDING) \
                          .offset(skip).limit(limit)
            
            docs = query.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                results.append(data)
            return results
        except Exception as e:
            print(f"Error fetching Firestore history: {e}")
            return []

    def get_stats(self) -> Dict[str, int]:
        """Calculates dashboard stats from Firestore"""
        if not self.enabled:
            return {"total_audits": 0, "passed_messages": 0, "failed_messages": 0, "validation_quality": 0}
            
        try:
            docs = self.db.collection("validation_history").stream()
            total = 0
            passed = 0
            failed = 0
            
            for doc in docs:
                total += 1
                data = doc.to_dict()
                if data.get("status") == "PASS":
                    passed += 1
                elif data.get("status") == "FAIL":
                    failed += 1
                    
            quality = round((passed / total) * 100) if total > 0 else 0
            return {
                "total_audits": total,
                "passed_messages": passed,
                "failed_messages": failed,
                "validation_quality": quality
            }
        except Exception as e:
            print(f"Error calculating stats from Firestore: {e}")
            return {"total_audits": 0, "passed_messages": 0, "failed_messages": 0, "validation_quality": 0}

    def delete_record(self, validation_id: str) -> bool:
        """Deletes a single record or a batch depending on the provided ID"""
        if not self.enabled:
            return False
        try:
            # First, try deleting by batch_id
            docs = list(self.db.collection("validation_history").where("batch_id", "==", validation_id).stream())
            if docs:
                batch = self.db.batch()
                for doc in docs:
                    batch.delete(doc.reference)
                batch.commit()
                return True
                
            # Fallback to deleting by document ID (validation_id)
            self.db.collection("validation_history").document(validation_id).delete()
            return True
        except:
            return False

    def delete_all(self) -> int:
        """Deletes all records from the collection"""
        if not self.enabled:
            return 0
        
        try:
            # Firestore batch delete (up to 500 at a time)
            batch = self.db.batch()
            docs = list(self.db.collection("validation_history").stream())
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            if count % 500 != 0:
                batch.commit()
            
            return count
        except Exception as e:
            print(f"Error during batch delete: {e}")
            return 0

    def get_detail(self, validation_id: str) -> Optional[Dict[str, Any]]:
        """Gets full report and original message"""
        if not self.enabled:
            return None
        try:
            doc = self.db.collection("validation_history").document(validation_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error fetching detail: {e}")
            return None
