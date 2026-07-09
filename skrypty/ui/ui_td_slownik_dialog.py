# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(520, 560)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_info = QtWidgets.QLabel(Dialog)
        self.label_info.setGeometry(QtCore.QRect(20, 12, 480, 36))
        self.label_info.setFont(font)
        self.label_info.setWordWrap(True)
        self.label_info.setObjectName("label_info")

        self.tableWidget = QtWidgets.QTableWidget(Dialog)
        self.tableWidget.setGeometry(QtCore.QRect(20, 56, 480, 400))
        self.tableWidget.setFont(font)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem())
        self.tableWidget.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem())
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.setColumnWidth(0, 110)

        self.pushButton_dodaj = QtWidgets.QPushButton(Dialog)
        self.pushButton_dodaj.setGeometry(QtCore.QRect(20, 464, 150, 26))
        self.pushButton_dodaj.setFont(font)
        self.pushButton_dodaj.setObjectName("pushButton_dodaj")

        self.pushButton_usun = QtWidgets.QPushButton(Dialog)
        self.pushButton_usun.setGeometry(QtCore.QRect(180, 464, 150, 26))
        self.pushButton_usun.setFont(font)
        self.pushButton_usun.setObjectName("pushButton_usun")

        self.pushButton_zapisz = QtWidgets.QPushButton(Dialog)
        self.pushButton_zapisz.setGeometry(QtCore.QRect(20, 500, 150, 34))
        font_zapisz = QtGui.QFont()
        font_zapisz.setFamily("Arial")
        font_zapisz.setBold(True)
        font_zapisz.setWeight(75)
        self.pushButton_zapisz.setFont(font_zapisz)
        self.pushButton_zapisz.setObjectName("pushButton_zapisz")

        self.pushButton_resetuj = QtWidgets.QPushButton(Dialog)
        self.pushButton_resetuj.setGeometry(QtCore.QRect(180, 500, 150, 34))
        self.pushButton_resetuj.setFont(font)
        self.pushButton_resetuj.setObjectName("pushButton_resetuj")

        self.pushButton_zamknij = QtWidgets.QPushButton(Dialog)
        self.pushButton_zamknij.setGeometry(QtCore.QRect(340, 500, 160, 34))
        self.pushButton_zamknij.setFont(font)
        self.pushButton_zamknij.setObjectName("pushButton_zamknij")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate(
            "Dialog", "Słownik TD (typ drzewostanu docelowego)"))
        self.label_info.setText(_translate(
            "Dialog",
            "Typ siedliskowy lasu (TSL) -> gatunki docelowe (kolejność = "
            "ważność, gatunki oddzielaj spacją, np. \"SO JD BK\")."))
        item0 = self.tableWidget.horizontalHeaderItem(0)
        item0.setText(_translate("Dialog", "TSL"))
        item1 = self.tableWidget.horizontalHeaderItem(1)
        item1.setText(_translate("Dialog", "Gatunki docelowe"))
        self.pushButton_dodaj.setText(_translate("Dialog", "Dodaj wiersz"))
        self.pushButton_usun.setText(_translate("Dialog", "Usuń wiersz"))
        self.pushButton_zapisz.setText(_translate("Dialog", "Zapisz"))
        self.pushButton_zapisz.setToolTip(_translate(
            "Dialog", "Zapisz zmiany w słowniku TD"))
        self.pushButton_resetuj.setText(_translate("Dialog", "Resetuj"))
        self.pushButton_resetuj.setToolTip(_translate(
            "Dialog", "Przywróć słownik domyślny TPU"))
        self.pushButton_zamknij.setText(_translate("Dialog", "Zamknij"))
