# Debug script to check revision order for project 4269
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
        print(f"\n{'='*80}")
        print(f"Project: ID={proje_id}, Code={proj[1]}, Name={proj[2]}")
        print(f"{'='*80}")

        # Get ALL revision data
        revisions = cursor.execute(
            """SELECT r.id, r.revizyon_kodu, r.yazi_turu, r.proje_rev_no,
                      r.gelen_yazi_no, r.onay_yazi_no, r.red_yazi_no
               FROM revizyonlar r
               WHERE r.proje_id = ?
               ORDER BY r.id""",
            (proje_id,),
        ).fetchall()

        print(f"\nTotal revisions: {len(revisions)}")
        print("\nAll revisions (ordered by ID):")
        print(
            f"{'ID':<5} {'RevKod':<8} {'YaziTuru':<15} {'PrjRevNo':<10} {'GelenNo':<15} {'OnayNo':<15} {'RedNo':<15}"
        )
        print("-" * 100)
        for rev in revisions:
            print(
                f"{rev[0]:<5} {rev[1]:<8} {str(rev[2]):<15} {rev[3]:<10} {str(rev[4]):<15} {str(rev[5]):<15} {str(rev[6]):<15}"
            )

        # Check yazi_turu values
        print("\n\nYazi Turu Analysis:")
        yazi_turu_counts = {}
        for rev in revisions:
            yt = rev[2] if rev[2] else "NULL"
            yazi_turu_counts[yt] = yazi_turu_counts.get(yt, 0) + 1

        for yt, count in sorted(yazi_turu_counts.items()):
            print(f"  {yt}: {count} revisions")

else:
    print("No projects containing 4269 found")

conn.close()
