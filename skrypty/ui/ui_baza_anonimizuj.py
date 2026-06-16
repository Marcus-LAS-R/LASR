# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Ui_Dialog):
        Ui_Dialog.setObjectName("Ui_Dialog")
        Ui_Dialog.resize(400, 110)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Ui_Dialog.setFont(font)

        self.checkBox_kwerendy = QtWidgets.QCheckBox(Ui_Dialog)
        self.checkBox_kwerendy.setGeometry(QtCore.QRect(20, 20, 360, 22))
        font_cb = QtGui.QFont()
        font_cb.setFamily("Arial")
        self.checkBox_kwerendy.setFont(font_cb)
        self.checkBox_kwerendy.setChecked(True)
        self.checkBox_kwerendy.setObjectName("checkBox_kwerendy")

        self.pushButton_ok = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 60, 170, 34))
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Ui_Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(210, 60, 170, 34))
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
        self.checkBox_kwerendy.setText(_translate("Ui_Dialog", "Usuń kwerendy z baz"))
        self.pushButton_ok.setText(_translate("Ui_Dialog", "Wykonaj"))
        self.pushButton_cancel.setText(_translate("Ui_Dialog", "Porzuć"))
