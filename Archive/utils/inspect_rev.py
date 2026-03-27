import sys, os
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)
from database import ProjeTakipDB
import sqlite3

db_file = os.path.join(REPO_ROOT, 'projeler.db')
db = ProjeTakipDB(db_file)
rev_id = 1038
cur = db.cursor

cur.execute('SELECT id, proje_id, proje_rev_no, revizyon_kodu, durum, tarih, aciklama, proje_rev_no, gelen_yazi_no, gelen_yazi_tarih, onay_yazi_no, onay_yazi_tarih, red_yazi_no, red_yazi_tarih, tse_gonderildi, yazi_turu FROM revizyonlar WHERE id = ?', (rev_id,))
row = cur.fetchone()
print('Row:', row)

# Also run revizyonlari_getir query fetch
rows = []
rows = db.revizyonlari_getir(row[1])
for r in rows:
    if r.id == rev_id:
        print('Rev.Model fields:')
        print('id', r.id)
        print('proje_rev_no', r.proje_rev_no)
        print('revizyon_kodu', r.revizyon_kodu)
        print('durum', r.durum)
        print('tarih', r.tarih)
        print('aciklama', r.aciklama)
        print('dokuman_durumu', r.dokuman_durumu)
        print('onay_yazi_no', r.onay_yazi_no)
        print('onay_yazi_tarih', r.onay_yazi_tarih)
        print('red_yazi_no', r.red_yazi_no)
        print('red_yazi_tarih', r.red_yazi_tarih)
        print('gelen_yazi_no', r.gelen_yazi_no)
        print('gelen_yazi_tarih', r.gelen_yazi_tarih)
        print('tse_gonderildi', r.tse_gonderildi)
        print('yazi_turu', r.yazi_turu)
        print('dosya_adi', r.dosya_adi)

