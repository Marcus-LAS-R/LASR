from PyQt5.QtWidgets import QDialog, QFileDialog

from .ui.ui_baza_wybor_katalogu import Ui_Dialog


def przegladaj_katalog_z_podgladem(parent, tytul, wzorzec, start=''):
    """Otwiera customowy (nie-natywny) QFileDialog w trybie Directory,
    pokazujący pliki pasujące do wzorca obok folderów (wyszarzone,
    niewybieralne) - żeby było widać, czy trafiono we właściwe miejsce,
    zanim się zatwierdzi (natywny selektor na Windows pokazuje wyłącznie
    podfoldery, więc katalog z samymi bazami wyglądałby pusty). Zwraca
    wybrany katalog, albo None jeśli użytkownik zrezygnował."""
    dlg = QFileDialog(parent, tytul, start)
    dlg.setFileMode(QFileDialog.Directory)
    dlg.setOption(QFileDialog.ShowDirsOnly, False)
    dlg.setOption(QFileDialog.DontUseNativeDialog, True)
    dlg.setNameFilter(wzorzec)
    dlg.setLabelText(QFileDialog.LookIn, "Szukaj w:")
    dlg.setLabelText(QFileDialog.FileName, "Folder:")
    dlg.setLabelText(QFileDialog.FileType, "Pliki typu:")
    dlg.setLabelText(QFileDialog.Accept, "Wybierz folder")
    dlg.setLabelText(QFileDialog.Reject, "Anuluj")
    if dlg.exec_() == QDialog.Accepted and dlg.selectedFiles():
        return dlg.selectedFiles()[0]
    return None


class WybierzKatalogDialog(QDialog):
    """Dialog do wskazania katalogu z bazami danych (.mdb/.sqlite) -
    pole tekstowe wspiera wklejanie ścieżki (Ctrl+V), przycisk Przeglądaj
    otwiera dodatkowo customowy QFileDialog pokazujący pliki pasujące do
    wzorca obok folderów (natywny selektor na Windows pokazuje wyłącznie
    podfoldery, więc katalog z samymi bazami wyglądałby pusty)."""

    def __init__(self, iface, tytul, wzorzec):
        super().__init__(iface.mainWindow())
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle(tytul)
        self.wzorzec = wzorzec

        self.ui.lineEdit_katalog.textChanged.connect(self._aktualizuj_ok)
        self.ui.pushButton_przegladaj.clicked.connect(self._przegladaj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)
        self._aktualizuj_ok()

    def _przegladaj(self):
        start = self.ui.lineEdit_katalog.text() or ''
        sc = przegladaj_katalog_z_podgladem(
            self, "Katalog z bazami danych", self.wzorzec, start)
        if sc:
            self.ui.lineEdit_katalog.setText(sc)

    def _aktualizuj_ok(self, *_):
        self.ui.pushButton_ok.setEnabled(self.ui.lineEdit_katalog.text().strip() != '')

    def katalog(self):
        # obcina cudzyslowy - "Kopiuj jako sciezke" w eksploratorze Windows
        # otacza wklejona sciezke cudzyslowami
        return self.ui.lineEdit_katalog.text().strip().strip('"')
