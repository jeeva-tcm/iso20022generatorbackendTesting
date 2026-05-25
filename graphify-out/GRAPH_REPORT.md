# Graph Report - iso20022generatorbackend  (2026-05-25)

## Corpus Check
- 52 files · ~64,776 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 637 nodes · 1022 edges · 65 communities (37 shown, 28 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 36 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e3617f65`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]

## God Nodes (most connected - your core abstractions)
1. `ISOValidator` - 58 edges
2. `MT2MXConverter` - 36 edges
3. `generate_single_xml()` - 34 edges
4. `xe()` - 25 edges
5. `FirebaseHistoryService` - 19 edges
6. `rng_datetime()` - 17 edges
7. `rng_id()` - 17 edges
8. `apphdr_fi()` - 17 edges
9. `BicRefreshService` - 16 edges
10. `agent_xml()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `ISOValidator`  [INFERRED]
  scratch/test_full_pipeline.py → app/services/validator.py
- `test_pacs009()` --calls--> `generate_single_xml()`  [INFERRED]
  scratch/debug_pacs009.py → app/services/bulk_generator.py
- `test_messages()` --calls--> `generate_single_xml()`  [INFERRED]
  scratch/debug_pain008.py → app/services/bulk_generator.py
- `main()` --calls--> `generate_single_xml()`  [INFERRED]
  scratch/test_bulk_fail.py → app/services/bulk_generator.py
- `test_msg()` --calls--> `generate_single_xml()`  [INFERRED]
  scratch/test_issues.py → app/services/bulk_generator.py

## Communities (65 total, 28 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (91): main(), main(), account_othr_xml(), account_xml(), agent_xml(), apphdr_fi(), el(), _fi_party() (+83 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (35): Exception, MT2MXConverter, MTMXConversionError, Attempts to detect the MT type from Block 2 and subtypes from Block 3 (Tag 119)., BUG 1 + BUG 4 FIX:         MT202COV carries two sequences:           Sequence, Map MT 71F (sender's charges) and 71G (receiver's charges) into pacs.008 / pacs., Locate a node by slash-delimited local-name path (namespace-aware)., BUG 1 + BUG 4 FIX:         MT202COV carries two sequences:           Sequence (+27 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (23): _cbpr_check_value(), CBPRJsonSchemaMixin, _extract_catalog(), _local_name(), CBPR+ JSON Schema Validator (Layer 4) ===================================== Runs, Strip namespace from an lxml tag like '{urn:...}MsgId' → 'MsgId'., Mixin added to ISOValidator. Provides one entry point: _run_cbpr_json_schema_che, Locate a JSON schema file matching the message type.          Examples of expect (+15 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (22): ChatService, ISO 20022 RAG Chatbot - Chat Service Combines retrieval with an LLM to generate, Force rebuild the knowledge base., Retrieve relevant context chunks for a question., Format retrieved results into a context string for the LLM., Generate answer using OpenAI ChatGPT., Generate a structured answer without an LLM, using the retrieved chunks directly, Main chat endpoint. Retrieves context and generates an answer. (+14 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (30): bulk_generate(), bulk_generate_stream(), export_history(), firebase_write_test(), generate_id(), get_bic_refresh_status(), get_bulk_blocks(), get_codelist() (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (14): BicRefreshService, BIC Dataset Refresh Service ============================ Maintains an up-to-da, Retrieve recent logs and include version history., Roll back to a specific previous version hash (BR-ROLLBACK)., Core refresh logic with Intelligent Change Detection and Volumetric Guardrails., Stream download with incremental SHA-256 calculation., Parse the JSONL file and verify it meets quality thresholds.          Args:, Atomic replacement logic with Windows file-lock handling. (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (23): Agent, anchor(), _bban_for(), _iban_check_digits(), make_address_country(), make_bic(), make_company_name(), make_iban() (+15 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (22): BaseModel, ask_question(), ChatRequest, ChatResponse, get_chatbot_stats(), get_suggestions(), ISO 20022 RAG Chatbot - FastAPI Routes Provides /chatbot/* endpoints for the cha, Ask a question about ISO 20022 / SWIFT messaging. (+14 more)

### Community 8 - "Community 8"
Cohesion: 0.15
Nodes (6): _build_credentials(), FirebaseHistoryService, Update the circuit-breaker state after a Firestore call., Recursively converts Firestore-specific types to JSON-serializable Python types., Issue a single tiny Firestore read to verify the credentials actually         w, _sanitize_firestore_doc()

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (15): CBPRJsonSchemaMixin, Layer1Mixin, Layer2Mixin, Layer3Mixin, Pacs004Mixin, test_pacs009(), test_messages(), main() (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.14
Nodes (10): Layer3Mixin, Executes validation based on the Generic Field Library and Global Algorithms., Loads the new global algorithms and field library., Advanced Dynamic Rule Dispatcher., Loads global rules + family rules + message-specific rules., Evaluates dynamic expressions against the canonical data map.         Supports, Business Rule: Validate if the transaction currency matches the local currency, Business Rule: Verify if the MsgId + UETR combination has been seen before. (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.19
Nodes (17): Add an uploaded document to the knowledge base., build_knowledge_base(), _chunk_text(), _generate_chunk_id(), ingest_json_rules(), ingest_mt_mappings(), ingest_uploaded_file(), ingest_validator_code() (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.19
Nodes (10): get_system_config(), is_business_day(), is_holiday(), next_business_day(), parse_time(), Dynamic lookup for holidays from configuration., to_zoned_datetime(), validateLayer3Timing() (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (12): SWIFT CBPR+ Rule — pain.008 GrpHdr must contain FwdgAgt.          The base ISO, SWIFT CBPR+ Rule — pain.008 GrpHdr must contain FwdgAgt.          The base ISO, Step 4.17 — Duplicate Identification Validation         Scans for unique identi, Step 4.17 — Duplicate Identification Validation         Scans for unique identi, Robust Message Type Detection - Prioritizes Payload over Header, Robust Message Type Detection - Prioritizes Payload over Header, Main 10-Step Validation Flow, Main 10-Step Validation Flow (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (10): Locates the XSD file for the given message type.         1. Exact Match (e.g. p, Locates the XSD file for the given message type.         1. Exact Match (e.g. p, Helper to build a simple non-indexed XPath for an lxml element, Step 4.18 — Duplicate Tag Validation         Checks for tags that appear more t, Helper to build a simple non-indexed XPath for an lxml element, Step 4.18 — Duplicate Tag Validation         Checks for tags that appear more t, Validates Legal Entity Identifier (LEI) using ISO 7064 MOD 97-10.         Retur, Validates Legal Entity Identifier (LEI) using ISO 7064 MOD 97-10.         Retur (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (8): Loads the dynamic configuration file, Loads BIC codes from the entities.ftm.json file (JSONL format), Loads BIC codes from the entities.ftm.json file (JSONL format), High-Performance Extraction Engine:         Automatically unzips all XSD bluepr, High-Performance Extraction Engine:         Automatically unzips all XSD bluepr, Loads all JSON codelists from the resource directory (Lowercased keys), Loads all JSON codelists from the resource directory (Lowercased keys), Loads the dynamic configuration file

### Community 16 - "Community 16"
Cohesion: 0.46
Nodes (7): _camel_to_words(), _find_elements_in_container(), get_schema_tree(), _parse_complex_type(), _parse_element(), Convert ISO 20022 CamelCase names to readable English words., SchemaGenerator

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (4): _iban_check_digits(), Compute valid IBAN check digits using ISO 13616 MOD-97-10 algorithm., Generate a random IBAN with valid MOD-97 check digits., rng_iban()

## Knowledge Gaps
- **263 isolated node(s):** `Gracefully stop the APScheduler background scheduler on server shutdown.`, `Get aggregated dashboard statistics from Firestore`, `Generate the next sequential validation ID for batch use`, `Initialize a validation batch:     - Generates a single VAL{DDMMYY}{NNNNN} batc`, `Dynamically extract the schema tree for a specific MX message type` (+258 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ISOValidator` connect `Community 9` to `Community 2`, `Community 10`, `Community 13`, `Community 14`, `Community 15`, `Community 18`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 36`, `Community 37`, `Community 38`?**
  _High betweenness centrality (0.227) - this node is a cross-community bridge._
- **Why does `generate_single_xml()` connect `Community 0` to `Community 9`, `Community 26`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `get_blocks_for_message()` connect `Community 0` to `Community 4`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `ISOValidator` (e.g. with `ValidationIssue` and `ValidationReport`) actually correct?**
  _`ISOValidator` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `generate_single_xml()` (e.g. with `main()` and `test_pacs009()`) actually correct?**
  _`generate_single_xml()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Gracefully stop the APScheduler background scheduler on server shutdown.`, `Get aggregated dashboard statistics from Firestore`, `Generate the next sequential validation ID for batch use` to the rest of the system?**
  _263 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._