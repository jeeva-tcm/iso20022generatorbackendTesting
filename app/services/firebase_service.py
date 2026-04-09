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
                print(f"DEBUG: FIREBASE_PROJECT_ID: {'SET' if os.getenv('FIREBASE_PROJECT_ID') else 'MISSING'}")
                print(f"DEBUG: FIREBASE_PRIVATE_KEY: {'SET' if os.getenv('FIREBASE_PRIVATE_KEY') else 'MISSING'}")
                print(f"DEBUG: FIREBASE_CLIENT_EMAIL: {'SET' if os.getenv('FIREBASE_CLIENT_EMAIL') else 'MISSING'}")
                print(f"DEBUG: FIREBASE_KEY_PATH: {'SET' if os.getenv('FIREBASE_KEY_PATH') else 'MISSING'}")
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
            # Handle cases where the key might have been pasted with literal quotes into the env UI
            if private_key.startswith('"') and private_key.endswith('"'):
                private_key = private_key[1:-1]
            # Also handle single quotes for good measure
            if private_key.startswith("'") and private_key.endswith("'"):
                private_key = private_key[1:-1]
            # Strip again in case there was space inside quotes
            private_key = private_key.strip()

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
        
        if "deleted" not in record:
            record["deleted"] = False
            
        doc_id = record["validation_id"]
        if record.get("file_id"):
            doc_id = f"{record['validation_id']}_{record['file_id']}"
            
        doc_ref = self.db.collection("validation_history").document(doc_id)
        doc_ref.set(record)
        return doc_id

    def get_history(self, skip: int = 0, limit: int = 5000) -> List[Dict[str, Any]]:
        """Retrieves history records from Firestore"""
        if not self.enabled:
            return []
            
        try:
            # We filter for deleted=False in Python to avoid requiring a composite index in Firestore.
            query = self.db.collection("validation_history") \
                          .order_by("timestamp", direction=firestore.Query.DESCENDING)
            
            docs = query.stream()
            results = []
            count = 0
            for doc in docs:
                data = doc.to_dict()
                if not data.get("deleted", False):
                    if count >= skip:
                        results.append(data)
                    count += 1
                    if len(results) >= limit:
                        break
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
                data = doc.to_dict()
                if data.get("deleted", False):
                    continue
                    
                total += 1
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
                    batch.update(doc.reference, {"deleted": True})
                batch.commit()
                return True
                
            # Fallback to soft deleting by document ID (validation_id)
            self.db.collection("validation_history").document(validation_id).update({"deleted": True})
            return True
        except:
            return False

    def delete_all(self) -> int:
        """Deletes all records from the collection"""
        if not self.enabled:
            return 0
        
        try:
            # Firestore batch update (up to 500 at a time)
            batch = self.db.batch()
            docs = list(self.db.collection("validation_history").stream())
            count = 0
            for doc in docs:
                if not doc.to_dict().get("deleted", False):
                    batch.update(doc.reference, {"deleted": True})
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

    def reset_all_counters(self):
        """Deletes all documents in the validation_counters collection to reset sequences"""
        if not self.enabled:
            return
        try:
            docs = list(self.db.collection("validation_counters").stream())
            batch = self.db.batch()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            if count % 500 != 0:
                batch.commit()
            print(f"Reset {count} counter document(s) in Firebase.")
        except Exception as e:
            print(f"Error resetting counters: {e}")

    def hard_delete_all(self) -> int:
        """
        HARD deletes all records from validation_history AND resets validation_counters.
        This is a full wipe — documents are permanently removed from Firestore.
        """
        if not self.enabled:
            return 0
        
        total_deleted = 0
        try:
            # 1. Hard delete all validation_history documents
            docs = list(self.db.collection("validation_history").stream())
            batch = self.db.batch()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            if count % 500 != 0:
                batch.commit()
            total_deleted = count
            
            # 2. Reset all counters
            self.reset_all_counters()
            
            print(f"Hard deleted {total_deleted} history documents and reset all counters.")
        except Exception as e:
            print(f"Error during hard delete: {e}")
        
        return total_deleted

    def get_detail(self, validation_id: str) -> Optional[Dict[str, Any]]:
        """Gets full report and original message"""
        if not self.enabled:
            return None
        try:
            doc = self.db.collection("validation_history").document(validation_id).get()
            if doc.exists:
                data = doc.to_dict()
                if not data.get("deleted", False):
                    return data
            return None
        except Exception as e:
            print(f"Error fetching detail: {e}")
            return None

    def get_next_sequence(self, date_str: str) -> int:
        """
        Atomically increments and returns the sequence number for a given date.
        This ensures that validation IDs (VAL{DDMMYY}XXXXX) are unique and sequential 
        across server restarts and multiple instances.
        """
        if not self.enabled:
            return None
            
        doc_ref = self.db.collection("validation_counters").document(date_str)
        try:
            # Use a transaction to ensure atomicity
            transaction = self.db.transaction()
            
            @firestore.transactional
            def get_and_increment(transaction):
                snapshot = doc_ref.get(transaction=transaction)
                if snapshot.exists:
                    new_seq = snapshot.get("seq") + 1
                    transaction.update(doc_ref, {"seq": new_seq})
                else:
                    new_seq = 1
                    transaction.set(doc_ref, {"seq": 1})
                return new_seq
                
            return get_and_increment(transaction)
        except Exception as e:
            print(f"Firebase counter error: {e}")
            return None

    def check_duplicate_msg_uetr(self, msg_id: str, uetr: str) -> bool:
        """
        Checks Firestore for any existing validation history record with the
        same MsgId and UETR combination.
        """
        if not self.enabled:
            return False
            
        try:
            # Search for documents where message_type contains pacs.009 (optional but narrows search)
            # and report_json. GrpHdr.MsgId matches OR report_json hasMsgId/UETR at certain paths
            # Since report_json is a nested dict, Firestore allows querying nested fields.
            
            # The most direct way given save_history structure is to query original_message OR the report_json
            # report_json contains the full report. We can also index MsgId and UETR during save_history for faster lookup.
            
            # For now, let's query based on the original structure saved in save_history
            # MsgId is saved in report_json["GrpHdr"]["MsgId"] (usually)
            # UETR is saved in report_json["CdtTrfTxInf"]["PmtId"]["UETR"]
            
            # However, the record itself has some flattened fields.
            # Let's check if we have msg_id / uetr in the record. No, they are in report_json.
            
            # To make this performant without deep nested queries, 
            # we should ideally add 'msg_id' and 'uetr' to the record dict in main.py.
            
            # Let's try searching via where clauses on properties we know.
            # We'll use a slightly broader query and filter in Python if needed, 
            # but Firestore where() is better.
            
            query = self.db.collection("validation_history") \
                        .where("deleted", "==", False) \
                        .where("report_json.metadata.MsgId", "==", msg_id) \
                        .stream()
            
            for doc in query:
                data = doc.to_dict()
                report = data.get("report_json", {})
                metadata = report.get("metadata", {})
                
                if metadata.get("UETR") == uetr:
                    return True
                    
            return False
        except Exception as e:
            print(f"Error checking duplicate MsgId/UETR in Firestore: {e}")
            return False

