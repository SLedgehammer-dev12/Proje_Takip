import os, sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)
from database import ProjeTakipDB

DB_PATH = os.path.join(REPO_ROOT, 'projeler.db')
if len(sys.argv) > 1:
    DB_PATH = sys.argv[1]

if not os.path.exists(DB_PATH):
    print('Database not found at', DB_PATH)
    sys.exit(1)

from utils import setup_logging
import os
os.environ['PT_DEBUG'] = '1'
setup_logging()

print('Using DB:', DB_PATH)
db = ProjeTakipDB(DB_PATH)

# Gather distinct yazi numbers used in revizyonlar
cursor = db.cursor
cursor.execute('SELECT DISTINCT gelen_yazi_no FROM revizyonlar WHERE gelen_yazi_no IS NOT NULL')
revs = [r[0] for r in cursor.fetchall() if r[0]]

# Also onay and red
cursor.execute('SELECT DISTINCT onay_yazi_no FROM revizyonlar WHERE onay_yazi_no IS NOT NULL')
revs += [r[0] for r in cursor.fetchall() if r[0]]
cursor.execute('SELECT DISTINCT red_yazi_no FROM revizyonlar WHERE red_yazi_no IS NOT NULL')
revs += [r[0] for r in cursor.fetchall() if r[0]]

revs = sorted(set(revs))

missing = []
for y in revs:
    doc = db.yazi_dokumani_getir(y)
    if not doc:
        missing.append(y)

if not missing:
    print('No missing yazi documents found')
else:
    print('Missing yazi documents:', missing)
    print('\nYou can add them using tools/add_yazi_doc.py:')
    for y in missing:
        print(f"python tools\\add_yazi_doc.py {y} path\\to\\{y}.pdf {DB_PATH}")

print('Done')
