import sqlite3

from database import ProjeTakipDB
from models import Durum


def _make_db(tmp_path):
    db_path = tmp_path / "projeler.db"
    return ProjeTakipDB(str(db_path))


def test_add_outgoing_revision_copy_sets_onay_fields_atomically(tmp_path):
    db = _make_db(tmp_path)
    try:
        proje_id = db.proje_ekle("P-001", "Test Proje")
        assert proje_id is not None

        ilk_rev_id = db.mevcut_projeye_revizyon_ekle(
            proje_id=proje_id,
            revizyon_kodu="A",
            dosya_yolu=None,
            aciklama="Ilk revizyon",
            yazi_turu="yok",
            durum=Durum.ONAYSIZ.value,
            dosya_verisi=b"%PDF-1.7\nilk\n",
        )
        assert ilk_rev_id is not None

        yeni_rev_id, yeni_durum = db.mevcut_projeye_giden_yazi_revizyonu_ekle(
            proje_id=proje_id,
            revizyon_kodu="A",
            dosya_adi="ilk.pdf",
            dosya_verisi=b"%PDF-1.7\ngiden\n",
            islem_turu="Onay",
            yazi_no="42044",
            yazi_tarih="31.03.2026",
        )

        row = db.cursor.execute(
            """
            SELECT proje_rev_no, revizyon_kodu, durum, yazi_turu,
                   onay_yazi_no, onay_yazi_tarih, red_yazi_no
            FROM revizyonlar
            WHERE id = ?
            """,
            (yeni_rev_id,),
        ).fetchone()
        dokuman = db.cursor.execute(
            "SELECT dosya_adi, dosya_verisi FROM dokumanlar WHERE revizyon_id = ?",
            (yeni_rev_id,),
        ).fetchone()

        assert yeni_durum == Durum.ONAYLI.value
        assert row == (1, "A", Durum.ONAYLI.value, "giden", "42044", "31.03.2026", None)
        assert dokuman[0] == "ilk.pdf"
        assert dokuman[1] == b"%PDF-1.7\ngiden\n"
    finally:
        db.close()


def test_add_outgoing_revision_copy_rejects_unknown_operation_without_partial_write(tmp_path):
    db = _make_db(tmp_path)
    try:
        proje_id = db.proje_ekle("P-002", "Test Proje 2")
        assert proje_id is not None

        rev_id = db.mevcut_projeye_revizyon_ekle(
            proje_id=proje_id,
            revizyon_kodu="A",
            dosya_yolu=None,
            aciklama="Ilk revizyon",
            yazi_turu="yok",
            durum=Durum.ONAYSIZ.value,
            dosya_verisi=b"%PDF-1.7\nilk\n",
        )
        assert rev_id is not None

        before_count = db.cursor.execute(
            "SELECT COUNT(*) FROM revizyonlar WHERE proje_id = ?",
            (proje_id,),
        ).fetchone()[0]

        try:
            db.mevcut_projeye_giden_yazi_revizyonu_ekle(
                proje_id=proje_id,
                revizyon_kodu="A",
                dosya_adi="ilk.pdf",
                dosya_verisi=b"%PDF-1.7\ngiden\n",
                islem_turu="Bilinmeyen",
                yazi_no="99999",
                yazi_tarih="31.03.2026",
            )
            assert False, "ValueError bekleniyordu"
        except ValueError:
            pass

        after_count = db.cursor.execute(
            "SELECT COUNT(*) FROM revizyonlar WHERE proje_id = ?",
            (proje_id,),
        ).fetchone()[0]

        assert after_count == before_count
    finally:
        db.close()


def test_bulk_project_insert_normalizes_invalid_category_ids(tmp_path):
    db = _make_db(tmp_path)
    pdf_path = tmp_path / "ilk.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\nbulk\n")

    try:
        result = db.dosyadan_proje_ve_revizyon_ekle(
            kod="P-003",
            isim="Bulk Proje",
            dosya_yolu=str(pdf_path),
            kategori_id=0,
        )

        assert result is not None
        row = db.cursor.execute(
            "SELECT kategori_id, hiyerarsi FROM projeler WHERE proje_kodu = ?",
            ("P-003",),
        ).fetchone()
        assert row == (None, None)

        assert db.projeyi_guncelle(
            proje_id=db.proje_var_mi("P-003"),
            yeni_kod="P-003",
            yeni_isim="Bulk Proje",
            yeni_tur=None,
            yeni_kategori_id=999,
        )
        updated = db.cursor.execute(
            "SELECT kategori_id FROM projeler WHERE proje_kodu = ?",
            ("P-003",),
        ).fetchone()
        assert updated == (None,)
    finally:
        db.close()


def test_revision_metadata_fields_roundtrip(tmp_path):
    db = _make_db(tmp_path)
    try:
        proje_id = db.proje_ekle("P-004", "OCR Proje")
        assert proje_id is not None

        rev_id = db.mevcut_projeye_revizyon_ekle(
            proje_id=proje_id,
            revizyon_kodu="A",
            dosya_yolu=None,
            aciklama="OCR aciklama",
            yazi_turu="gelen",
            durum=Durum.ONAYSIZ.value,
            dosya_verisi=b"%PDF-1.7\nocr\n",
            gelen_yazi_no="123",
            gelen_yazi_tarih="01.04.2026",
            yazi_konu="Pompa istasyonu revizyon talebi",
            yazi_kurum="BOTAS Genel Mudurlugu",
        )
        assert rev_id is not None

        row = db.cursor.execute(
            "SELECT yazi_konu, yazi_kurum FROM revizyonlar WHERE id = ?",
            (rev_id,),
        ).fetchone()
        latest = db.en_son_revizyon_bilgisi_getir(proje_id)

        assert row == ("Pompa istasyonu revizyon talebi", "BOTAS Genel Mudurlugu")
        assert latest is not None
        assert latest.yazi_konu == "Pompa istasyonu revizyon talebi"
        assert latest.yazi_kurum == "BOTAS Genel Mudurlugu"
    finally:
        db.close()


def test_legacy_database_gains_revision_metadata_columns_on_open(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE kategoriler (
                id INTEGER PRIMARY KEY,
                isim TEXT NOT NULL,
                parent_id INTEGER
            );
            CREATE TABLE projeler (
                id INTEGER PRIMARY KEY,
                proje_kodu TEXT NOT NULL UNIQUE,
                proje_ismi TEXT NOT NULL,
                proje_turu TEXT,
                olusturma_tarihi TIMESTAMP,
                hiyerarsi TEXT,
                kategori_id INTEGER
            );
            CREATE TABLE revizyonlar (
                id INTEGER PRIMARY KEY,
                proje_id INTEGER NOT NULL,
                revizyon_kodu TEXT NOT NULL,
                aciklama TEXT,
                durum TEXT,
                tarih TIMESTAMP,
                gelen_yazi_no TEXT,
                gelen_yazi_tarih TEXT,
                onay_yazi_no TEXT,
                onay_yazi_tarih TEXT,
                red_yazi_no TEXT,
                red_yazi_tarih TEXT,
                proje_rev_no INTEGER,
                tse_gonderildi INTEGER DEFAULT 0,
                tse_yazi_no TEXT,
                tse_yazi_tarih TEXT,
                yazi_turu TEXT DEFAULT 'gelen'
            );
            CREATE TABLE dokumanlar (
                id INTEGER PRIMARY KEY,
                revizyon_id INTEGER NOT NULL UNIQUE,
                dosya_adi TEXT NOT NULL,
                dosya_verisi BLOB NOT NULL
            );
            CREATE TABLE yazi_dokumanlari (
                id INTEGER PRIMARY KEY,
                yazi_no TEXT NOT NULL,
                yazi_tarih TEXT NOT NULL DEFAULT '',
                dosya_adi TEXT NOT NULL,
                dosya_verisi BLOB NOT NULL,
                yazi_turu TEXT NOT NULL,
                UNIQUE(yazi_no, yazi_tarih, yazi_turu)
            );
            CREATE TABLE revizyon_takipleri (
                id INTEGER PRIMARY KEY,
                revizyon_id INTEGER NOT NULL UNIQUE,
                takip_notu TEXT,
                aktif INTEGER DEFAULT 1,
                olusturma_tarihi TIMESTAMP,
                guncelleme_tarihi TIMESTAMP,
                kapatma_tarihi TIMESTAMP
            );
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password_hash TEXT,
                full_name TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_login TIMESTAMP
            );
            INSERT INTO projeler (id, proje_kodu, proje_ismi) VALUES (1, 'P-LEGACY', 'Legacy Proje');
            INSERT INTO revizyonlar (
                id, proje_id, revizyon_kodu, aciklama, durum, tarih, gelen_yazi_no, gelen_yazi_tarih
            ) VALUES (
                1, 1, 'A', 'Eski kayit', 'ONAYSIZ', '2026-03-01', '123', '01.03.2026'
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = ProjeTakipDB(str(db_path), allow_create=False)
    try:
        columns = {
            row[1]
            for row in db.cursor.execute("PRAGMA table_info(revizyonlar)").fetchall()
        }
        latest = db.en_son_revizyon_bilgisi_getir(1)

        assert "yazi_konu" in columns
        assert "yazi_kurum" in columns
        assert latest is not None
        assert latest.yazi_konu is None
        assert latest.yazi_kurum is None
    finally:
        db.close()


def test_restore_backup_reapplies_revision_metadata_migration(tmp_path):
    legacy_backup = tmp_path / "legacy_backup.db"
    conn = sqlite3.connect(legacy_backup)
    try:
        conn.executescript(
            """
            CREATE TABLE kategoriler (
                id INTEGER PRIMARY KEY,
                isim TEXT NOT NULL,
                parent_id INTEGER
            );
            CREATE TABLE projeler (
                id INTEGER PRIMARY KEY,
                proje_kodu TEXT NOT NULL UNIQUE,
                proje_ismi TEXT NOT NULL,
                proje_turu TEXT,
                olusturma_tarihi TIMESTAMP,
                hiyerarsi TEXT,
                kategori_id INTEGER
            );
            CREATE TABLE revizyonlar (
                id INTEGER PRIMARY KEY,
                proje_id INTEGER NOT NULL,
                revizyon_kodu TEXT NOT NULL,
                aciklama TEXT,
                durum TEXT,
                tarih TIMESTAMP,
                gelen_yazi_no TEXT,
                gelen_yazi_tarih TEXT,
                onay_yazi_no TEXT,
                onay_yazi_tarih TEXT,
                red_yazi_no TEXT,
                red_yazi_tarih TEXT,
                proje_rev_no INTEGER,
                tse_gonderildi INTEGER DEFAULT 0,
                tse_yazi_no TEXT,
                tse_yazi_tarih TEXT,
                yazi_turu TEXT DEFAULT 'gelen'
            );
            CREATE TABLE dokumanlar (
                id INTEGER PRIMARY KEY,
                revizyon_id INTEGER NOT NULL UNIQUE,
                dosya_adi TEXT NOT NULL,
                dosya_verisi BLOB NOT NULL
            );
            CREATE TABLE yazi_dokumanlari (
                id INTEGER PRIMARY KEY,
                yazi_no TEXT NOT NULL,
                dosya_adi TEXT NOT NULL,
                dosya_verisi BLOB NOT NULL,
                yazi_turu TEXT NOT NULL
            );
            CREATE TABLE revizyon_takipleri (
                id INTEGER PRIMARY KEY,
                revizyon_id INTEGER NOT NULL UNIQUE,
                takip_notu TEXT,
                aktif INTEGER DEFAULT 1,
                olusturma_tarihi TIMESTAMP,
                guncelleme_tarihi TIMESTAMP,
                kapatma_tarihi TIMESTAMP
            );
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password_hash TEXT,
                full_name TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_login TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    live_db_path = tmp_path / "projeler.db"
    db = ProjeTakipDB(str(live_db_path))
    try:
        assert db.yedekten_geri_yukle(str(legacy_backup)) is True
        columns = {
            row[1]
            for row in db.cursor.execute("PRAGMA table_info(revizyonlar)").fetchall()
        }

        assert "yazi_konu" in columns
        assert "yazi_kurum" in columns
        assert "yazi_tarih" in {
            row[1]
            for row in db.cursor.execute("PRAGMA table_info(yazi_dokumanlari)").fetchall()
        }
    finally:
        db.close()
