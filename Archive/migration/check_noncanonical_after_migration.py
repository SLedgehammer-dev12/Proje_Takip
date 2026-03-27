import os, sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)
from database import ProjeTakipDB

DB_PATH = os.path.join(REPO_ROOT, 'projeler.db')
if not os.path.exists(DB_PATH):
    print('Database not found at:', DB_PATH)
    sys.exit(1)

# Open DB; this runs migrations
os.environ['PT_DEBUG'] = '1'
from utils import setup_logging
setup_logging()

print('Opening DB (this will run migrations)...')
db = ProjeTakipDB(DB_PATH)
print('DB opened; checking non-canonical yazi_turu entries...')
rows = db.cursor.execute("SELECT id, revizyon_kodu, gelen_yazi_no, onay_yazi_no, red_yazi_no, yazi_turu FROM revizyonlar WHERE yazi_turu NOT IN ('gelen', 'giden', 'yok') OR yazi_turu IS NULL").fetchall()
if not rows:
    print('No non-canonical yazi_turu rows found: migrations cleaned them up')
else:
    print('Found non-canonical yazi_turu rows:')
    for r in rows:
        print(r)

print('Done')
