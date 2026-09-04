# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(560, 184)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_warstwa = QtWidgets.QLabel(Dialog)
        self.label_warstwa.setGeometry(QtCore.QRect(20, 16, 480, 16))
        self.label_warstwa.setFont(font)
        self.label_warstwa.setObjectName("label_warstwa")

        self.lineEdit_warstwa = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_warstwa.setGeometry(QtCore.QRect(20, 36, 440, 22))
        self.lineEdit_warstwa.setFont(font)
        self.lineEdit_warstwa.setObjectName("lineEdit_warstwa")

        self.pushButton_warstwa = QtWidgets.QPushButton(Dialog)
        self.pushButton_warstwa.setGeometry(QtCore.QRect(465, 36, 75, 23))
        self.pushButton_warstwa.setFont(font)
        self.pushButton_warstwa.setObjectName("pushButton_warstwa")

        self.checkBox_lz = QtWidgets.QCheckBox(Dialog)
        self.checkBox_lz.setGeometry(QtCore.QRect(20, 72, 520, 22))
        self.checkBox_lz.setFont(font)
        self.checkBox_lz.setChecked(True)
        self.checkBox_lz.setObjectName("checkBox_lz")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 124, 250, 34))
        self.pushButton_ok.setEnabled(False)
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(290, 124, 250, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate(
            "Dialog", "Doliterkuj wydzielenia (Aktualizacja UPUL)"))
        self.label_warstwa.setText(_translate("Dialog", "Warstwa wydzieleń:"))
        self.pushButton_warstwa.setText(_translate("Dialog", "Wybierz"))
        self.checkBox_lz.setText(_translate(
            "Dialog", "Dopisz Lz na podstawie opis_pkt"))
        self.pushButton_ok.setText(_translate("Dialog", "Wykonaj"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
