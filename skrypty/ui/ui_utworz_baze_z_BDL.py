# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(560, 538)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_folder = QtWidgets.QLabel(Dialog)
        self.label_folder.setGeometry(QtCore.QRect(20, 16, 480, 16))
        self.label_folder.setFont(font)
        self.label_folder.setObjectName("label_folder")

        self.lineEdit_folder = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_folder.setGeometry(QtCore.QRect(20, 36, 440, 22))
        self.lineEdit_folder.setFont(font)
        self.lineEdit_folder.setObjectName("lineEdit_folder")

        self.pushButton_folder = QtWidgets.QPushButton(Dialog)
        self.pushButton_folder.setGeometry(QtCore.QRect(465, 36, 75, 23))
        self.pushButton_folder.setFont(font)
        self.pushButton_folder.setObjectName("pushButton_folder")

        self.label_baza = QtWidgets.QLabel(Dialog)
        self.label_baza.setGeometry(QtCore.QRect(20, 68, 480, 16))
        self.label_baza.setFont(font)
        self.label_baza.setObjectName("label_baza")

        self.lineEdit_baza = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_baza.setGeometry(QtCore.QRect(20, 88, 440, 22))
        self.lineEdit_baza.setFont(font)
        self.lineEdit_baza.setObjectName("lineEdit_baza")

        self.pushButton_baza = QtWidgets.QPushButton(Dialog)
        self.pushButton_baza.setGeometry(QtCore.QRect(465, 88, 75, 23))
        self.pushButton_baza.setFont(font)
        self.pushButton_baza.setObjectName("pushButton_baza")

        self.label_obr = QtWidgets.QLabel(Dialog)
        self.label_obr.setGeometry(QtCore.QRect(20, 120, 480, 16))
        self.label_obr.setFont(font)
        self.label_obr.setObjectName("label_obr")

        self.lineEdit_obr = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_obr.setGeometry(QtCore.QRect(20, 140, 440, 22))
        self.lineEdit_obr.setFont(font)
        self.lineEdit_obr.setObjectName("lineEdit_obr")

        self.pushButton_obr = QtWidgets.QPushButton(Dialog)
        self.pushButton_obr.setGeometry(QtCore.QRect(465, 140, 75, 23))
        self.pushButton_obr.setFont(font)
        self.pushButton_obr.setObjectName("pushButton_obr")

        self.label_wlasnosc = QtWidgets.QLabel(Dialog)
        self.label_wlasnosc.setGeometry(QtCore.QRect(20, 172, 400, 16))
        self.label_wlasnosc.setFont(font)
        self.label_wlasnosc.setObjectName("label_wlasnosc")

        self.listWidget_wlasnosc = QtWidgets.QListWidget(Dialog)
        self.listWidget_wlasnosc.setGeometry(QtCore.QRect(20, 192, 520, 110))
        self.listWidget_wlasnosc.setFont(font)
        self.listWidget_wlasnosc.setObjectName("listWidget_wlasnosc")

        self.label_obreb = QtWidgets.QLabel(Dialog)
        self.label_obreb.setGeometry(QtCore.QRect(20, 312, 400, 16))
        self.label_obreb.setFont(font)
        self.label_obreb.setObjectName("label_obreb")

        self.listWidget_obreb = QtWidgets.QListWidget(Dialog)
        self.listWidget_obreb.setGeometry(QtCore.QRect(20, 332, 520, 110))
        self.listWidget_obreb.setFont(font)
        self.listWidget_obreb.setObjectName("listWidget_obreb")

        self.checkBox_utworz_shp = QtWidgets.QCheckBox(Dialog)
        self.checkBox_utworz_shp.setGeometry(QtCore.QRect(20, 452, 520, 22))
        self.checkBox_utworz_shp.setFont(font)
        self.checkBox_utworz_shp.setChecked(True)
        self.checkBox_utworz_shp.setObjectName("checkBox_utworz_shp")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 484, 250, 34))
        self.pushButton_ok.setEnabled(False)
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(290, 484, 250, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Utwórz bazę z BDL"))
        self.label_folder.setText(_translate(
            "Dialog", "Folder z danymi BDL (wynik \"Ściągnij dane z BDL\"):"))
        self.pushButton_folder.setText(_translate("Dialog", "Wybierz"))
        self.label_baza.setText(_translate(
            "Dialog", "Baza docelowa (czysta, .mdb):"))
        self.pushButton_baza.setText(_translate("Dialog", "Wybierz"))
        self.label_obr.setText(_translate(
            "Dialog", "Warstwa OBR (przetworzona MUNICIP/COMMUNITY albo "
            "surowa PZGiK/EGiB/PRG):"))
        self.pushButton_obr.setText(_translate("Dialog", "Wybierz"))
        self.label_wlasnosc.setText(_translate(
            "Dialog", "Własność (owner_cat_) - do dopisania:"))
        self.label_obreb.setText(_translate(
            "Dialog",
            "Obręb - do dopisania (domyślnie zaznaczone tylko te z warstwy OBR):"))
        self.checkBox_utworz_shp.setText(_translate(
            "Dialog", "Utwórz SHP z wybranych (wybrane_BDL.shp)"))
        self.pushButton_ok.setText(_translate("Dialog", "Utwórz bazę"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
