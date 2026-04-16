import ast
from pathlib import Path

def _get_imports_from_ast(lines):
    tree = ast.parse(lines)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append(('import', alias.name, alias.asname))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                results.append(('from', node.module, alias.name, alias.asname))
    return results

def main():
    p = Path(__file__).resolve().parent.parent / 'main_window.py'
    src = p.read_text(encoding='utf-8')
    tokens = set([t for t in ast.walk(ast.parse(src)) if isinstance(t, ast.Name)])
    names_used = set()
    for n in tokens:
        names_used.add(n.id)
    imports = _get_imports_from_ast(src)
    print('Detected imports:')
    for imp in imports:
        if imp[0] == 'import':
            name = imp[1].split('.')[0]
            if name not in names_used:
                print(f"Unused import: {name}")
        elif imp[0] == 'from':
            module, name, asname = imp[1], imp[2], imp[3]
            alias = asname or name
            if alias not in names_used and name != '*':
                print(f"Potential unused import from {module}: {name}")
    print('Done')

if __name__ == '__main__':
    main()
