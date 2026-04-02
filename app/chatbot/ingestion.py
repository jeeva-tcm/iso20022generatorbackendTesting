"""
ISO 20022 RAG Chatbot - Document Ingestion & Chunking
Reads XSD schemas, JSON validation rules, MT mapping files, and Python validators
to build a knowledge base for the RAG chatbot.
"""

import os
import re
import json
import hashlib
from typing import List, Dict


def _chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += max_chars - overlap
    return chunks


def _generate_chunk_id(source: str, idx: int) -> str:
    return hashlib.md5(f"{source}:{idx}".encode()).hexdigest()


def ingest_xsd_files(xsd_dir: str) -> List[Dict]:
    """
    Parse XSD files and extract meaningful chunks:
    - Complex type definitions
    - Simple type definitions (enums, patterns)
    - Element declarations
    """
    documents = []
    if not os.path.isdir(xsd_dir):
        return documents

    for fname in os.listdir(xsd_dir):
        if not fname.endswith(".xsd"):
            continue
        fpath = os.path.join(xsd_dir, fname)
        msg_type = fname.replace(".xsd", "")

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Extract message category info from filename
        parts = msg_type.split(".")
        category = parts[0] if parts else msg_type
        category_upper = category.upper()

        # 1) Extract each complexType block as a chunk
        complex_types = re.findall(
            r'(<xs:complexType\s+name="([^"]+)".*?</xs:complexType>)',
            content,
            re.DOTALL,
        )
        for idx, (block, type_name) in enumerate(complex_types):
            # Extract element names within this type
            elements = re.findall(r'name="([^"]+)"', block)
            elements_str = ", ".join(elements[:15])

            summary = (
                f"ISO 20022 schema definition for complex type '{type_name}' "
                f"in message {msg_type}. "
                f"Contains elements: {elements_str}."
            )

            # Sub-chunk if too large
            for ci, chunk in enumerate(_chunk_text(block, 1200, 150)):
                documents.append(
                    {
                        "id": _generate_chunk_id(f"xsd:{msg_type}:{type_name}", ci),
                        "text": f"{summary}\n\n{chunk}",
                        "metadata": {
                            "source": fname,
                            "type": "xsd_complex_type",
                            "message_type": msg_type,
                            "category": category_upper,
                            "complex_type": type_name,
                        },
                    }
                )

        # 2) Extract simpleType definitions (enumerations / patterns)
        simple_types = re.findall(
            r'(<xs:simpleType\s+name="([^"]+)".*?</xs:simpleType>)',
            content,
            re.DOTALL,
        )
        for idx, (block, type_name) in enumerate(simple_types):
            enums = re.findall(r'value="([^"]+)"', block)
            patterns = re.findall(r'<xs:pattern\s+value="([^"]+)"', block)

            desc_parts = [f"Simple type '{type_name}' in {msg_type}."]
            if enums:
                desc_parts.append(f"Allowed values: {', '.join(enums[:20])}")
            if patterns:
                desc_parts.append(f"Pattern: {patterns[0]}")

            summary = " ".join(desc_parts)

            documents.append(
                {
                    "id": _generate_chunk_id(f"xsd_simple:{msg_type}:{type_name}", 0),
                    "text": f"{summary}\n\n{block}",
                    "metadata": {
                        "source": fname,
                        "type": "xsd_simple_type",
                        "message_type": msg_type,
                        "category": category_upper,
                        "simple_type": type_name,
                    },
                }
            )

        # 3) Overall document summary
        root_element = re.search(r'<xs:element\s+name="Document"', content)
        doc_type_match = re.search(
            r'<xs:element\s+name="([^"]+)"\s+type="([^"]+)"',
            content[content.find("Document") :] if root_element else content,
        )
        root_msg = doc_type_match.group(1) if doc_type_match else msg_type

        documents.append(
            {
                "id": _generate_chunk_id(f"xsd_overview:{msg_type}", 0),
                "text": (
                    f"ISO 20022 message schema overview for {msg_type} ({category_upper} category). "
                    f"Root element: Document > {root_msg}. "
                    f"Contains {len(complex_types)} complex types and {len(simple_types)} simple types. "
                    f"This schema defines the XML structure for {msg_type} messages used in SWIFT financial messaging."
                ),
                "metadata": {
                    "source": fname,
                    "type": "xsd_overview",
                    "message_type": msg_type,
                    "category": category_upper,
                },
            }
        )

    return documents


def ingest_json_rules(rules_dir: str) -> List[Dict]:
    """Ingest JSON validation rules files."""
    documents = []
    if not os.path.isdir(rules_dir):
        return documents

    for fname in os.listdir(rules_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(rules_dir, fname)
        rule_name = fname.replace(".json", "")

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        content_str = json.dumps(data, indent=2)

        for ci, chunk in enumerate(_chunk_text(content_str, 1500, 200)):
            summary = (
                f"ISO 20022 validation rules from '{fname}'. "
                f"These rules define validation logic, field constraints, and business rules "
                f"for SWIFT ISO 20022 message processing."
            )
            documents.append(
                {
                    "id": _generate_chunk_id(f"rule:{rule_name}", ci),
                    "text": f"{summary}\n\n{chunk}",
                    "metadata": {
                        "source": fname,
                        "type": "validation_rule",
                        "rule_name": rule_name,
                    },
                }
            )

    return documents


def ingest_mt_mappings(mappings_dir: str) -> List[Dict]:
    """Ingest MT-to-MX mapping files."""
    documents = []
    if not os.path.isdir(mappings_dir):
        return documents

    for fname in os.listdir(mappings_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(mappings_dir, fname)
        mt_type = fname.replace(".json", "")

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        content_str = json.dumps(data, indent=2)

        for ci, chunk in enumerate(_chunk_text(content_str, 1500, 200)):
            summary = (
                f"SWIFT MT-to-MX mapping definition for {mt_type}. "
                f"This mapping defines how SWIFT MT (FIN) {mt_type} message fields "
                f"are converted to ISO 20022 MX (XML) format."
            )
            documents.append(
                {
                    "id": _generate_chunk_id(f"mt_mapping:{mt_type}", ci),
                    "text": f"{summary}\n\n{chunk}",
                    "metadata": {
                        "source": fname,
                        "type": "mt_mapping",
                        "mt_type": mt_type,
                    },
                }
            )

    return documents


def ingest_validator_code(services_dir: str) -> List[Dict]:
    """Ingest Python validator code for knowledge about validation logic."""
    documents = []
    if not os.path.isdir(services_dir):
        return documents

    target_files = [
        "validator.py",
        "layer1_validator.py",
        "layer2_validator.py",
        "layer3_validator.py",
        "layer3_timing.py",
        "pacs004_validator.py",
        "mt_mx_converter.py",
    ]

    for fname in target_files:
        fpath = os.path.join(services_dir, fname)
        if not os.path.exists(fpath):
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Extract function/method definitions with their docstrings
        func_pattern = re.compile(
            r'((?:async\s+)?def\s+\w+\s*\([^)]*\)[^:]*:\s*(?:""".*?""")?)',
            re.DOTALL,
        )
        functions = func_pattern.findall(content)

        # Chunk the entire file
        for ci, chunk in enumerate(_chunk_text(content, 1500, 200)):
            summary = (
                f"Validation logic from '{fname}'. "
                f"This code implements ISO 20022 / SWIFT message validation rules including "
                f"schema checking, field validation, cross-field rules, and date/amount checks."
            )
            documents.append(
                {
                    "id": _generate_chunk_id(f"validator:{fname}", ci),
                    "text": f"{summary}\n\n{chunk}",
                    "metadata": {
                        "source": fname,
                        "type": "validator_code",
                        "file_name": fname,
                    },
                }
            )

    return documents


def ingest_uploaded_file(file_path: str, file_name: str) -> List[Dict]:
    """Ingest a user-uploaded file (txt, json, xml, csv, md)."""
    documents = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return documents

    ext = os.path.splitext(file_name)[1].lower()
    file_type = "uploaded_document"
    if ext == ".json":
        file_type = "uploaded_json"
    elif ext in (".xml", ".xsd"):
        file_type = "uploaded_schema"
    elif ext in (".md", ".txt"):
        file_type = "uploaded_text"

    for ci, chunk in enumerate(_chunk_text(content, 1500, 200)):
        summary = (
            f"User-uploaded document: '{file_name}'. "
            f"Contains additional SWIFT / ISO 20022 reference information."
        )
        documents.append(
            {
                "id": _generate_chunk_id(f"uploaded:{file_name}", ci),
                "text": f"{summary}\n\n{chunk}",
                "metadata": {
                    "source": file_name,
                    "type": file_type,
                    "uploaded": True,
                },
            }
        )
    return documents


def build_knowledge_base(base_dir: str) -> List[Dict]:
    """
    Build the complete knowledge base from all available data sources.
    base_dir should be the root of the backend project (iso20022generatorbackend).
    """
    all_docs = []

    # 1) XSD schemas (extracted folder - most valuable)
    xsd_extracted = os.path.join(base_dir, "xsds", "extracted")
    print(f"[RAG] Ingesting XSD schemas from {xsd_extracted}...")
    xsd_docs = ingest_xsd_files(xsd_extracted)
    print(f"[RAG]   -> {len(xsd_docs)} chunks from XSD schemas")
    all_docs.extend(xsd_docs)

    # 2) Temp pacs XSDs
    xsd_temp = os.path.join(base_dir, "xsds", "temp_pacs")
    if os.path.isdir(xsd_temp):
        print(f"[RAG] Ingesting temp pacs XSDs...")
        temp_docs = ingest_xsd_files(xsd_temp)
        print(f"[RAG]   -> {len(temp_docs)} chunks from temp pacs")
        all_docs.extend(temp_docs)

    # 3) Validation rules
    rules_dir = os.path.join(base_dir, "app", "resources", "rules")
    print(f"[RAG] Ingesting validation rules from {rules_dir}...")
    rule_docs = ingest_json_rules(rules_dir)
    print(f"[RAG]   -> {len(rule_docs)} chunks from rules")
    all_docs.extend(rule_docs)

    # 4) MT mapping files
    mappings_dir = os.path.join(base_dir, "app", "mappings")
    print(f"[RAG] Ingesting MT mappings from {mappings_dir}...")
    mt_docs = ingest_mt_mappings(mappings_dir)
    print(f"[RAG]   -> {len(mt_docs)} chunks from MT mappings")
    all_docs.extend(mt_docs)

    # 5) Validator code
    services_dir = os.path.join(base_dir, "app", "services")
    print(f"[RAG] Ingesting validator code from {services_dir}...")
    code_docs = ingest_validator_code(services_dir)
    print(f"[RAG]   -> {len(code_docs)} chunks from validator code")
    all_docs.extend(code_docs)

    # 6) Uploaded documents (from chatbot uploads folder)
    uploads_dir = os.path.join(base_dir, "app", "chatbot", "uploads")
    if os.path.isdir(uploads_dir):
        print(f"[RAG] Ingesting uploaded documents from {uploads_dir}...")
        for fname in os.listdir(uploads_dir):
            fpath = os.path.join(uploads_dir, fname)
            if os.path.isfile(fpath):
                upload_docs = ingest_uploaded_file(fpath, fname)
                all_docs.extend(upload_docs)
        print(f"[RAG]   -> uploaded docs processed")

    print(f"[RAG] Total knowledge base: {len(all_docs)} chunks")
    return all_docs
