# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Ui_Dialog):
        Ui_Dialog.setObjectName("Ui_Dialog")
        Ui_Dialog.resize(480, 170)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Ui_Dialog.setFont(font)

        self.label_folder = QtWidgets.QLabel(Ui_Dialog)
        self.label_folder.setGeometry(QtCore.QRect(20, 16, 400, 16))
        self.label_folder.setFont(font)
        self.label_folder.setObjectName("label_folder")

        self.lineEdit_folder = QtWidgets.QLineEdit(Ui_Dialog)
        self.lineEdit_folder.setGeometry(QtCore.QRect(20, 36, 360, 22))
        self.lineEdit_folder.setFont(font)
        self.lineEdit_folder.setObjectName("lineEdit_folder")

        self.pushButton_folder = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_folder.setGeometry(QtCore.QRect(385, 36, 75, 23))
        self.pushButton_folder.setFont(font)
        self.pushButton_folder.setObjectName("pushButton_folder")

        self.checkBox_kwerendy = QtWidgets.QCheckBox(Ui_Dialog)
        self.checkBox_kwerendy.setGeometry(QtCore.QRect(20, 78, 420, 22))
        font_cb = QtGui.QFont()
        font_cb.setFamily("Arial")
        self.checkBox_kwerendy.setFont(font_cb)
        self.checkBox_kwerendy.setChecked(True)
        self.checkBox_kwerendy.setObjectName("checkBox_kwerendy")

        self.pushButton_ok = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 120, 210, 34))
        self.pushButton_ok.setEnabled(False)
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(250, 120, 210, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Ui_Dialog)
        QtCore.QMetaObject.connectSlotsByName(Ui_Dialog)

    def retranslateUi(self, Ui_Dialog):
        _translate = QtCore.QCoreApplication.translate
        Ui_Dialog.setWindowTitle(_translate("Ui_Dialog", "Anonimizuj bazy - opcje"))
        self.label_folder.setText(_translate("Ui_Dialog", "Katalog z bazami danych:"))
        self.pushButton_folder.setText(_translate("Ui_Dialog", "Wybierz"))
        self.checkBox_kwerendy.setText(_translate("Ui_Dialog", "Usuń kwerendy z baz"))
        self.pushButton_ok.setText(_translate("Ui_Dialog", "Wykonaj"))
        self.pushButton_cancel.setText(_translate("Ui_Dialog", "Porzuć"))
