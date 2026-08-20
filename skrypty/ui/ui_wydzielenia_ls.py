# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(560, 340)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        font_male = QtGui.QFont()
        font_male.setFamily("Arial")
        font_male.setPointSize(8)
        font_male.setItalic(True)

        self.label_naglowek = QtWidgets.QLabel(Dialog)
        self.label_naglowek.setGeometry(QtCore.QRect(20, 12, 520, 20))
        self.label_naglowek.setFont(font)
        self.label_naglowek.setObjectName("label_naglowek")

        # --- warstwa wydzielen ---
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(20, 40, 300, 18))
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")

        self.lineEdit_wydzielenia = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_wydzielenia.setGeometry(QtCore.QRect(20, 58, 400, 26))
        self.lineEdit_wydzielenia.setFont(font)
        self.lineEdit_wydzielenia.setObjectName("lineEdit_wydzielenia")

        self.pushButton_wydzielenia = QtWidgets.QPushButton(Dialog)
        self.pushButton_wydzielenia.setGeometry(QtCore.QRect(430, 58, 90, 26))
        self.pushButton_wydzielenia.setFont(font)
        self.pushButton_wydzielenia.setObjectName("pushButton_wydzielenia")

        self.label_wydzielenia = QtWidgets.QLabel(Dialog)
        self.label_wydzielenia.setGeometry(QtCore.QRect(20, 86, 500, 16))
        self.label_wydzielenia.setFont(font_male)
        self.label_wydzielenia.setObjectName("label_wydzielenia")

        # --- warstwa DZKAT ---
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setGeometry(QtCore.QRect(20, 112, 300, 18))
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")

        self.lineEdit_dzkat = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_dzkat.setGeometry(QtCore.QRect(20, 130, 400, 26))
        self.lineEdit_dzkat.setFont(font)
        self.lineEdit_dzkat.setObjectName("lineEdit_dzkat")

        self.pushButton_dzkat = QtWidgets.QPushButton(Dialog)
        self.pushButton_dzkat.setGeometry(QtCore.QRect(430, 130, 90, 26))
        self.pushButton_dzkat.setFont(font)
        self.pushButton_dzkat.setObjectName("pushButton_dzkat")

        self.label_dzkat = QtWidgets.QLabel(Dialog)
        self.label_dzkat.setGeometry(QtCore.QRect(20, 158, 500, 16))
        self.label_dzkat.setFont(font_male)
        self.label_dzkat.setObjectName("label_dzkat")

        # --- katalog z bazami ---
        self.label_4 = QtWidgets.QLabel(Dialog)
        self.label_4.setGeometry(QtCore.QRect(20, 184, 300, 18))
        self.label_4.setFont(font)
        self.label_4.setObjectName("label_4")

        self.lineEdit_bazy = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_bazy.setGeometry(QtCore.QRect(20, 202, 400, 26))
        self.lineEdit_bazy.setFont(font)
        self.lineEdit_bazy.setObjectName("lineEdit_bazy")

        self.pushButton_bazy = QtWidgets.QPushButton(Dialog)
        self.pushButton_bazy.setGeometry(QtCore.QRect(430, 202, 90, 26))
        self.pushButton_bazy.setFont(font)
        self.pushButton_bazy.setObjectName("pushButton_bazy")

        self.label_bazy = QtWidgets.QLabel(Dialog)
        self.label_bazy.setGeometry(QtCore.QRect(20, 230, 500, 16))
        self.label_bazy.setFont(font_male)
        self.label_bazy.setObjectName("label_bazy")

        # --- wlasnosc ---
        self.label_5 = QtWidgets.QLabel(Dialog)
        self.label_5.setGeometry(QtCore.QRect(20, 258, 90, 24))
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")

        self.comboBox_wlas = QtWidgets.QComboBox(Dialog)
        self.comboBox_wlas.setGeometry(QtCore.QRect(110, 256, 260, 26))
        self.comboBox_wlas.setFont(font)
        self.comboBox_wlas.setObjectName("comboBox_wlas")
        self.comboBox_wlas.addItem("")
        self.comboBox_wlas.addItem("")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 292, 300, 34))
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(340, 292, 180, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        self.pushButton_cancel.clicked.connect(Dialog.close)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Przygotuj Lsy z wydzieleń"))
        self.label_naglowek.setText(_translate(
            "Dialog", "Wskaż dane wejściowe:"))
        self.label_2.setText(_translate("Dialog", "Warstwa wydzieleń (kontur):"))
        self.pushButton_wydzielenia.setText(_translate("Dialog", "Wybierz"))
        self.label_3.setText(_translate("Dialog", "Warstwa DZKAT:"))
        self.pushButton_dzkat.setText(_translate("Dialog", "Wybierz"))
        self.label_4.setText(_translate("Dialog", "Katalog z bazami:"))
        self.pushButton_bazy.setText(_translate("Dialog", "Wybierz"))
        self.label_5.setText(_translate("Dialog", "Własność:"))
        self.comboBox_wlas.setItemText(0, _translate("Dialog", "OF i współwłasności"))
        self.comboBox_wlas.setItemText(1, _translate("Dialog", "Wszystkie"))
        self.pushButton_ok.setText(_translate("Dialog", "OK"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
