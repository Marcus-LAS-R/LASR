# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(660, 600)
        font = QtGui.QFont()
        font.setFamily("Arial")
        Dialog.setFont(font)

        self.label_naglowek = QtWidgets.QLabel(Dialog)
        self.label_naglowek.setGeometry(QtCore.QRect(20, 12, 620, 20))
        self.label_naglowek.setFont(font)
        self.label_naglowek.setObjectName("label_naglowek")

        # --- Grupa 2: ewidencyjna ---
        self.groupBox_grupa2 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_grupa2.setGeometry(QtCore.QRect(20, 40, 620, 150))
        self.groupBox_grupa2.setFont(font)
        self.groupBox_grupa2.setCheckable(True)
        self.groupBox_grupa2.setChecked(True)
        self.groupBox_grupa2.setObjectName("groupBox_grupa2")

        self.checkBox_f_parcel = QtWidgets.QCheckBox(self.groupBox_grupa2)
        self.checkBox_f_parcel.setGeometry(QtCore.QRect(20, 28, 580, 22))
        self.checkBox_f_parcel.setFont(font)
        self.checkBox_f_parcel.setChecked(True)
        self.checkBox_f_parcel.setObjectName("checkBox_f_parcel")

        self.checkBox_v_address = QtWidgets.QCheckBox(self.groupBox_grupa2)
        self.checkBox_v_address.setGeometry(QtCore.QRect(20, 54, 580, 22))
        self.checkBox_v_address.setFont(font)
        self.checkBox_v_address.setChecked(True)
        self.checkBox_v_address.setObjectName("checkBox_v_address")

        self.checkBox_f_parcel_land_use = QtWidgets.QCheckBox(self.groupBox_grupa2)
        self.checkBox_f_parcel_land_use.setGeometry(QtCore.QRect(20, 80, 580, 22))
        self.checkBox_f_parcel_land_use.setFont(font)
        self.checkBox_f_parcel_land_use.setChecked(True)
        self.checkBox_f_parcel_land_use.setObjectName("checkBox_f_parcel_land_use")

        self.checkBox_v_parcel_participation = QtWidgets.QCheckBox(self.groupBox_grupa2)
        self.checkBox_v_parcel_participation.setGeometry(QtCore.QRect(20, 106, 580, 22))
        self.checkBox_v_parcel_participation.setFont(font)
        self.checkBox_v_parcel_participation.setChecked(True)
        self.checkBox_v_parcel_participation.setObjectName("checkBox_v_parcel_participation")

        # --- Grupa 3: lesna (2 kolumny x 8) ---
        self.groupBox_grupa3 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_grupa3.setGeometry(QtCore.QRect(20, 200, 620, 260))
        self.groupBox_grupa3.setFont(font)
        self.groupBox_grupa3.setCheckable(True)
        self.groupBox_grupa3.setChecked(True)
        self.groupBox_grupa3.setObjectName("groupBox_grupa3")

        kol1_x, kol2_x = 20, 320
        kol_szer = 280
        wiersz_h = 26
        start_y = 28

        self.checkBox_f_arodes = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arodes.setGeometry(QtCore.QRect(kol1_x, start_y + 0 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arodes.setFont(font)
        self.checkBox_f_arodes.setChecked(True)
        self.checkBox_f_arodes.setObjectName("checkBox_f_arodes")

        self.checkBox_f_subarea = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_subarea.setGeometry(QtCore.QRect(kol1_x, start_y + 1 * wiersz_h, kol_szer, 22))
        self.checkBox_f_subarea.setFont(font)
        self.checkBox_f_subarea.setChecked(True)
        self.checkBox_f_subarea.setObjectName("checkBox_f_subarea")

        self.checkBox_f_arod_storey = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_storey.setGeometry(QtCore.QRect(kol1_x, start_y + 2 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_storey.setFont(font)
        self.checkBox_f_arod_storey.setChecked(True)
        self.checkBox_f_arod_storey.setObjectName("checkBox_f_arod_storey")

        self.checkBox_f_storey_species = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_storey_species.setGeometry(QtCore.QRect(kol1_x, start_y + 3 * wiersz_h, kol_szer, 22))
        self.checkBox_f_storey_species.setFont(font)
        self.checkBox_f_storey_species.setChecked(True)
        self.checkBox_f_storey_species.setObjectName("checkBox_f_storey_species")

        self.checkBox_f_arod_stand_pec = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_stand_pec.setGeometry(QtCore.QRect(kol1_x, start_y + 4 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_stand_pec.setFont(font)
        self.checkBox_f_arod_stand_pec.setChecked(True)
        self.checkBox_f_arod_stand_pec.setObjectName("checkBox_f_arod_stand_pec")

        self.checkBox_f_arod_goal = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_goal.setGeometry(QtCore.QRect(kol1_x, start_y + 5 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_goal.setFont(font)
        self.checkBox_f_arod_goal.setChecked(True)
        self.checkBox_f_arod_goal.setObjectName("checkBox_f_arod_goal")

        self.checkBox_f_arod_spec_area = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_spec_area.setGeometry(QtCore.QRect(kol1_x, start_y + 6 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_spec_area.setFont(font)
        self.checkBox_f_arod_spec_area.setChecked(True)
        self.checkBox_f_arod_spec_area.setObjectName("checkBox_f_arod_spec_area")

        self.checkBox_f_species_sparea = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_species_sparea.setGeometry(QtCore.QRect(kol1_x, start_y + 7 * wiersz_h, kol_szer, 22))
        self.checkBox_f_species_sparea.setFont(font)
        self.checkBox_f_species_sparea.setChecked(True)
        self.checkBox_f_species_sparea.setObjectName("checkBox_f_species_sparea")

        self.checkBox_f_arod_phenomena = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_phenomena.setGeometry(QtCore.QRect(kol2_x, start_y + 0 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_phenomena.setFont(font)
        self.checkBox_f_arod_phenomena.setChecked(True)
        self.checkBox_f_arod_phenomena.setObjectName("checkBox_f_arod_phenomena")

        self.checkBox_f_arod_cue = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_cue.setGeometry(QtCore.QRect(kol2_x, start_y + 1 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_cue.setFont(font)
        self.checkBox_f_arod_cue.setChecked(True)
        self.checkBox_f_arod_cue.setObjectName("checkBox_f_arod_cue")

        self.checkBox_f_arod_category = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_category.setGeometry(QtCore.QRect(kol2_x, start_y + 2 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_category.setFont(font)
        self.checkBox_f_arod_category.setChecked(True)
        self.checkBox_f_arod_category.setObjectName("checkBox_f_arod_category")

        self.checkBox_f_arod_soil_spec = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_soil_spec.setGeometry(QtCore.QRect(kol2_x, start_y + 3 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_soil_spec.setFont(font)
        self.checkBox_f_arod_soil_spec.setChecked(True)
        self.checkBox_f_arod_soil_spec.setObjectName("checkBox_f_arod_soil_spec")

        self.checkBox_f_compartment = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_compartment.setGeometry(QtCore.QRect(kol2_x, start_y + 4 * wiersz_h, kol_szer, 22))
        self.checkBox_f_compartment.setFont(font)
        self.checkBox_f_compartment.setChecked(True)
        self.checkBox_f_compartment.setObjectName("checkBox_f_compartment")

        self.checkBox_f_set = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_set.setGeometry(QtCore.QRect(kol2_x, start_y + 5 * wiersz_h, kol_szer, 22))
        self.checkBox_f_set.setFont(font)
        self.checkBox_f_set.setChecked(True)
        self.checkBox_f_set.setObjectName("checkBox_f_set")

        self.checkBox_f_arod_damage = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_damage.setGeometry(QtCore.QRect(kol2_x, start_y + 6 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_damage.setFont(font)
        self.checkBox_f_arod_damage.setChecked(True)
        self.checkBox_f_arod_damage.setObjectName("checkBox_f_arod_damage")

        self.checkBox_f_arod_land_use = QtWidgets.QCheckBox(self.groupBox_grupa3)
        self.checkBox_f_arod_land_use.setGeometry(QtCore.QRect(kol2_x, start_y + 7 * wiersz_h, kol_szer, 22))
        self.checkBox_f_arod_land_use.setFont(font)
        self.checkBox_f_arod_land_use.setChecked(True)
        self.checkBox_f_arod_land_use.setObjectName("checkBox_f_arod_land_use")

        self.label_community = QtWidgets.QLabel(Dialog)
        self.label_community.setGeometry(QtCore.QRect(20, 470, 620, 20))
        self.label_community.setFont(font)
        self.label_community.setObjectName("label_community")

        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setGeometry(QtCore.QRect(20, 510, 300, 34))
        font_ok = QtGui.QFont()
        font_ok.setFamily("Arial")
        font_ok.setPointSize(11)
        font_ok.setBold(True)
        font_ok.setWeight(75)
        self.pushButton_ok.setFont(font_ok)
        self.pushButton_ok.setObjectName("pushButton_ok")

        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setGeometry(QtCore.QRect(340, 510, 300, 34))
        font_cancel = QtGui.QFont()
        font_cancel.setFamily("Arial")
        font_cancel.setPointSize(8)
        self.pushButton_cancel.setFont(font_cancel)
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Połącz bazy TPU — wybór zakresu"))
        self.label_naglowek.setText(_translate(
            "Dialog", "Wybierz grupy i tabele do skopiowania (domyślnie wszystko włączone):"))

        self.groupBox_grupa2.setTitle(_translate("Dialog", "Grupa ewidencyjna"))
        self.checkBox_f_parcel.setText(_translate(
            "Dialog", "F_PARCEL — działki ewidencyjne"))
        self.checkBox_v_address.setText(_translate(
            "Dialog", "V_ADDRESS — właściciele/adresaci"))
        self.checkBox_f_parcel_land_use.setText(_translate(
            "Dialog", "F_PARCEL_LAND_USE — użytki działek (wymaga F_PARCEL)"))
        self.checkBox_v_parcel_participation.setText(_translate(
            "Dialog", "V_PARCEL_PARTICIPATION — udziały właścicieli "
            "(wymaga F_PARCEL i V_ADDRESS)"))

        self.groupBox_grupa3.setTitle(_translate("Dialog", "Grupa leśna"))
        self.checkBox_f_arodes.setText(_translate(
            "Dialog", "F_ARODES — wydzielenia (szkielet)"))
        self.checkBox_f_subarea.setText(_translate("Dialog", "F_SUBAREA"))
        self.checkBox_f_arod_storey.setText(_translate("Dialog", "F_AROD_STOREY"))
        self.checkBox_f_storey_species.setText(_translate("Dialog", "F_STOREY_SPECIES"))
        self.checkBox_f_arod_stand_pec.setText(_translate("Dialog", "F_AROD_STAND_PEC"))
        self.checkBox_f_arod_goal.setText(_translate("Dialog", "F_AROD_GOAL"))
        self.checkBox_f_arod_spec_area.setText(_translate("Dialog", "F_AROD_SPEC_AREA"))
        self.checkBox_f_species_sparea.setText(_translate("Dialog", "F_SPECIES_SPAREA"))
        self.checkBox_f_arod_phenomena.setText(_translate("Dialog", "F_AROD_PHENOMENA"))
        self.checkBox_f_arod_cue.setText(_translate("Dialog", "F_AROD_CUE"))
        self.checkBox_f_arod_category.setText(_translate("Dialog", "F_AROD_CATEGORY"))
        self.checkBox_f_arod_soil_spec.setText(_translate("Dialog", "F_AROD_SOIL_SPEC"))
        self.checkBox_f_compartment.setText(_translate("Dialog", "F_COMPARTMENT"))
        self.checkBox_f_set.setText(_translate("Dialog", "F_SET"))
        self.checkBox_f_arod_damage.setText(_translate("Dialog", "F_AROD_DAMAGE"))
        self.checkBox_f_arod_land_use.setText(_translate(
            "Dialog", "F_AROD_LAND_USE (wymaga F_PARCEL)"))

        self.label_community.setText(_translate(
            "Dialog", "F_COMMUNITY (słownik miejscowości) jest kopiowana zawsze."))

        self.pushButton_ok.setText(_translate("Dialog", "Dalej"))
        self.pushButton_cancel.setText(_translate("Dialog", "Anuluj"))
