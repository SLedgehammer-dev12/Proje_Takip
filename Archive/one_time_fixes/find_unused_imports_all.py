import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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


def analyze_file(path: Path):
    try:
        src = path.read_text(encoding='utf-8')
    except Exception:
        return None
    try:
        tokens = set([t for t in ast.walk(ast.parse(src)) if isinstance(t, ast.Name)])
        names_used = set(n.id for n in tokens)
    except Exception:
        # skip files that don't parse
        return None
    imports = _get_imports_from_ast(src)
    unused = []
    for imp in imports:
        if imp[0] == 'import':
            full_name, asname = imp[1], imp[2]
            # prefer alias for check if present, else the top-level module
            check_name = asname or full_name.split('.')[0]
            if check_name not in names_used:
                unused.append(('import', full_name, asname))
        elif imp[0] == 'from':
            module, name, asname = imp[1], imp[2], imp[3]
            alias = asname or name
            if alias not in names_used and name != '*':
                unused.append(('from', module, name, asname))
    return unused


def main():
    results = {}
    for path in ROOT.glob('**/*.py'):
        if 'venv' in path.parts or '.venv' in path.parts or 'site-packages' in path.parts:
            continue
        # skip package __init__ files (they intentionally re-export symbols)
        if path.name == "__init__.py":
            continue
        # skip tests; we want to analyze source modules only
        if "tests" in path.parts:
            continue
        unused = analyze_file(path)
        if unused:
            results[str(path.relative_to(ROOT))] = unused
    if results:
        print('Unused import report:')
        for f, imps in results.items():
            print(f) 
            for i in imps:
                print('  ', i)
    else:
        print('No unused imports detected')


if __name__ == '__main__':
    main()
