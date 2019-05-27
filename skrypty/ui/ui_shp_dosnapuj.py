# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_shp_dosnapuj.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(897, 205)
        Dialog.setMinimumSize(QtCore.QSize(897, 205))
        Dialog.setMaximumSize(QtCore.QSize(897, 205))
        self.pushButton_snap = QtWidgets.QPushButton(Dialog)
        self.pushButton_snap.setGeometry(QtCore.QRect(800, 20, 88, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_snap.setFont(font)
        self.pushButton_snap.setObjectName("pushButton_snap")
        self.pushButton_dz = QtWidgets.QPushButton(Dialog)
        self.pushButton_dz.setGeometry(QtCore.QRect(800, 70, 88, 34))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_dz.setFont(font)
        self.pushButton_dz.setObjectName("pushButton_dz")
        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 160, 471, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")
        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(650, 160, 241, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.pushButton_cancel.setFont(font)
        self.pushButton_cancel.setObjectName("pushButton_cancel")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(20, 30, 161, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(20, 70, 151, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setGeometry(QtCore.QRect(160, 120, 181, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.lineEdit_snap = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_snap.setGeometry(QtCore.QRect(180, 20, 611, 32))
        self.lineEdit_snap.setObjectName("lineEdit_snap")
        self.lineEdit_dz = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_dz.setGeometry(QtCore.QRect(180, 70, 611, 32))
        self.lineEdit_dz.setObjectName("lineEdit_dz")
        self.lineEdit_cm = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_cm.setGeometry(QtCore.QRect(350, 110, 121, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.lineEdit_cm.setFont(font)
        self.lineEdit_cm.setAlignment(QtCore.Qt.AlignCenter)
        self.lineEdit_cm.setObjectName("lineEdit_cm")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.pushButton_snap.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_dz.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_ok.setText(_translate("Dialog", "OK"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
        self.label.setText(_translate("Dialog", "Warstwa do dociągnięcia:"))
        self.label_2.setText(_translate("Dialog", "Działki ewidencyjne:"))
        self.label_3.setText(_translate("Dialog", "Zasięg snapowania: [cm]"))
        self.lineEdit_cm.setText(_translate("Dialog", "10"))


