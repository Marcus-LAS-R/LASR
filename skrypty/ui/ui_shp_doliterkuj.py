# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(560, 230)
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

        self.checkBox_oddz_reczny = QtWidgets.QCheckBox(Dialog)
        self.checkBox_oddz_reczny.setGeometry(QtCore.QRect(20, 68, 220, 22))
        self.checkBox_oddz_reczny.setFont(font)
        self.checkBox_oddz_reczny.setChecked(False)
        self.checkBox_oddz_reczny.setObjectName("checkBox_oddz_reczny")

        self.lineEdit_oddz_reczny = QtWidgets.QLineEdit(Dialog)
        self.lineEdit_oddz_reczny.setGeometry(QtCore.QRect(250, 68, 100, 22))
        self.lineEdit_oddz_reczny.setFont(font)
        self.lineEdit_oddz_reczny.setEnabled(False)
        self.lineEdit_oddz_reczny.setObjectName("lineEdit_oddz_reczny")

        self.checkBox_od = QtWidgets.QCheckBox(Dialog)
        self.checkBox_od.setGeometry(QtCore.QRect(20, 100, 520, 22))
        self.checkBox_od.setFont(font)
        self.checkBox_od.setChecked(False)
        self.checkBox_od.setObjectName("checkBox_od")

        self.tableWidget_oddzialy = QtWidgets.QTableWidget(Dialog)
        self.tableWidget_oddzialy.setGeometry(QtCore.QRect(20, 128, 520, 220))
        self.tableWidget_oddzialy.setFont(font)
        self.tableWidget_oddzialy.setObjectName("tableWidget_oddzialy")
        self.tableWidget_oddzialy.setColumnCount(5)
        self.tableWidget_oddzialy.setRowCount(0)
        self.tableWidget_oddzialy.setHorizontalHeaderLabels(
            ["Gmina", "Obręb", "Oddział", "Do doliterowania", "Litera startowa"])
        self.tableWidget_oddzialy.verticalHeader().setVisible(False)
        self.tableWidget_oddzialy.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.Stretch)
        self.tableWidget_oddzialy.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.Stretch)
        self.tableWidget_oddzialy.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.Stretch)
        self.tableWidget_oddzialy.horizontalHeader().setSectionResizeMode(
            3, QtWidgets.QHeaderView.Fixed)
        self.tableWidget_oddzialy.setColumnWidth(3, 110)
        self.tableWidget_oddzialy.horizontalHeader().setSectionResizeMode(
            4, QtWidgets.QHeaderView.Fixed)
        self.tableWidget_oddzialy.setColumnWidth(4, 110)
        self.tableWidget_oddzialy.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget_oddzialy.setVisible(False)

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 176, 250, 34))
        self.pushButton_ok.setEnabled(False)
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(290, 176, 250, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Doliterkuj wydzielenia - opcje"))
        self.label_warstwa.setText(_translate("Dialog", "Warstwa wydzieleń:"))
        self.pushButton_warstwa.setText(_translate("Dialog", "Wybierz"))
        self.checkBox_oddz_reczny.setText(_translate(
            "Dialog", "Wpisz oddział ręcznie:"))
        self.checkBox_od.setText(_translate(
            "Dialog",
            "Doliterkuj od... (osobno dla każdego oddziału)"))
        self.pushButton_ok.setText(_translate("Dialog", "Wykonaj"))
        self.pushButton_cancel.setText(_translate("Dialog", "Porzuć"))
