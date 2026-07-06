# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(560, 214)
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

        self.label_rozmiar = QtWidgets.QLabel(Dialog)
        self.label_rozmiar.setGeometry(QtCore.QRect(20, 68, 300, 22))
        self.label_rozmiar.setFont(font)
        self.label_rozmiar.setObjectName("label_rozmiar")

        self.spinBox_rozmiar = QtWidgets.QSpinBox(Dialog)
        self.spinBox_rozmiar.setGeometry(QtCore.QRect(330, 68, 100, 22))
        self.spinBox_rozmiar.setFont(font)
        self.spinBox_rozmiar.setMinimum(100)
        self.spinBox_rozmiar.setMaximum(20000)
        self.spinBox_rozmiar.setSingleStep(100)
        self.spinBox_rozmiar.setValue(2000)
        self.spinBox_rozmiar.setSuffix(" m")
        self.spinBox_rozmiar.setObjectName("spinBox_rozmiar")

        self.label_folder = QtWidgets.QLabel(Dialog)
        self.label_folder.setGeometry(QtCore.QRect(20, 100, 480, 16))
        self.label_folder.setFont(font)
        self.label_folder.setObjectName("label_folder")

        self.lineEdit_folder = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_folder.setGeometry(QtCore.QRect(20, 120, 440, 22))
        self.lineEdit_folder.setFont(font)
        self.lineEdit_folder.setObjectName("lineEdit_folder")

        self.pushButton_folder = QtWidgets.QPushButton(Dialog)
        self.pushButton_folder.setGeometry(QtCore.QRect(465, 120, 75, 23))
        self.pushButton_folder.setFont(font)
        self.pushButton_folder.setObjectName("pushButton_folder")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 160, 250, 34))
        self.pushButton_ok.setEnabled(False)
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(290, 160, 250, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Ściągnij dane z BDL"))
        self.label_warstwa.setText(_translate(
            "Dialog", "Warstwa zasięgu (OBR lub GMIN), EPSG:2180:"))
        self.pushButton_warstwa.setText(_translate("Dialog", "Wybierz"))
        self.label_rozmiar.setText(_translate(
            "Dialog", "Rozmiar oczka siatki:"))
        self.label_folder.setText(_translate(
            "Dialog", "Folder wyjściowy:"))
        self.pushButton_folder.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_ok.setText(_translate("Dialog", "Pobierz"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
