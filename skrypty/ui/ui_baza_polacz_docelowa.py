# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(520, 230)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_naglowek = QtWidgets.QLabel(Dialog)
        self.label_naglowek.setGeometry(QtCore.QRect(20, 12, 480, 20))
        self.label_naglowek.setFont(font)
        self.label_naglowek.setObjectName("label_naglowek")

        self.label_info = QtWidgets.QLabel(Dialog)
        self.label_info.setGeometry(QtCore.QRect(20, 40, 480, 40))
        self.label_info.setFont(font)
        self.label_info.setWordWrap(True)
        self.label_info.setObjectName("label_info")

        self.checkBox_wskaz = QtWidgets.QCheckBox(Dialog)
        self.checkBox_wskaz.setGeometry(QtCore.QRect(20, 90, 480, 24))
        self.checkBox_wskaz.setFont(font)
        self.checkBox_wskaz.setObjectName("checkBox_wskaz")

        self.lineEdit_baza = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(20, 122, 380, 26))
        self.lineEdit_baza.setFont(font)
        self.lineEdit_baza.setReadOnly(True)
        self.lineEdit_baza.setEnabled(False)
        self.lineEdit_baza.setObjectName("lineEdit_baza")

        self.pushButton_przegladaj = QtWidgets.QPushButton(Dialog)
        self.pushButton_przegladaj.setGeometry(QtCore.QRect(410, 122, 90, 26))
        self.pushButton_przegladaj.setFont(font)
        self.pushButton_przegladaj.setEnabled(False)
        self.pushButton_przegladaj.setObjectName("pushButton_przegladaj")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 176, 300, 34))
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(340, 176, 160, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Połącz bazy TPU — baza docelowa"))
        self.label_naglowek.setText(_translate(
            "Dialog", "Wybierz bazę docelową (do której zostaną dopisane pozostałe):"))
        self.label_info.setText(_translate("Dialog", ""))
        self.checkBox_wskaz.setText(_translate(
            "Dialog", "Wskaż bazę docelową ręcznie (np. pustą bazę-szablon)"))
        self.pushButton_przegladaj.setText(_translate("Dialog", "Przeglądaj..."))
        self.pushButton_ok.setText(_translate("Dialog", "Dalej"))
        self.pushButton_cancel.setText(_translate("Dialog", "Anuluj"))
