# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_raport_wyles.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(551, 518)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(10, 20, 131, 18))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.groupBox = QtWidgets.QGroupBox(Dialog)
        self.groupBox.setGeometry(QtCore.QRect(10, 60, 531, 101))
        self.groupBox.setObjectName("groupBox")
        self.radioButton_all = QtWidgets.QRadioButton(self.groupBox)
        self.radioButton_all.setGeometry(QtCore.QRect(20, 30, 401, 22))
        self.radioButton_all.setChecked(True)
        self.radioButton_all.setObjectName("radioButton_all")
        self.radioButton_wyb = QtWidgets.QRadioButton(self.groupBox)
        self.radioButton_wyb.setGeometry(QtCore.QRect(20, 60, 401, 22))
        self.radioButton_wyb.setObjectName("radioButton_wyb")
        self.lineEdit = QtWidgets.QLineEdit(Dialog)
        self.lineEdit.setGeometry(QtCore.QRect(100, 10, 421, 41))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        self.lineEdit.setFont(font)
        self.lineEdit.setObjectName("lineEdit")
        self.textEdit = QtWidgets.QTextEdit(Dialog)
        self.textEdit.setEnabled(False)
        self.textEdit.setGeometry(QtCore.QRect(10, 170, 531, 281))
        font = QtGui.QFont()
        font.setFamily("Arial")
        self.textEdit.setFont(font)
        self.textEdit.setObjectName("textEdit")
        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(30, 460, 341, 51))
        self.pushButton_ok.setObjectName("pushButton_ok")
        self.pushButton_porzuc = QtWidgets.QPushButton(Dialog)
        self.pushButton_porzuc.setGeometry(QtCore.QRect(420, 470, 88, 34))
        self.pushButton_porzuc.setObjectName("pushButton_porzuc")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label.setText(_translate("Dialog", "Nazwa gminy:"))
        self.groupBox.setTitle(_translate("Dialog", "Tryb generowania kart"))
        self.radioButton_all.setText(_translate("Dialog", "Wszystkie poligony z warstwy wylesień"))
        self.radioButton_wyb.setText(_translate("Dialog", "Tylko zaznaczone poligony z warstwy wylesień"))
        self.lineEdit.setText(_translate("Dialog", "Przykładowa nazwa gminy"))
        self.textEdit.setHtml(_translate("Dialog", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Arial\'; font-size:10pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">Wymagania generowania kart wylesień na działkach:</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">-Skrypt powinien być uruchamiany przy otwartym projekcie do tego przeznaczonym</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">-warstwa inne_wyl powinna zawierać wybrane poligony INNE WYL z warstwy WYDZ_POL przecięte z warstwą DZKAT</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">-warstwa pkt_gran powinny zawierać wszystkie pkt graniczne, które mają być pokazywane na poszczególnych kartach</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">- warstwa gr działki ew. powinna zawierać ewidencję (proszę zwrócić uwagę, na labelki, czy istnieją odpowiednie pola z których poligony będą labelkowane)</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">- warstwa KLU_AFT powinna zawierać kolumnę KLU z połączonymi danymi z AU i SQ</span></p></body></html>"))
        self.pushButton_ok.setText(_translate("Dialog", "Generuj"))
        self.pushButton_porzuc.setText(_translate("Dialog", "Porzuć"))


