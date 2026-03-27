import sqlite3

conn = sqlite3.connect("projeler.db")
cursor = conn.cursor()

# Find projects containing 4269 in code
result = cursor.execute(
    "SELECT id, proje_kodu, proje_ismi FROM projeler WHERE proje_kodu LIKE ?",
    ("%4269%",),
).fetchall()

if result:
    for proj in result:
        proje_id = proj[0]
        print(f"\n{'='*60}")
        print(f"Project: ID={proje_id}, Code={proj[1]}, Name={proj[2]}")
        print(f"{'='*60}")

        # Get revisions ordered by revision code, then by proje_rev_no DESC
        revisions = cursor.execute(
            """SELECT r.id, r.revizyon_kodu, r.yazi_turu, r.proje_rev_no
               FROM revizyonlar r
               WHERE r.proje_id = ?
               ORDER BY r.revizyon_kodu, r.proje_rev_no DESC""",
            (proje_id,),
        ).fetchall()

        print("\nCurrent DB ordering (by revizyon_kodu, proje_rev_no DESC):")
        for rev in revisions:
            print(
                f"  RevKod={rev[1]:3s}, YaziTuru={rev[2]:10s}, ProjeRevNo={rev[3]:2d}, ID={rev[0]}"
            )

        # Now show what the display order SHOULD be (gelen before giden)
        print(
            "\nExpected ordering (by revizyon_kodu, gelen first, then proje_rev_no DESC):"
        )

        def yazi_turu_key(yt):
            if not yt:
                return 2
            y = yt.strip().lower()
            if "gelen" in y:
                return 0
            if "giden" in y or "onay" in y or "red" in y:
                return 1
            return 2

        sorted_revs = sorted(
            revisions, key=lambda r: (r[1], yazi_turu_key(r[2]), -r[3])
        )
        for rev in sorted_revs:
            print(
                f"  RevKod={rev[1]:3s}, YaziTuru={rev[2]:10s}, ProjeRevNo={rev[3]:2d}, ID={rev[0]}"
            )
else:
    print("No projects containing 4269 found")

conn.close()
