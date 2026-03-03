import os
import re
from lxml import etree
from typing import Dict, Any, List, Optional

XS = 'http://www.w3.org/2001/XMLSchema'

def _camel_to_words(name: str) -> str:
    """Convert ISO 20022 CamelCase names to readable English words."""
    if not name:
        return ""
    # Strip trailing version digits (e.g. GroupHeader131 → GroupHeader)
    name = re.sub(r'\d+$', '', name)
    # Split: uppercase letters that start a new word
    words = re.findall(r'[A-Z][a-z]+|[A-Z]+(?=[A-Z][a-z]|$)|[a-z]+|[A-Z]', name)
    return ' '.join(words) if words else name

class SchemaGenerator:
    _cache: Dict[str, Any] = {}

    @staticmethod
    def get_schema_tree(xsd_path: str) -> Optional[Dict[str, Any]]:
        if xsd_path in SchemaGenerator._cache:
            return SchemaGenerator._cache[xsd_path]
        
        if not os.path.exists(xsd_path):
            return None
            
        try:
            tree = etree.parse(xsd_path)
            root = tree.getroot()
            
            # Namespace handling
            target_ns = root.get('targetNamespace')
            
            # 1. Find the root element (Document or BusMsg)
            root_elements = root.xpath(f"//xs:element[@name='Document' or @name='BusMsg']", namespaces={'xs': XS})
            if not root_elements:
                # Fallback to the first top-level element
                root_elements = root.xpath(f"/xs:schema/xs:element", namespaces={'xs': XS})
            
            if not root_elements:
                return None
                
            # We use a state to track visited types to prevent infinite recursion in circular XSDs
            # (though ISO 20022 is usually not circular, it's good practice)
            visited_types = set()
            
            result = SchemaGenerator._parse_element(root_elements[0], root, visited_types)
            if result:
                result["namespace"] = target_ns
            SchemaGenerator._cache[xsd_path] = result
            return result
        except Exception as e:
            print(f"Error generating schema tree for {xsd_path}: {e}")
            return None

    @staticmethod
    def _parse_element(elem, xsd_root, visited_types, depth=0) -> Dict[str, Any]:
        # Increase depth limit for complex ISO messages like pacs.008
        if depth > 20: 
            return {"name": elem.get('name'), "type": "truncated"}

        name = elem.get('name')
        type_name = elem.get('type')
        min_occ = elem.get('minOccurs', '1')
        max_occ = elem.get('maxOccurs', '1')
        
        node = {
            "name": name,
            "label": _camel_to_words(name),
            "mandatory": min_occ != '0',
            "repeatable": max_occ == 'unbounded' or (max_occ.isdigit() and int(max_occ) > 1),
            "type": "simple",
            "children": []
        }
        
        # If no explicit type, check if it has a complexType child
        if not type_name:
            complex_type = elem.find(f"{{{XS}}}complexType")
            if complex_type is not None:
                node["type"] = "complex"
                node["children"] = SchemaGenerator._parse_complex_type(complex_type, xsd_root, visited_types, depth + 1)
            else:
                simple_type = elem.find(f"{{{XS}}}simpleType")
                if simple_type is not None:
                     node["type"] = "simple"
        else:
            # Check if it's a built-in type
            if ":" in type_name and any(type_name.startswith(p) for p in ["xs:", "xsd:"]):
                node["type"] = type_name.split(":")[-1]
            else:
                local_type_name = type_name.split(":")[-1] if ":" in type_name else type_name
                
                # Search for type definition
                # Try complexType first
                type_def = xsd_root.xpath(f"//xs:complexType[@name='{local_type_name}']", namespaces={'xs': XS})
                if type_def:
                    node["type"] = "complex"
                    # Avoid infinite recursion
                    if local_type_name in visited_types and depth > 10:
                         node["type"] = "referred_complex"
                         node["type_name"] = local_type_name
                    else:
                        visited_types.add(local_type_name)
                        node["children"] = SchemaGenerator._parse_complex_type(type_def[0], xsd_root, visited_types, depth + 1)
                        visited_types.remove(local_type_name)
                else:
                    # Try simpleType
                    type_def = xsd_root.xpath(f"//xs:simpleType[@name='{local_type_name}']", namespaces={'xs': XS})
                    if type_def:
                        node["type"] = "simple"
                        # Could extract restrictions (enumeration, pattern) here if needed
                        restrictions = type_def[0].xpath(".//xs:enumeration", namespaces={'xs': XS})
                        if restrictions:
                             node["options"] = [r.get('value') for r in restrictions]
                    else:
                        node["type"] = "simple"
        
        return node

    @staticmethod
    def _parse_complex_type(complex_node, xsd_root, visited_types, depth) -> List[Dict[str, Any]]:
        children = []
        
        # Parse attributes as children too, so they appear in the UI/Generator
        for attr in complex_node.xpath(".//xs:attribute", namespaces={'xs': XS}):
            attr_name = attr.get('name')
            if attr_name:
                children.append({
                    "name": attr_name,
                    "label": f"@{_camel_to_words(attr_name)}",
                    "mandatory": attr.get('use') == 'required',
                    "repeatable": False,
                    "type": attr.get('type') or "string",
                    "isAttribute": True,
                    "children": []
                })

        # 1. Check for complexContent (extension/restriction)
        complex_content = complex_node.find(f"{{{XS}}}complexContent")
        if complex_content is not None:
            extension = complex_content.find(f"{{{XS}}}extension")
            if extension is not None:
                base_type = extension.get('base')
                if base_type:
                    local_base = base_type.split(":")[-1] if ":" in base_type else base_type
                    base_def = xsd_root.xpath(f"//xs:complexType[@name='{local_base}']", namespaces={'xs': XS})
                    if base_def:
                        children.extend(SchemaGenerator._parse_complex_type(base_def[0], xsd_root, visited_types, depth))
                
                # Add elements defined in the extension
                children.extend(SchemaGenerator._find_elements_in_container(extension, xsd_root, visited_types, depth))
            return children

        # 2. Sequential/Choice/All containers
        children.extend(SchemaGenerator._find_elements_in_container(complex_node, xsd_root, visited_types, depth))
        
        return children

    @staticmethod
    def _find_elements_in_container(container, xsd_root, visited_types, depth) -> List[Dict[str, Any]]:
        results = []
        # Find all direct xs:element or nested containers
        for sub in container.xpath("./xs:element | ./xs:sequence | ./xs:choice | ./xs:all | ./xs:group", namespaces={'xs': XS}):
            tag = sub.tag.split('}')[-1]
            if tag == 'element':
                results.append(SchemaGenerator._parse_element(sub, xsd_root, visited_types, depth))
            elif tag in ['sequence', 'choice', 'all']:
                # Recursively extract elements from these containers
                child_results = SchemaGenerator._find_elements_in_container(sub, xsd_root, visited_types, depth)
                
                # CRITICAL FIX: If inside a 'choice', all resulting children must be treated as optional
                # for the purpose of auto-filling data, because picking multiple branches is illegal.
                if tag == 'choice':
                    for c in child_results:
                        c["mandatory"] = False
                
                results.extend(child_results)
            elif tag == 'group':
                ref = sub.get('ref')
                if ref:
                    local_ref = ref.split(":")[-1] if ":" in ref else ref
                    group_def = xsd_root.xpath(f"//xs:group[@name='{local_ref}']", namespaces={'xs': XS})
                    if group_def:
                        results.extend(SchemaGenerator._find_elements_in_container(group_def[0], xsd_root, visited_types, depth))
        return results
