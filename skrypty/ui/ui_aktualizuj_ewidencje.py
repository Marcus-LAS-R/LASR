# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_aktualizuj_ewidencje.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(700, 230)
        Dialog.setMinimumSize(QtCore.QSize(700, 230))
        Dialog.setMaximumSize(QtCore.QSize(700, 230))

        self.label_oryg = QtWidgets.QLabel(Dialog)
        self.label_oryg.setGeometry(QtCore.QRect(20, 25, 171, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_oryg.setFont(font)
        self.label_oryg.setObjectName("label_oryg")

        self.lineEdit_oryg = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_oryg.setGeometry(QtCore.QRect(200, 20, 400, 32))
        self.lineEdit_oryg.setObjectName("lineEdit_oryg")

        self.pushButton_oryg = QtWidgets.QPushButton(Dialog)
        self.pushButton_oryg.setGeometry(QtCore.QRect(610, 20, 70, 32))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_oryg.setFont(font)
        self.pushButton_oryg.setObjectName("pushButton_oryg")

        self.label_nowa = QtWidgets.QLabel(Dialog)
        self.label_nowa.setGeometry(QtCore.QRect(20, 75, 171, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_nowa.setFont(font)
        self.label_nowa.setObjectName("label_nowa")

        self.lineEdit_nowa = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_nowa.setGeometry(QtCore.QRect(200, 70, 400, 32))
        self.lineEdit_nowa.setObjectName("lineEdit_nowa")

        self.pushButton_nowa = QtWidgets.QPushButton(Dialog)
        self.pushButton_nowa.setGeometry(QtCore.QRect(610, 70, 70, 32))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_nowa.setFont(font)
        self.pushButton_nowa.setObjectName("pushButton_nowa")

        self.label_wyjscie = QtWidgets.QLabel(Dialog)
        self.label_wyjscie.setGeometry(QtCore.QRect(20, 125, 171, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_wyjscie.setFont(font)
        self.label_wyjscie.setObjectName("label_wyjscie")

        self.lineEdit_wyjscie = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_wyjscie.setGeometry(QtCore.QRect(200, 120, 400, 32))
        self.lineEdit_wyjscie.setObjectName("lineEdit_wyjscie")

        self.pushButton_wyjscie = QtWidgets.QPushButton(Dialog)
        self.pushButton_wyjscie.setGeometry(QtCore.QRect(610, 120, 70, 32))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_wyjscie.setFont(font)
        self.pushButton_wyjscie.setObjectName("pushButton_wyjscie")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 172, 441, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(480, 172, 200, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_cancel.setFont(font)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Aktualizacja ewidencji N-ctwo"))
        self.label_oryg.setText(_translate("Dialog", "Warstwa ORYG (dawna):"))
        self.pushButton_oryg.setText(_translate("Dialog", "Wybierz"))
        self.label_nowa.setText(_translate("Dialog", "Warstwa NOWA (aktualna):"))
        self.pushButton_nowa.setText(_translate("Dialog", "Wybierz"))
        self.label_wyjscie.setText(_translate("Dialog", "Zapisz wynik jako:"))
        self.pushButton_wyjscie.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_ok.setText(_translate("Dialog", "OK"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
