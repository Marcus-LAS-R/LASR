# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(520, 190)
        Dialog.setMinimumSize(QtCore.QSize(520, 190))
        Dialog.setMaximumSize(QtCore.QSize(520, 190))

        font = QtGui.QFont()
        font.setFamily("Arial")

        self.label_wydz = QtWidgets.QLabel(Dialog)
        self.label_wydz.setGeometry(QtCore.QRect(20, 20, 120, 16))
        self.label_wydz.setFont(font)
        self.label_wydz.setObjectName("label_wydz")

        self.lineEdit_wydz = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_wydz.setGeometry(QtCore.QRect(145, 18, 280, 22))
        self.lineEdit_wydz.setFont(font)
        self.lineEdit_wydz.setObjectName("lineEdit_wydz")

        self.pushButton_wydz = QtWidgets.QPushButton(Dialog)
        self.pushButton_wydz.setGeometry(QtCore.QRect(435, 18, 75, 23))
        self.pushButton_wydz.setFont(font)
        self.pushButton_wydz.setObjectName("pushButton_wydz")

        self.label_baza = QtWidgets.QLabel(Dialog)
        self.label_baza.setGeometry(QtCore.QRect(20, 60, 120, 16))
        self.label_baza.setFont(font)
        self.label_baza.setObjectName("label_baza")

        self.lineEdit_baza = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(145, 58, 280, 22))
        self.lineEdit_baza.setFont(font)
        self.lineEdit_baza.setObjectName("lineEdit_baza")

        self.pushButton_baza = QtWidgets.QPushButton(Dialog)
        self.pushButton_baza.setGeometry(QtCore.QRect(435, 58, 75, 23))
        self.pushButton_baza.setFont(font)
        self.pushButton_baza.setObjectName("pushButton_baza")

        self.label_wyj_opis = QtWidgets.QLabel(Dialog)
        self.label_wyj_opis.setGeometry(QtCore.QRect(20, 100, 120, 16))
        self.label_wyj_opis.setFont(font)
        self.label_wyj_opis.setObjectName("label_wyj_opis")

        font_it = QtGui.QFont()
        font_it.setFamily("Arial")
        font_it.setItalic(True)

        self.label_wyj = QtWidgets.QLabel(Dialog)
        self.label_wyj.setGeometry(QtCore.QRect(145, 100, 355, 16))
        self.label_wyj.setFont(font_it)
        self.label_wyj.setText("")
        self.label_wyj.setObjectName("label_wyj")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(100, 148, 201, 31))
        self.pushButton_ok.setEnabled(False)
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(360, 148, 75, 31))
        self.pushButton_cancel.setFont(font)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        self.pushButton_ok.clicked.connect(Dialog.accept)
        self.pushButton_cancel.clicked.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Przygotuj cięcie ST UPUL"))
        self.label_wydz.setText(_translate("Dialog", "Warstwa starych wydzień:"))
        self.label_baza.setText(_translate("Dialog", "Baza danych stara:"))
        self.label_wyj_opis.setText(_translate("Dialog", "Folder wynikowy:"))
        self.pushButton_wydz.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_baza.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_ok.setText(_translate("Dialog", "Uruchom"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
