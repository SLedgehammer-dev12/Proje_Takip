import sqlite3
import os
from database import ProjeTakipDB

db_path = 'test_old_db.sqlite'
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('CREATE TABLE projeler (id INTEGER PRIMARY KEY, proje_kodu TEXT NOT NULL UNIQUE, proje_ismi TEXT NOT NULL, proje_turu TEXT)')
c.execute('CREATE TABLE revizyonlar (id INTEGER PRIMARY KEY, proje_id INTEGER, revizyon_kodu TEXT, aciklama TEXT, durum TEXT DEFAULT ''Onaysiz'', tarih TIMESTAMP)')
c.execute('CREATE TABLE dokumanlar (id INTEGER PRIMARY KEY, revizyon_id INTEGER, dosya_adi TEXT, dosya_verisi BLOB)')
conn.commit()
conn.close()

try:
    print('Opening with ProjeTakipDB (should trigger migrations)...')
    db = ProjeTakipDB(db_path)
    print('Migration successful!')
    print('Testing write...')
    db.proje_ekle('P-100', 'Test Projesi', kategori_id=None)
    print('Write successful!')
    print('Testing read...')
    projeler = db.projeleri_listele()
    print(f'Read successful! Found {len(projeler)} project(s).')
    print('ALL COMPATIBILITY TESTS PASSED!')
finally:
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass
