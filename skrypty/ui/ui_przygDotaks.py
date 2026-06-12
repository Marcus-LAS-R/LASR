# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(520, 230)
        Dialog.setMinimumSize(QtCore.QSize(520, 230))
        Dialog.setMaximumSize(QtCore.QSize(520, 230))

        font = QtGui.QFont()
        font.setFamily("Arial")

        self.label_ls = QtWidgets.QLabel(Dialog)
        self.label_ls.setGeometry(QtCore.QRect(20, 20, 120, 16))
        self.label_ls.setFont(font)
        self.label_ls.setObjectName("label_ls")

        self.lineEdit_ls = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_ls.setGeometry(QtCore.QRect(145, 18, 280, 22))
        self.lineEdit_ls.setFont(font)
        self.lineEdit_ls.setObjectName("lineEdit_ls")

        self.pushButton_ls = QtWidgets.QPushButton(Dialog)
        self.pushButton_ls.setGeometry(QtCore.QRect(435, 18, 75, 23))
        self.pushButton_ls.setFont(font)
        self.pushButton_ls.setObjectName("pushButton_ls")

        self.label_stare = QtWidgets.QLabel(Dialog)
        self.label_stare.setGeometry(QtCore.QRect(20, 60, 120, 16))
        self.label_stare.setFont(font)
        self.label_stare.setObjectName("label_stare")

        self.lineEdit_stare = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_stare.setGeometry(QtCore.QRect(145, 58, 280, 22))
        self.lineEdit_stare.setFont(font)
        self.lineEdit_stare.setObjectName("lineEdit_stare")

        self.pushButton_stare = QtWidgets.QPushButton(Dialog)
        self.pushButton_stare.setGeometry(QtCore.QRect(435, 58, 75, 23))
        self.pushButton_stare.setFont(font)
        self.pushButton_stare.setObjectName("pushButton_stare")

        self.label_baza = QtWidgets.QLabel(Dialog)
        self.label_baza.setGeometry(QtCore.QRect(20, 100, 120, 16))
        self.label_baza.setFont(font)
        self.label_baza.setObjectName("label_baza")

        self.lineEdit_baza = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(145, 98, 280, 22))
        self.lineEdit_baza.setFont(font)
        self.lineEdit_baza.setObjectName("lineEdit_baza")

        self.pushButton_baza = QtWidgets.QPushButton(Dialog)
        self.pushButton_baza.setGeometry(QtCore.QRect(435, 98, 75, 23))
        self.pushButton_baza.setFont(font)
        self.pushButton_baza.setObjectName("pushButton_baza")

        self.label_wyj_opis = QtWidgets.QLabel(Dialog)
        self.label_wyj_opis.setGeometry(QtCore.QRect(20, 140, 120, 16))
        self.label_wyj_opis.setFont(font)
        self.label_wyj_opis.setObjectName("label_wyj_opis")

        font_it = QtGui.QFont()
        font_it.setFamily("Arial")
        font_it.setItalic(True)

        self.label_wyj = QtWidgets.QLabel(Dialog)
        self.label_wyj.setGeometry(QtCore.QRect(145, 140, 355, 16))
        self.label_wyj.setFont(font_it)
        self.label_wyj.setText("")
        self.label_wyj.setObjectName("label_wyj")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(100, 188, 201, 31))
        self.pushButton_ok.setEnabled(False)
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(360, 188, 75, 31))
        self.pushButton_cancel.setFont(font)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        self.pushButton_ok.clicked.connect(Dialog.accept)
        self.pushButton_cancel.clicked.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Przygotuj warstwy DOTAKS"))
        self.label_ls.setText(_translate("Dialog", "Warstwa LS nowe:"))
        self.label_stare.setText(_translate("Dialog", "Wydzielenia stare:"))
        self.label_baza.setText(_translate("Dialog", "Baza danych stara:"))
        self.label_wyj_opis.setText(_translate("Dialog", "Folder wynikowy:"))
        self.pushButton_ls.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_stare.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_baza.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_ok.setText(_translate("Dialog", "Uruchom"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
