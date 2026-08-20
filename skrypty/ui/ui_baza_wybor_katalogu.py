# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(520, 150)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_naglowek = QtWidgets.QLabel(Dialog)
        self.label_naglowek.setGeometry(QtCore.QRect(20, 12, 480, 20))
        self.label_naglowek.setFont(font)
        self.label_naglowek.setObjectName("label_naglowek")

        self.lineEdit_katalog = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_katalog.setGeometry(QtCore.QRect(20, 42, 380, 26))
        self.lineEdit_katalog.setFont(font)
        self.lineEdit_katalog.setObjectName("lineEdit_katalog")

        self.pushButton_przegladaj = QtWidgets.QPushButton(Dialog)
        self.pushButton_przegladaj.setGeometry(QtCore.QRect(410, 42, 90, 26))
        self.pushButton_przegladaj.setFont(font)
        self.pushButton_przegladaj.setObjectName("pushButton_przegladaj")

        self.label_podpowiedz = QtWidgets.QLabel(Dialog)
        self.label_podpowiedz.setGeometry(QtCore.QRect(20, 76, 480, 20))
        font_male = QtGui.QFont()
        font_male.setFamily("Arial")
        font_male.setPointSize(8)
        font_male.setItalic(True)
        self.label_podpowiedz.setFont(font_male)
        self.label_podpowiedz.setObjectName("label_podpowiedz")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 100, 300, 34))
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(340, 100, 160, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Katalog z bazami danych"))
        self.label_naglowek.setText(_translate(
            "Dialog", "Wskaż katalog z bazami danych:"))
        self.pushButton_przegladaj.setText(_translate("Dialog", "Przeglądaj..."))
        self.label_podpowiedz.setText(_translate(
            "Dialog", "Możesz wkleić ścieżkę bezpośrednio w pole powyżej (Ctrl+V)."))
        self.pushButton_ok.setText(_translate("Dialog", "Dalej"))
        self.pushButton_cancel.setText(_translate("Dialog", "Anuluj"))
