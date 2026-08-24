# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets

_NAGLOWKI_OBREBY = ["G", "Obręb", "Gmina", "Powiat", "Województwo", "Działek"]


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(820, 548)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_shp = QtWidgets.QLabel(Dialog)
        self.label_shp.setGeometry(QtCore.QRect(20, 16, 780, 16))
        self.label_shp.setFont(font)
        self.label_shp.setObjectName("label_shp")

        self.lineEdit_shp = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_shp.setGeometry(QtCore.QRect(20, 36, 695, 22))
        self.lineEdit_shp.setFont(font)
        self.lineEdit_shp.setObjectName("lineEdit_shp")

        self.pushButton_shp = QtWidgets.QPushButton(Dialog)
        self.pushButton_shp.setGeometry(QtCore.QRect(725, 36, 75, 23))
        self.pushButton_shp.setFont(font)
        self.pushButton_shp.setObjectName("pushButton_shp")

        self.label_baza = QtWidgets.QLabel(Dialog)
        self.label_baza.setGeometry(QtCore.QRect(20, 68, 780, 16))
        self.label_baza.setFont(font)
        self.label_baza.setObjectName("label_baza")

        self.lineEdit_baza = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(20, 88, 695, 22))
        self.lineEdit_baza.setFont(font)
        self.lineEdit_baza.setObjectName("lineEdit_baza")

        self.pushButton_baza = QtWidgets.QPushButton(Dialog)
        self.pushButton_baza.setGeometry(QtCore.QRect(725, 88, 75, 23))
        self.pushButton_baza.setFont(font)
        self.pushButton_baza.setObjectName("pushButton_baza")

        self.label_status = QtWidgets.QLabel(Dialog)
        self.label_status.setGeometry(QtCore.QRect(20, 118, 780, 34))
        self.label_status.setFont(font)
        self.label_status.setWordWrap(True)
        self.label_status.setObjectName("label_status")

        self.label_obreby = QtWidgets.QLabel(Dialog)
        self.label_obreby.setGeometry(QtCore.QRect(20, 158, 780, 16))
        self.label_obreby.setFont(font)
        self.label_obreby.setObjectName("label_obreby")

        self.tableWidget_obreby = QtWidgets.QTableWidget(Dialog)
        self.tableWidget_obreby.setGeometry(QtCore.QRect(20, 178, 780, 220))
        self.tableWidget_obreby.setFont(font)
        self.tableWidget_obreby.setObjectName("tableWidget_obreby")
        self.tableWidget_obreby.setColumnCount(len(_NAGLOWKI_OBREBY))
        self.tableWidget_obreby.setHorizontalHeaderLabels(_NAGLOWKI_OBREBY)
        self.tableWidget_obreby.verticalHeader().setVisible(False)
        for kolumna, szerokosc in enumerate([30, 230, 130, 130, 140, 70]):
            self.tableWidget_obreby.setColumnWidth(kolumna, szerokosc)

        self.groupBox_wlasciciel = QtWidgets.QGroupBox(Dialog)
        self.groupBox_wlasciciel.setGeometry(QtCore.QRect(20, 410, 780, 64))
        self.groupBox_wlasciciel.setFont(font)
        self.groupBox_wlasciciel.setObjectName("groupBox_wlasciciel")

        self.label_name1 = QtWidgets.QLabel(self.groupBox_wlasciciel)
        self.label_name1.setGeometry(QtCore.QRect(15, 24, 170, 16))
        self.label_name1.setFont(font)
        self.label_name1.setObjectName("label_name1")

        self.lineEdit_name1 = QtWidgets.QLineEdit(self.groupBox_wlasciciel)
        self.lineEdit_name1.setGeometry(QtCore.QRect(195, 22, 565, 22))
        self.lineEdit_name1.setFont(font)
        self.lineEdit_name1.setObjectName("lineEdit_name1")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 494, 380, 34))
        self.pushButton_ok.setEnabled(False)
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(420, 494, 380, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Przygotuj bazę z EWID"))
        self.label_shp.setText(_translate(
            "Dialog",
            "Warstwa SHP działek ewidencyjnych (z geoportalu, np. EWID.shp):"))
        self.pushButton_shp.setText(_translate("Dialog", "Wybierz"))
        self.label_baza.setText(_translate(
            "Dialog", "Baza docelowa (pusta, wcześniej skopiowana, .mdb):"))
        self.pushButton_baza.setText(_translate("Dialog", "Wybierz"))
        self.label_obreby.setText(_translate(
            "Dialog",
            "Obręby znalezione w warstwie (numery grup G1, G2… przydzielane "
            "automatycznie):"))
        self.groupBox_wlasciciel.setTitle(_translate(
            "Dialog", "Właściciel (jeden dla całej bazy)"))
        self.label_name1.setText(_translate(
            "Dialog", "Nazwisko/Nazwa (NAME_1) *:"))
        self.pushButton_ok.setText(_translate("Dialog", "Utwórz bazę"))
        self.pushButton_cancel.setText(_translate("Dialog", "Anuluj"))
