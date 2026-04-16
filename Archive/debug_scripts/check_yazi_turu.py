# Check current yazi_turu values and what they SHOULD be
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
        print(f"\n{'='*100}")
        print(f"Project: ID={proje_id}, Code={proj[1]}, Name={proj[2]}")
        print(f"{'='*100}\n")

        # Get ALL revision data
        revisions = cursor.execute(
            """SELECT r.id, r.revizyon_kodu, r.yazi_turu, r.proje_rev_no,
                      r.gelen_yazi_no, r.onay_yazi_no, r.red_yazi_no
               FROM revizyonlar r
               WHERE r.proje_id = ?
               ORDER BY r.revizyon_kodu, r.proje_rev_no DESC""",
            (proje_id,),
        ).fetchall()

        print(f"Total revisions: {len(revisions)}\n")

        # Analysis
        print("Current Data:")
        print(
            f"{'ID':<6} {'RevKod':<7} {'YaziTuru':<12} {'PrjRev':<7} {'Gelen?':<10} {'Onay?':<10} {'Red?':<10} {'Should Be':<12}"
        )
        print("-" * 100)

        for rev in revisions:
            rev_id, rev_kod, yazi_turu, prj_rev, gelen_no, onay_no, red_no = rev

            # Determine what yazi_turu SHOULD be
            has_gelen = gelen_no is not None and str(gelen_no).strip() != ""
            has_onay = onay_no is not None and str(onay_no).strip() != ""
            has_red = red_no is not None and str(red_no).strip() != ""

            if has_gelen:
                should_be = "gelen"
            elif has_onay or has_red:
                should_be = "giden"
            else:
                should_be = "yok"

            gelen_str = "YES" if has_gelen else ""
            onay_str = "YES" if has_onay else ""
            red_str = "YES" if has_red else ""

            mismatch = "" if yazi_turu == should_be else " <<<< MISMATCH"

            print(
                f"{rev_id:<6} {rev_kod:<7} {str(yazi_turu):<12} {prj_rev:<7} {gelen_str:<10} {onay_str:<10} {red_str:<10} {should_be:<12}{mismatch}"
            )

        # Count mismatches
        print("\n" + "=" * 100)
        mismatches = 0
        for rev in revisions:
            rev_id, rev_kod, yazi_turu, prj_rev, gelen_no, onay_no, red_no = rev
            has_gelen = gelen_no is not None and str(gelen_no).strip() != ""
            has_onay = onay_no is not None and str(onay_no).strip() != ""
            has_red = red_no is not None and str(red_no).strip() != ""

            if has_gelen:
                should_be = "gelen"
            elif has_onay or has_red:
                should_be = "giden"
            else:
                should_be = "yok"

            if yazi_turu != should_be:
                mismatches += 1

        print(f"\nMismatches found: {mismatches}")
        if mismatches > 0:
            print("Migration needed to fix yazi_turu values!")
        else:
            print("All yazi_turu values are correct.")

else:
    print("No projects containing 4269 found")

conn.close()
