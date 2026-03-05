from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import csv
import io

from .schemas import validation as schemas
from .services.validator import ISOValidator
from .services.firebase_service import FirebaseHistoryService
from .services.schema_generator import SchemaGenerator

# Initialize services
validator = ISOValidator()
history_service = FirebaseHistoryService()

# DEPRECATED: SQLite Initialization
# database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="ISO 20022 Validation API (Firebase Powered)")

# Configure CORS
origins_str = os.getenv("CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200")
origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/validate", response_model=schemas.ValidationResponse)
async def validate_message(
    request: schemas.ValidationRequest
):
    report = await validator.validate(request.xml_content, request.mode, request.message_type)
    report_dict = report.to_dict()
    
    if request.store_in_history:
        record = {
            "validation_id": report_dict["validation_id"],
            "batch_id": request.batch_id or report_dict["validation_id"],
            "timestamp": report_dict["timestamp"], # Already in report
            "message_type": report_dict["message"],
            "status": report_dict["status"],
            "total_errors": report_dict["errors"],
            "total_warnings": report_dict["warnings"],
            "execution_time_ms": report_dict["total_time_ms"],
            "report_json": report_dict,
            "original_message": request.xml_content
        }
        history_service.save_history(record)
    
    return report_dict

@app.post("/validate-file", response_model=schemas.ValidationResponse)
async def validate_file(
    file: UploadFile = File(...),
    mode: str = Form("Full 1-3"),
    message_type: str = Form("Auto-detect"),
    store_in_history: bool = Form(True),
    batch_id: Optional[str] = Form(None)
):
    content = await file.read()
    xml_content = content.decode("utf-8")
    
    report = await validator.validate(xml_content, mode, message_type, filename=file.filename)
    report_dict = report.to_dict()
    
    if store_in_history:
        record = {
            "validation_id": report_dict["validation_id"],
            "batch_id": batch_id or report_dict["validation_id"],
            "timestamp": report_dict["timestamp"],
            "message_type": report_dict["message"],
            "status": report_dict["status"],
            "total_errors": report_dict["errors"],
            "total_warnings": report_dict["warnings"],
            "execution_time_ms": report_dict["total_time_ms"],
            "report_json": report_dict,
            "original_message": xml_content
        }
        history_service.save_history(record)
    
    return report_dict

@app.get("/history", response_model=List[schemas.HistorySummary])
def get_history(skip: int = 0, limit: int = 100):
    return history_service.get_history(skip, limit)

@app.get("/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats():
    """Get aggregated dashboard statistics from Firestore"""
    return history_service.get_stats()

@app.get("/history/export")
def export_history():
    try:
        results = history_service.get_history(limit=50000) # Max export
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Timestamp", "Validation ID", "Message Type", "Status", "Errors", "Warnings", "Duration (ms)"])
        
        for row in results:
            ts = row.get("timestamp")
            # Handle Firestore Timestamp or datetime
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)
            
            writer.writerow([
                f"{ts_str} (UTC)",
                row.get("validation_id"),
                row.get("message_type"),
                row.get("status"),
                row.get("total_errors"),
                row.get("total_warnings"),
                row.get("execution_time_ms")
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=iso20022_audit_trail.csv",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        print(f"EXPORT ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/history/{validation_id}")
def get_history_detail(validation_id: str):
    detail = history_service.get_detail(validation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Validation not found")
    return {
        "report": detail.get("report_json"),
        "original_message": detail.get("original_message")
    }

@app.delete("/history")
def delete_all_history():
    num_deleted = history_service.delete_all()
    return {"message": f"Deleted {num_deleted} records successfully"}

@app.delete("/history/{validation_id}")
def delete_history_record(validation_id: str):
    success = history_service.delete_record(validation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Validation not found or delete failed")
    return {"message": "Record deleted successfully"}

@app.get("/messages", response_model=List[str])
def get_messages():
    return validator.get_supported_messages()

@app.get("/messages/{message_type}/schema")
def get_message_schema(message_type: str):
    """Dynamically extract the schema tree for a specific MX message type"""
    xsd_path = validator._get_xsd_path(message_type)
    if not xsd_path or not os.path.exists(xsd_path):
        raise HTTPException(status_code=404, detail=f"Schema not found for {message_type}")
    
    schema_tree = SchemaGenerator.get_schema_tree(xsd_path)
    if not schema_tree:
        raise HTTPException(status_code=500, detail=f"Failed to generate schema tree for {message_type}")
    
    return schema_tree

# --- GLOBALLY READY: Serve Frontend ---
# This allows the backend to serve the frontend UI in a production environment
frontend_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(frontend_path):
    app.mount("/ui", StaticFiles(directory=frontend_path, html=True), name="ui")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # If it looks like an API call or file with extension, don't interfere
        if full_path.startswith("api") or "." in full_path:
            return None # standard fastapi behavior
        
        # Otherwise, serve index.html for SPA routing
        index_file = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"status": "ok", "info": "Frontend build folder found but index.html missing."}

@app.get("/")
def health_check():
    # If frontend exists, redirect to UI
    if os.path.exists(frontend_path):
        return FileResponse(os.path.join(frontend_path, "index.html"))
    return {"status": "ok", "service": "ISO 20022 Validator", "info": "Run frontend on port 4200 or build it into backend/app/static"}
