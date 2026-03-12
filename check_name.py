
import ast

def check_unbound():
    content = open('app/services/layer2_validator.py').read()
    tree = ast.parse(content)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            assigned = set()
            used = []
            
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    if isinstance(child.ctx, ast.Store):
                        assigned.add(child.id)
                    elif isinstance(child.ctx, ast.Load):
                        used.append((child.lineno, child.id))
            
            for lineno, var in used:
                if var == 'name' and var not in assigned:
                    pass # may be global
                elif var == 'name':
                    print(f"Function {node.name} uses 'name' at line {lineno}")

check_unbound()
