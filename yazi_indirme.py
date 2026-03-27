# Wrapper for the updated downloader implementation
try:
    from yazi_indirme_new import main
except Exception as e:
    # Minimal fallback: show message and exit
    import sys
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Import Error", f"Failed to import updated downloader: {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()
