# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_baza_klonuj.ui'
#
# Created by: PyQt5 UI code generator 5.12
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Ui_Dialog(object):
    def setupUi(self, Ui_Dialog):
        Ui_Dialog.setObjectName("Ui_Dialog")
        Ui_Dialog.resize(649, 154)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Ui_Dialog.setFont(font)
        self.pushButton_ok = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(70, 110, 251, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")
        self.pushButton_cancel = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(380, 110, 181, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(8)
        self.pushButton_cancel.setFont(font)
        self.pushButton_cancel.setObjectName("pushButton_cancel")
        self.lineEdit_wydz = QtWidgets.QLineEdit(Ui_Dialog)
        self.lineEdit_wydz.setGeometry(QtCore.QRect(160, 10, 381, 32))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.lineEdit_wydz.setFont(font)
        self.lineEdit_wydz.setObjectName("lineEdit_wydz")
        self.lineEdit_baza = QtWidgets.QLineEdit(Ui_Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(159, 60, 381, 32))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.lineEdit_baza.setFont(font)
        self.lineEdit_baza.setObjectName("lineEdit_baza")
        self.label = QtWidgets.QLabel(Ui_Dialog)
        self.label.setGeometry(QtCore.QRect(20, 20, 131, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(Ui_Dialog)
        self.label_2.setGeometry(QtCore.QRect(20, 70, 131, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.pushButton_wydz = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_wydz.setGeometry(QtCore.QRect(550, 10, 88, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_wydz.setFont(font)
        self.pushButton_wydz.setObjectName("pushButton_wydz")
        self.pushButton_baza = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_baza.setGeometry(QtCore.QRect(550, 60, 88, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_baza.setFont(font)
        self.pushButton_baza.setObjectName("pushButton_baza")

        self.retranslateUi(Ui_Dialog)
        QtCore.QMetaObject.connectSlotsByName(Ui_Dialog)

    def retranslateUi(self, Ui_Dialog):
        _translate = QtCore.QCoreApplication.translate
        Ui_Dialog.setWindowTitle(_translate("Ui_Dialog", "Klonuj wydzielenia"))
        self.pushButton_ok.setText(_translate("Ui_Dialog", "Wykonaj"))
        self.pushButton_cancel.setText(_translate("Ui_Dialog", "Porzuć"))
        self.label.setText(_translate("Ui_Dialog", "Plik tekstowy:"))
        self.label_2.setText(_translate("Ui_Dialog", "Baza Taksatora:"))
        self.pushButton_wydz.setText(_translate("Ui_Dialog", "Wybierz"))
        self.pushButton_baza.setText(_translate("Ui_Dialog", "Wybierz"))


