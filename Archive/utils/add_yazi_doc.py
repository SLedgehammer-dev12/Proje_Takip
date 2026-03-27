import sys, os
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)
from database import ProjeTakipDB

if len(sys.argv) < 3:
    print('Usage: add_yazi_doc.py <yazi_no> <file_path> [db_path]')
    sys.exit(1)

yazi_no = sys.argv[1]
file_path = sys.argv[2]
DB_PATH = sys.argv[3] if len(sys.argv) > 3 else os.path.join(REPO_ROOT, 'projeler.db')

if not os.path.exists(file_path):
    print('File does not exist', file_path)
    sys.exit(1)

from utils import setup_logging
os.environ['PT_DEBUG'] = '1'
setup_logging()

print('Using DB:', DB_PATH)
db = ProjeTakipDB(DB_PATH)

with open(file_path, 'rb') as f:
    data = f.read()

try:
    ok = db.yazi_dokumani_kaydet(yazi_no, os.path.basename(file_path), data, 'gelen')
    print('Saved yazi doc for', yazi_no, 'result:', ok)
except Exception as e:
    print('Error while saving yazi doc:', e)
    raise
