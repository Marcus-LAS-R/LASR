# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setFixedSize(520, 210)

        font = QtGui.QFont()
        font.setFamily("Arial")

        font_it = QtGui.QFont()
        font_it.setFamily("Arial")
        font_it.setItalic(True)

        # --- tryb wsadowy checkbox ---
        self.checkBox_wsadowo = QtWidgets.QCheckBox(Dialog)
        self.checkBox_wsadowo.setGeometry(QtCore.QRect(20, 15, 200, 20))
        self.checkBox_wsadowo.setFont(font)
        self.checkBox_wsadowo.setObjectName("checkBox_wsadowo")

        # --- SINGLE MODE widgets ---
        self.label_folder = QtWidgets.QLabel(Dialog)
        self.label_folder.setGeometry(QtCore.QRect(20, 52, 120, 16))
        self.label_folder.setFont(font)
        self.label_folder.setObjectName("label_folder")

        self.lineEdit_folder = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_folder.setGeometry(QtCore.QRect(145, 50, 280, 22))
        self.lineEdit_folder.setFont(font)
        self.lineEdit_folder.setObjectName("lineEdit_folder")

        self.pushButton_folder = QtWidgets.QPushButton(Dialog)
        self.pushButton_folder.setGeometry(QtCore.QRect(435, 50, 75, 23))
        self.pushButton_folder.setFont(font)
        self.pushButton_folder.setObjectName("pushButton_folder")

        self.label_baza = QtWidgets.QLabel(Dialog)
        self.label_baza.setGeometry(QtCore.QRect(20, 90, 120, 16))
        self.label_baza.setFont(font)
        self.label_baza.setObjectName("label_baza")

        self.lineEdit_baza = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(145, 88, 280, 22))
        self.lineEdit_baza.setFont(font)
        self.lineEdit_baza.setObjectName("lineEdit_baza")

        self.pushButton_baza = QtWidgets.QPushButton(Dialog)
        self.pushButton_baza.setGeometry(QtCore.QRect(435, 88, 75, 23))
        self.pushButton_baza.setFont(font)
        self.pushButton_baza.setObjectName("pushButton_baza")

        self.label_wyj_opis = QtWidgets.QLabel(Dialog)
        self.label_wyj_opis.setGeometry(QtCore.QRect(20, 128, 120, 16))
        self.label_wyj_opis.setFont(font)
        self.label_wyj_opis.setObjectName("label_wyj_opis")

        self.label_wyj = QtWidgets.QLabel(Dialog)
        self.label_wyj.setGeometry(QtCore.QRect(145, 128, 355, 16))
        self.label_wyj.setFont(font_it)
        self.label_wyj.setText("")
        self.label_wyj.setObjectName("label_wyj")

        # --- BATCH MODE widgets ---
        self.label_powiat = QtWidgets.QLabel(Dialog)
        self.label_powiat.setGeometry(QtCore.QRect(20, 52, 120, 16))
        self.label_powiat.setFont(font)
        self.label_powiat.setObjectName("label_powiat")
        self.label_powiat.setVisible(False)

        self.lineEdit_powiat = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_powiat.setGeometry(QtCore.QRect(145, 50, 280, 22))
        self.lineEdit_powiat.setFont(font)
        self.lineEdit_powiat.setObjectName("lineEdit_powiat")
        self.lineEdit_powiat.setVisible(False)

        self.pushButton_powiat = QtWidgets.QPushButton(Dialog)
        self.pushButton_powiat.setGeometry(QtCore.QRect(435, 50, 75, 23))
        self.pushButton_powiat.setFont(font)
        self.pushButton_powiat.setObjectName("pushButton_powiat")
        self.pushButton_powiat.setVisible(False)

        self.listWidget_gminy = QtWidgets.QListWidget(Dialog)
        self.listWidget_gminy.setGeometry(QtCore.QRect(20, 82, 490, 240))
        self.listWidget_gminy.setFont(font)
        self.listWidget_gminy.setObjectName("listWidget_gminy")
        self.listWidget_gminy.setVisible(False)

        # --- buttons (always visible) ---
        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(100, 168, 201, 31))
        self.pushButton_ok.setEnabled(False)
        self.pushButton_ok.setFont(font)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(360, 168, 75, 31))
        self.pushButton_cancel.setFont(font)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        self.pushButton_ok.clicked.connect(Dialog.accept)
        self.pushButton_cancel.clicked.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Przygotuj warstwy dla taksatora"))
        self.checkBox_wsadowo.setText(_translate("Dialog", "Wiele gmin"))
        self.label_folder.setText(_translate("Dialog", "Folder projektu:"))
        self.label_baza.setText(_translate("Dialog", "Baza danych:"))
        self.label_wyj_opis.setText(_translate("Dialog", "Folder wynikowy:"))
        self.label_powiat.setText(_translate("Dialog", "Folder powiatu:"))
        self.pushButton_folder.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_baza.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_powiat.setText(_translate("Dialog", "Wybierz"))
        self.pushButton_ok.setText(_translate("Dialog", "Uruchom"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
