# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_wlasn_wydz.ui'
#
# Created by: PyQt5 UI code generator 5.12
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(739, 162)
        Dialog.setMinimumSize(QtCore.QSize(739, 162))
        Dialog.setMaximumSize(QtCore.QSize(739, 162))
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(10, 10, 101, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(10, 60, 101, 21))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(60, 110, 331, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")
        self.lineEdit_wydz = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_wydz.setGeometry(QtCore.QRect(120, 10, 511, 32))
        self.lineEdit_wydz.setObjectName("lineEdit_wydz")
        self.lineEdit_klu = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_klu.setGeometry(QtCore.QRect(120, 60, 511, 32))
        self.lineEdit_klu.setObjectName("lineEdit_klu")
        self.pushButton_wydz = QtWidgets.QPushButton(Dialog)
        self.pushButton_wydz.setGeometry(QtCore.QRect(640, 10, 88, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_wydz.setFont(font)
        self.pushButton_wydz.setObjectName("pushButton_wydz")
        self.pushButton_klu = QtWidgets.QPushButton(Dialog)
        self.pushButton_klu.setGeometry(QtCore.QRect(640, 60, 88, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_klu.setFont(font)
        self.pushButton_klu.setObjectName("pushButton_klu")
        self.pushButton_porzuc = QtWidgets.QPushButton(Dialog)
        self.pushButton_porzuc.setGeometry(QtCore.QRect(490, 110, 88, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_porzuc.setFont(font)
        self.pushButton_porzuc.setObjectName("pushButton_porzuc")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Własności w wydzieleniach"))
        self.label.setText(_translate("Dialog", "Wydzielenia:"))
        self.label_2.setText(_translate("Dialog", "Klasoużytki:"))
        self.pushButton_ok.setText(_translate("Dialog", "Wykonaj"))
        self.pushButton_wydz.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_klu.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_porzuc.setText(_translate("Dialog", "Porzuć"))


