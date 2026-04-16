import sqlite3

conn = sqlite3.connect("projeler.db")
cursor = conn.cursor()

# Find projects with multiple yazi_turu (which have both gelen and giden)
projects = cursor.execute(
    """SELECT DISTINCT p.id, p.proje_kodu 
       FROM projeler p
       JOIN revizyonlar r ON p.id = r.proje_id
       WHERE p.id IN (
           SELECT proje_id 
           FROM revizyonlar 
           GROUP BY proje_id 
           HAVING COUNT(DISTINCT yazi_turu) > 1
       )
       LIMIT 3"""
).fetchall()

print(f"Analyzing {len(projects)} projects with multiple yazi_turu types:\n")

for proj in projects:
    proje_id, proje_kodu = proj
    print(f"\n{'='*70}")
    print(f"Project: ID={proje_id}, Code={proje_kodu}")
    print(f"{'='*70}")

    # Get revisions with current ordering
    revisions = cursor.execute(
        """SELECT r.id, r.revizyon_kodu, r.yazi_turu, r.proje_rev_no
           FROM revizyonlar r
           WHERE r.proje_id = ?
           ORDER BY r.revizyon_kodu, r.proje_rev_no DESC""",
        (proje_id,),
    ).fetchall()

    print("\nCurrent DB ordering (revizyon_kodu, proje_rev_no DESC):")
    for i, rev in enumerate(revisions, 1):
        print(
            f"  {i}. RevKod={rev[1]:3s}, YaziTuru={rev[2]:10s}, ProjeRevNo={rev[3]:2d}"
        )

    # Show what order SHOULD be (gelen before giden)
    def yazi_turu_key(yt):
        if not yt:
            return 2
        y = yt.strip().lower()
        if "gelen" in y:
            return 0
        if "giden" in y or "onay" in y or "red" in y:
            return 1
        return 2

    # Sort with yazi_turu_key BEFORE proje_rev_no
    sorted_revs = sorted(revisions, key=lambda r: (r[1], yazi_turu_key(r[2]), -r[3]))

    print(
        "\nExpected ordering (revizyon_kodu, yazi_turu gelen first, proje_rev_no DESC):"
    )
    for i, rev in enumerate(sorted_revs, 1):
        print(
            f"  {i}. RevKod={rev[1]:3s}, YaziTuru={rev[2]:10s}, ProjeRevNo={rev[3]:2d}"
        )

    # Check if they're different
    current_order = [(r[1], r[2], r[3]) for r in revisions]
    expected_order = [(r[1], r[2], r[3]) for r in sorted_revs]

    if current_order != expected_order:
        print("\n⚠️  SIRA YANLIŞ! Düzeltme gerekli!")
    else:
        print("\n✅ Sıra doğru")

conn.close()
