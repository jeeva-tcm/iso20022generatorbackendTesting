import time
import re
from typing import Optional
from lxml import etree
from .models import ValidationIssue, ValidationReport

class Layer1Mixin:
    async def _run_layer_1(self, xml_content: str, report: ValidationReport, filename: Optional[str] = None) -> bool:
        """
        LAYER 1 — Technical / Payload Validation
        Comprehensive check for well-formedness, illegal characters, and standard ISO envelopes.
        """
        start = time.time()
        
        # 1. Payload Presence (FATAL)
        if not xml_content or not xml_content.strip():
            report.add_issue(ValidationIssue(
                "ERROR", 1, "Empty File", "Line 1",
                "The uploaded file is empty or no content was provided.",
                "Please upload a valid XML message file or paste XML content."
            ))
            report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
            return False

        # 2. File Type & Preliminary XML Structure (NON-FATAL for L1 checks)
        allowed_exts = ('.xml', '.xsd', '.txt')
        if filename and not filename.lower().endswith(allowed_exts):
             report.add_issue(ValidationIssue(
                "ERROR", 1, "Wrong File Type", "File Extension",
                f"The file '{filename}' is not a standard XML extension.",
                "Please use .xml, .xsd, or .txt extension."
            ))

        # Check content structure (must look like XML)
        has_xml_structure = xml_content.lstrip().startswith(('<', '<?xml'))
        if not has_xml_structure:
             report.add_issue(ValidationIssue(
                "ERROR", 1, "Invalid Content", "Line 1",
                "The file content does not appear to be valid XML.",
                "Ensure the file contains XML tags starting with '<'."
            ))

        # 3. Payload Size (FATAL)
        size_kb = len(xml_content.encode('utf-8')) / 1024
        max_size = self.config.get("app_settings", {}).get("max_file_size_kb", 2048)
        if size_kb > max_size:
             report.add_issue(ValidationIssue(
                 "ERROR", 1, "File Too Large", "Size Limit", 
                 f"Your message is {size_kb:.1f} KB, exceeding the {max_size} KB limit.",
                 f"Please reduce the message size below {max_size} KB."
             ))
             report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
             return False

        # 4. UTF-8 Encoding & Header (NON-FATAL for L1 checks)
        header_match = re.search(r'<\?xml[^>]+encoding=["\']([^"\']+)["\']', xml_content, re.IGNORECASE)
        if not header_match:
             report.add_issue(ValidationIssue(
                "ERROR", 1, "Missing Header", "Line 1",
                "Your XML file is missing the required declaration header.",
                "Add this line at the very top: <?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            ))
        else:
            encoding = header_match.group(1).upper()
            if encoding != "UTF-8":
                report.add_issue(ValidationIssue(
                    "ERROR", 1, "Wrong Encoding", "Line 1",
                    f"Your file uses {encoding} encoding, but ISO 20022 messages must use UTF-8.",
                    "Change the encoding in your XML header to UTF-8."
                ))

        # 5. Illegal Characters (NON-FATAL for L1 checks)
        illegal_chars = re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', xml_content)
        if illegal_chars:
            report.add_issue(ValidationIssue(
                "ERROR", 1, "Invalid Characters", "Line 1",
                "Your message contains invisible control characters that are not allowed.",
                "Remove hidden characters (ASCII 0-31) from your XML."
            ))

        # 6. XML Well-Formedness & Identity (FATAL if parse fails)
        try:
            xml_bytes = xml_content.encode('utf-8')
            parser = etree.XMLParser(recover=False, no_network=True, remove_blank_text=True)
            root = etree.fromstring(xml_bytes, parser)
            
            # 7. Envelope Detection (Document / BusMsg / AppHdr)
            iso_nodes = root.xpath("//*[local-name()='Document' or local-name()='BusMsg' or local-name()='AppHdr' or local-name()='BusMsgEnvlp']")
            if not iso_nodes and any(x in root.tag for x in ['Document', 'BusMsg', 'AppHdr', 'BusMsgEnvlp']):
                iso_nodes = [root]
            
            if not iso_nodes:
                report.add_issue(ValidationIssue(
                    "ERROR", 1, "Missing Structure", "Root",
                    "The XML is missing the required ISO 20022 <Document> or <BusMsg> wrapper.",
                    "Ensure your message is wrapped in a standard ISO 20022 container."
                ))
            else:
                # 8. Namespace Validation
                payload_node = root.xpath("//*[local-name()='Document' or local-name()='BusMsg']")
                doc_node = payload_node[0] if payload_node else iso_nodes[0]
                ns = doc_node.nsmap.get(None) or ""
                
                if not re.match(r'^urn:iso:std:iso:20022:tech:xsd:[a-z]{4}\.\d{3}\.\d{3}\.\d{2}$', ns) and "head.001" not in ns:
                    report.add_issue(ValidationIssue(
                        "ERROR", 1, "Wrong Namespace", str(doc_node.sourceline or 1),
                        f"The namespace '{ns}' does not match the ISO 20022 standard format.",
                        "Use the correct URN format (e.g. urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08)."
                    ))
                report.metadata = {"Namespace": ns}

        except etree.XMLSyntaxError as e:
            report.add_issue(ValidationIssue(
                "ERROR", 1, "XML Syntax Error", f"Line {e.lineno}",
                "Your XML has a syntax error that prevents it from being read.",
                f"Technical details: {str(e)}. Check for unclosed tags or invalid characters."
            ))
            report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
            return False

        # Finish Layer 1
        success = report.status != "FAIL"
        report.layer_status["1"] = {"status": "✅" if success else "❌", "time": round((time.time() - start) * 1000, 2)}
        return success
