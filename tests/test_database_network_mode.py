from database import ProjeTakipDB


def test_unc_paths_are_detected_as_network_databases(tmp_path):
    db = ProjeTakipDB(str(tmp_path / "projeler.db"))
    try:
        db.db_adi = r"\\server\share\projeler.db"
        assert db._is_network_database() is True
    finally:
        db.close()
