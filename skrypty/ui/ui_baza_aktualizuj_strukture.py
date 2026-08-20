# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(560, 400)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        font_male = QtGui.QFont()
        font_male.setFamily("Arial")
        font_male.setPointSize(8)
        font_male.setItalic(True)

        self.label_naglowek = QtWidgets.QLabel(Dialog)
        self.label_naglowek.setGeometry(QtCore.QRect(20, 10, 520, 20))
        self.label_naglowek.setFont(font)
        self.label_naglowek.setObjectName("label_naglowek")

        # --- katalog ze starymi bazami ---
        self.label_katalog = QtWidgets.QLabel(Dialog)
        self.label_katalog.setGeometry(QtCore.QRect(20, 36, 500, 16))
        self.label_katalog.setFont(font_male)
        self.label_katalog.setObjectName("label_katalog")

        self.lineEdit_katalog = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_katalog.setGeometry(QtCore.QRect(20, 54, 400, 26))
        self.lineEdit_katalog.setFont(font)
        self.lineEdit_katalog.setObjectName("lineEdit_katalog")

        self.pushButton_przegladaj_katalog = QtWidgets.QPushButton(Dialog)
        self.pushButton_przegladaj_katalog.setGeometry(QtCore.QRect(430, 54, 90, 26))
        self.pushButton_przegladaj_katalog.setFont(font)
        self.pushButton_przegladaj_katalog.setObjectName("pushButton_przegladaj_katalog")

        self.label_status_katalog = QtWidgets.QLabel(Dialog)
        self.label_status_katalog.setGeometry(QtCore.QRect(20, 84, 500, 16))
        self.label_status_katalog.setFont(font_male)
        self.label_status_katalog.setObjectName("label_status_katalog")

        self.linia1 = QtWidgets.QFrame(Dialog)
        self.linia1.setGeometry(QtCore.QRect(20, 108, 520, 3))
        self.linia1.setFrameShape(QtWidgets.QFrame.HLine)
        self.linia1.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.linia1.setObjectName("linia1")

        # --- tryb ---
        self.radioButton_polacz = QtWidgets.QRadioButton(Dialog)
        self.radioButton_polacz.setGeometry(QtCore.QRect(20, 120, 520, 22))
        self.radioButton_polacz.setFont(font)
        self.radioButton_polacz.setChecked(True)
        self.radioButton_polacz.setObjectName("radioButton_polacz")

        self.radioButton_szablon = QtWidgets.QRadioButton(Dialog)
        self.radioButton_szablon.setGeometry(QtCore.QRect(20, 144, 520, 22))
        self.radioButton_szablon.setFont(font)
        self.radioButton_szablon.setObjectName("radioButton_szablon")

        self.linia2 = QtWidgets.QFrame(Dialog)
        self.linia2.setGeometry(QtCore.QRect(20, 174, 520, 3))
        self.linia2.setFrameShape(QtWidgets.QFrame.HLine)
        self.linia2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.linia2.setObjectName("linia2")

        # --- pola wspolne dla obu trybow ---
        self.label_szablon = QtWidgets.QLabel(Dialog)
        self.label_szablon.setGeometry(QtCore.QRect(20, 186, 500, 16))
        self.label_szablon.setFont(font_male)
        self.label_szablon.setObjectName("label_szablon")

        self.lineEdit_szablon = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_szablon.setGeometry(QtCore.QRect(20, 204, 400, 26))
        self.lineEdit_szablon.setFont(font)
        self.lineEdit_szablon.setObjectName("lineEdit_szablon")

        self.pushButton_przegladaj_szablon = QtWidgets.QPushButton(Dialog)
        self.pushButton_przegladaj_szablon.setGeometry(QtCore.QRect(430, 204, 90, 26))
        self.pushButton_przegladaj_szablon.setFont(font)
        self.pushButton_przegladaj_szablon.setObjectName("pushButton_przegladaj_szablon")

        self.label_folder_wyjsciowy = QtWidgets.QLabel(Dialog)
        self.label_folder_wyjsciowy.setGeometry(QtCore.QRect(20, 242, 500, 16))
        self.label_folder_wyjsciowy.setFont(font_male)
        self.label_folder_wyjsciowy.setObjectName("label_folder_wyjsciowy")

        self.lineEdit_folder_wyjsciowy = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_folder_wyjsciowy.setGeometry(QtCore.QRect(20, 260, 400, 26))
        self.lineEdit_folder_wyjsciowy.setFont(font)
        self.lineEdit_folder_wyjsciowy.setObjectName("lineEdit_folder_wyjsciowy")

        self.pushButton_przegladaj_folder = QtWidgets.QPushButton(Dialog)
        self.pushButton_przegladaj_folder.setGeometry(QtCore.QRect(430, 260, 90, 26))
        self.pushButton_przegladaj_folder.setFont(font)
        self.pushButton_przegladaj_folder.setObjectName("pushButton_przegladaj_folder")

        self.label_info = QtWidgets.QLabel(Dialog)
        self.label_info.setGeometry(QtCore.QRect(20, 296, 520, 40))
        self.label_info.setFont(font)
        self.label_info.setWordWrap(True)
        self.label_info.setObjectName("label_info")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 348, 300, 34))
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(340, 348, 200, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Aktualizuj strukturę bazy"))
        self.label_naglowek.setText(_translate(
            "Dialog", "Wskaż stare bazy i sposób ich aktualizacji:"))
        self.label_katalog.setText(_translate(
            "Dialog", "Katalog ze starymi bazami (.mdb/.sqlite):"))
        self.pushButton_przegladaj_katalog.setText(_translate("Dialog", "Przeglądaj..."))
        self.label_status_katalog.setText(_translate("Dialog", ""))
        self.radioButton_polacz.setText(_translate(
            "Dialog", "Połącz wszystkie stare bazy w jedną (na podstawie szablonu)"))
        self.radioButton_szablon.setText(_translate(
            "Dialog", "Zaktualizuj każdą osobno (kopia szablonu na każdą starą bazę)"))
        self.label_szablon.setText(_translate(
            "Dialog", "Szablon bazy (kopiowany do folderu eksportu, oryginał nie jest zmieniany):"))
        self.pushButton_przegladaj_szablon.setText(_translate("Dialog", "Przeglądaj..."))
        self.label_folder_wyjsciowy.setText(_translate(
            "Dialog", "Folder eksportu (gdzie zapisać zaktualizowane bazy):"))
        self.pushButton_przegladaj_folder.setText(_translate("Dialog", "Przeglądaj..."))
        self.label_info.setText(_translate("Dialog", ""))
        self.pushButton_ok.setText(_translate("Dialog", "Dalej"))
        self.pushButton_cancel.setText(_translate("Dialog", "Anuluj"))
