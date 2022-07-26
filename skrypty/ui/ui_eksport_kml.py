# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_eksport_kml.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(649, 168)
        Dialog.setMinimumSize(QtCore.QSize(649, 168))
        Dialog.setMaximumSize(QtCore.QSize(649, 168))
        self.ok = QtWidgets.QPushButton(Dialog)
        self.ok.setGeometry(QtCore.QRect(50, 130, 331, 34))
        self.ok.setObjectName("ok")
        self.pushButton_porzuc = QtWidgets.QPushButton(Dialog)
        self.pushButton_porzuc.setGeometry(QtCore.QRect(420, 130, 88, 34))
        self.pushButton_porzuc.setObjectName("pushButton_porzuc")
        self.pushButton_ls = QtWidgets.QPushButton(Dialog)
        self.pushButton_ls.setGeometry(QtCore.QRect(550, 30, 88, 34))
        self.pushButton_ls.setObjectName("pushButton_ls")
        self.pushButton_dz = QtWidgets.QPushButton(Dialog)
        self.pushButton_dz.setGeometry(QtCore.QRect(550, 90, 88, 34))
        self.pushButton_dz.setObjectName("pushButton_dz")
        self.ls_sc = QtWidgets.QLineEdit(Dialog)
        self.ls_sc.setGeometry(QtCore.QRect(10, 30, 531, 32))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.ls_sc.setFont(font)
        self.ls_sc.setObjectName("ls_sc")
        self.dz_sc = QtWidgets.QLineEdit(Dialog)
        self.dz_sc.setGeometry(QtCore.QRect(10, 90, 531, 32))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.dz_sc.setFont(font)
        self.dz_sc.setObjectName("dz_sc")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(10, 10, 121, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(10, 70, 121, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Wybierz warstwy do przełożenia na KML"))
        self.ok.setText(_translate("Dialog", "OK"))
        self.pushButton_porzuc.setText(_translate("Dialog", "Porzuć"))
        self.pushButton_ls.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_dz.setText(_translate("Dialog", "Wybierz"))
        self.label.setText(_translate("Dialog", "Warstwa Ls"))
        self.label_2.setText(_translate("Dialog", "Warstwa DZKAT"))

