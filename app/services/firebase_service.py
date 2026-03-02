import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class FirebaseHistoryService:
    def __init__(self):
        self.db = None
        self.enabled = False
        
        # Look for Firebase key in resources
        # The key should be downloaded from Firebase Console (Settings > Service Accounts)
        key_name = "firebase-key.json"
        key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", key_name)
        
        try:
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
                # Avoid re-initialization if app already initialized
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.enabled = True
                print("Firebase Firestore initialized successfully.")
            else:
                print(f"ALERT: Firebase key not found at {key_path}")
                print("Please download your service-account-key.json from Firebase and rename it to firebase-key.json in the resources folder.")
                self.enabled = False
        except Exception as e:
            print(f"CRITICAL: Error initializing Firebase: {str(e)}")
            self.enabled = False

    def save_history(self, record: Dict[str, Any]) -> str:
        """Saves a validation report to Firestore"""
        if not self.enabled:
            return None
        
        # Firestore handles dynamic schemas, but let's ensure the core fields are there
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
                # Firestore returns datetime objects, but our schema expects them or strings
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
            # For Firestore, simple counts require a full stream if they are small, 
            # or aggregation queries for large collections.
            # Using stream for MVP.
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
        """Deletes a single record"""
        if not self.enabled:
            return False
        try:
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
