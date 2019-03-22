# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_baza_zabiegi.ui'
#
# Created by: PyQt5 UI code generator 5.12
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(912, 391)
        self.pushButton_baza = QtWidgets.QPushButton(Dialog)
        self.pushButton_baza.setGeometry(QtCore.QRect(770, 30, 121, 41))
        self.pushButton_baza.setObjectName("pushButton_baza")
        self.lineEdit_baza = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(160, 30, 601, 41))
        self.lineEdit_baza.setObjectName("lineEdit_baza")
        self.grupBox = QtWidgets.QGroupBox(Dialog)
        self.grupBox.setGeometry(QtCore.QRect(20, 90, 871, 211))
        self.grupBox.setObjectName("grupBox")
        self.radioButton_sprawdz = QtWidgets.QRadioButton(self.grupBox)
        self.radioButton_sprawdz.setGeometry(QtCore.QRect(30, 50, 811, 22))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.radioButton_sprawdz.setFont(font)
        self.radioButton_sprawdz.setChecked(True)
        self.radioButton_sprawdz.setObjectName("radioButton_sprawdz")
        self.radioButton_uzpelnij = QtWidgets.QRadioButton(self.grupBox)
        self.radioButton_uzpelnij.setGeometry(QtCore.QRect(30, 100, 821, 22))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.radioButton_uzpelnij.setFont(font)
        self.radioButton_uzpelnij.setObjectName("radioButton_uzpelnij")
        self.radioButton_dopisz = QtWidgets.QRadioButton(self.grupBox)
        self.radioButton_dopisz.setGeometry(QtCore.QRect(30, 150, 811, 22))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.radioButton_dopisz.setFont(font)
        self.radioButton_dopisz.setObjectName("radioButton_dopisz")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(30, 30, 121, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 320, 571, 61))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")
        self.pushButton_porzuc = QtWidgets.QPushButton(Dialog)
        self.pushButton_porzuc.setGeometry(QtCore.QRect(670, 330, 151, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_porzuc.setFont(font)
        self.pushButton_porzuc.setObjectName("pushButton_porzuc")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Sprawdź / Uzupełnij bazę"))
        self.pushButton_baza.setText(_translate("Dialog", "Wybierz"))
        self.grupBox.setTitle(_translate("Dialog", "Wybierz czynność:"))
        self.radioButton_sprawdz.setText(_translate("Dialog", "Sprawdź wpisane zabiegi w bazie (Nie modyfikuje zawartości)"))
        self.radioButton_uzpelnij.setText(_translate("Dialog", "Uzupełnij powierzchnię zabiegów w bazie (Modyfikuje zawartość bazy, nie dodaje nowych rekordów)"))
        self.radioButton_dopisz.setText(_translate("Dialog", "Dopisz zabiegi do bazy (dopisuje brakujące zabiegi oraz poprawia niezgodne powierzchnie)"))
        self.label.setText(_translate("Dialog", "Baza taksatora:"))
        self.pushButton_ok.setText(_translate("Dialog", "OK"))
        self.pushButton_porzuc.setText(_translate("Dialog", "Porzuć"))


