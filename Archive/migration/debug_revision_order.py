from pathlib import Path
import sys

# Ensure package path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import ProjeTakipDB
from ui.panels.revision_panel import RevisionPanel
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

DB_PATH = r"c:/Users/Alper/Desktop/proje takip/veritabani_yedekleri/yedek_Acilis_20251123_161329.db"
PROJECT_ID = 103


def main():
    # Query DB ordering
    db = ProjeTakipDB(DB_PATH)
    revs = db.revizyonlari_getir(PROJECT_ID)
    print("DB revs (rev id, code, proj_rev_no, raw yazi_turu)")
    for r in revs:
        print(r.id, r.revizyon_kodu, r.proje_rev_no, r.yazi_turu)

    # GUI ordering using RevisionPanel (non-visible)
    QApplication.instance() or QApplication([])
    panel = RevisionPanel()
    panel.load_revisions(revs)
    print("\nRevisionPanel tree items after load:")
    header = panel.revizyon_agaci.header()
    print("Sorting enabled:", panel.revizyon_agaci.isSortingEnabled())
    print("Sort indicator shown:", header.isSortIndicatorShown())
    try:
        print(
            "Sort column, order:",
            header.sortIndicatorSection(),
            header.sortIndicatorOrder(),
        )
    except Exception:
        pass
    for i in range(panel.revizyon_agaci.topLevelItemCount()):
        it = panel.revizyon_agaci.topLevelItem(i)
        rev = it.data(0, Qt.UserRole)
        print(i, it.text(0), it.text(3), rev.id if rev else None)


if __name__ == "__main__":
    main()
