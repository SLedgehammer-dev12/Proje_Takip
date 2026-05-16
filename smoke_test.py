
import os
import sqlite3
from database import ProjeTakipDB
from models import ProjeModel

def smoke_test():
    db_name = "smoke_test.db"
    if os.path.exists(db_name):
        os.remove(db_name)
    
    print("1. Creating DB and checking initialization...")
    db = ProjeTakipDB(db_name)
    
    print("2. Adding a dummy project...")
    with db.transaction():
        db.cursor.execute("INSERT INTO projeler (proje_kodu, proje_ismi) VALUES ('P1', 'Test Proje')")
        p_id = db.cursor.lastrowid
        db.cursor.execute("INSERT INTO revizyonlar (proje_id, proje_rev_no, revizyon_kodu, is_flagged) VALUES (?, 1, 'A', 1)", (p_id,))
    
    print("3. Verifying flag status in listing...")
    projects = db.projeleri_listele()
    p = next(x for x in projects if x.id == p_id)
    assert p.is_flagged == 1, f"Expected flagged project, got {p.is_flagged}"
    
    print("4. Removing flag...")
    success = db.proje_flag_durumu_guncelle(p_id, False)
    assert success is True
    
    print("5. Verifying flag is gone in listing (Cache check)...")
    projects = db.projeleri_listele()
    p = next(x for x in projects if x.id == p_id)
    assert p.is_flagged == 0, f"Expected unflagged project, got {p.is_flagged}"
    
    print("6. Checking Sorting options...")
    db.projeleri_listele(sort_by="tarih_desc")
    db.projeleri_listele(sort_by="tur_asc")
    
    print("7. Compatibility Check: Simulate an old DB without is_flagged column...")
    db.close()
    os.remove(db_name)
    
    conn = sqlite3.connect(db_name)
    conn.execute("CREATE TABLE projeler (id INTEGER PRIMARY KEY, proje_kodu TEXT, proje_ismi TEXT)")
    conn.execute("CREATE TABLE revizyonlar (id INTEGER PRIMARY KEY, proje_id INTEGER, durum TEXT)")
    conn.close()
    
    print("   Initializing DB on old schema...")
    db_old = ProjeTakipDB(db_name)
    
    conn = db_old._get_connection()
    cursor = conn.execute("PRAGMA table_info(revizyonlar)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "is_flagged" in columns, "Migration failed to add is_flagged column"
    
    print("Smoke test passed successfully!")
    db_old.close()
    if os.path.exists(db_name):
        os.remove(db_name)

if __name__ == "__main__":
    smoke_test()
