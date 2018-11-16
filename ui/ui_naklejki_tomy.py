# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_naklejki_tomy.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_DialogTomy(object):
    def setupUi(self, DialogTomy):
        DialogTomy.setObjectName("DialogTomy")
        DialogTomy.resize(637, 741)
        DialogTomy.setMinimumSize(QtCore.QSize(399, 741))
        DialogTomy.setMaximumSize(QtCore.QSize(1399, 1060))
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(DialogTomy)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.tableWidget = QtWidgets.QTableWidget(DialogTomy)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        self.tableWidget.setFont(font)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.verticalLayout.addWidget(self.tableWidget)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(DialogTomy)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.horizontalLayout.addWidget(self.buttonBox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(DialogTomy)
        self.buttonBox.accepted.connect(DialogTomy.accept)
        self.buttonBox.rejected.connect(DialogTomy.reject)
        QtCore.QMetaObject.connectSlotsByName(DialogTomy)

    def retranslateUi(self, DialogTomy):
        _translate = QtCore.QCoreApplication.translate
        DialogTomy.setWindowTitle(_translate("DialogTomy", "Ilość tomów w opracowaniach"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DialogTomy = QtWidgets.QDialog()
    ui = Ui_DialogTomy()
    ui.setupUi(DialogTomy)
    DialogTomy.show()
    sys.exit(app.exec_())

