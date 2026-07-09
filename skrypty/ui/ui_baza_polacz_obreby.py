# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(760, 560)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_naglowek = QtWidgets.QLabel(Dialog)
        self.label_naglowek.setGeometry(QtCore.QRect(20, 12, 720, 20))
        self.label_naglowek.setFont(font)
        self.label_naglowek.setObjectName("label_naglowek")

        self.label_bazy = QtWidgets.QLabel(Dialog)
        self.label_bazy.setGeometry(QtCore.QRect(20, 40, 220, 16))
        self.label_bazy.setFont(font)
        self.label_bazy.setObjectName("label_bazy")

        self.listWidget_bazy = QtWidgets.QListWidget(Dialog)
        self.listWidget_bazy.setGeometry(QtCore.QRect(20, 60, 220, 420))
        self.listWidget_bazy.setFont(font)
        self.listWidget_bazy.setObjectName("listWidget_bazy")

        self.label_obreby = QtWidgets.QLabel(Dialog)
        self.label_obreby.setGeometry(QtCore.QRect(260, 40, 480, 16))
        self.label_obreby.setFont(font)
        self.label_obreby.setObjectName("label_obreby")

        self.listWidget_obreby = QtWidgets.QListWidget(Dialog)
        self.listWidget_obreby.setGeometry(QtCore.QRect(260, 60, 480, 380))
        self.listWidget_obreby.setFont(font)
        self.listWidget_obreby.setObjectName("listWidget_obreby")

        self.pushButton_zaznacz_wszystkie = QtWidgets.QPushButton(Dialog)
        self.pushButton_zaznacz_wszystkie.setGeometry(QtCore.QRect(260, 446, 230, 28))
        self.pushButton_zaznacz_wszystkie.setFont(font)
        self.pushButton_zaznacz_wszystkie.setObjectName("pushButton_zaznacz_wszystkie")

        self.pushButton_odznacz_wszystkie = QtWidgets.QPushButton(Dialog)
        self.pushButton_odznacz_wszystkie.setGeometry(QtCore.QRect(510, 446, 230, 28))
        self.pushButton_odznacz_wszystkie.setFont(font)
        self.pushButton_odznacz_wszystkie.setObjectName("pushButton_odznacz_wszystkie")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 500, 360, 34))
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(390, 500, 350, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Połącz bazy TPU — wybór obrębów"))
        self.label_naglowek.setText(_translate(
            "Dialog", "Wybierz, które obręby skopiować z każdej bazy (domyślnie wszystkie):"))
        self.label_bazy.setText(_translate("Dialog", "Bazy:"))
        self.label_obreby.setText(_translate("Dialog", "Obręby wybranej bazy:"))
        self.pushButton_zaznacz_wszystkie.setText(_translate("Dialog", "Zaznacz wszystkie"))
        self.pushButton_odznacz_wszystkie.setText(_translate("Dialog", "Odznacz wszystkie"))
        self.pushButton_ok.setText(_translate("Dialog", "Dalej"))
        self.pushButton_cancel.setText(_translate("Dialog", "Anuluj"))
