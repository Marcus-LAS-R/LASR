# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(900, 620)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        layout = QtWidgets.QVBoxLayout(Dialog)

        self.label_naglowek = QtWidgets.QLabel(Dialog)
        self.label_naglowek.setFont(font)
        self.label_naglowek.setObjectName("label_naglowek")
        self.label_naglowek.setWordWrap(True)
        layout.addWidget(self.label_naglowek)

        # Kontener przewijany z blokami "nazwa bazy + lista obrębów",
        # ułożonymi w 2 niezależne, samodzielnie pionowo pakowane kolumny
        # (a nie sztywna siatka - przy blokach o bardzo różnej wysokości
        # siatka wymusza wysokość wiersza na najwyższym elemencie i marnuje
        # mnóstwo miejsca w krótszej kolumnie). Bloki dokładane dynamicznie
        # przez WyborObrebowDialog (liczba baz nie jest znana na etapie
        # budowy UI) metodą "dołóż do krótszej kolumny".
        self.scrollArea = QtWidgets.QScrollArea(Dialog)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")

        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        kolumny_layout = QtWidgets.QHBoxLayout(self.scrollAreaWidgetContents)

        self.layout_kolumna_lewa = QtWidgets.QVBoxLayout()
        self.layout_kolumna_prawa = QtWidgets.QVBoxLayout()
        kolumny_layout.addLayout(self.layout_kolumna_lewa, 1)
        kolumny_layout.addLayout(self.layout_kolumna_prawa, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        layout.addWidget(self.scrollArea, 1)

        przyciski_zaznacz = QtWidgets.QHBoxLayout()
        self.pushButton_zaznacz_wszystkie = QtWidgets.QPushButton(Dialog)
        self.pushButton_zaznacz_wszystkie.setFont(font)
        self.pushButton_zaznacz_wszystkie.setObjectName("pushButton_zaznacz_wszystkie")
        przyciski_zaznacz.addWidget(self.pushButton_zaznacz_wszystkie)

        self.pushButton_odznacz_wszystkie = QtWidgets.QPushButton(Dialog)
        self.pushButton_odznacz_wszystkie.setFont(font)
        self.pushButton_odznacz_wszystkie.setObjectName("pushButton_odznacz_wszystkie")
        przyciski_zaznacz.addWidget(self.pushButton_odznacz_wszystkie)
        layout.addLayout(przyciski_zaznacz)

        przyciski_ok = QtWidgets.QHBoxLayout()
        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")
        przyciski_ok.addWidget(self.pushButton_ok, 1)

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")
        przyciski_ok.addWidget(self.pushButton_cancel, 1)
        layout.addLayout(przyciski_ok)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Połącz bazy TPU — wybór obrębów"))
        self.label_naglowek.setText(_translate(
            "Dialog", "Wybierz, które obręby skopiować z każdej bazy (domyślnie wszystkie):"))
        self.pushButton_zaznacz_wszystkie.setText(_translate("Dialog", "Zaznacz wszystkie"))
        self.pushButton_odznacz_wszystkie.setText(_translate("Dialog", "Odznacz wszystkie"))
        self.pushButton_ok.setText(_translate("Dialog", "Dalej"))
        self.pushButton_cancel.setText(_translate("Dialog", "Anuluj"))
