from sprawdz_ls import SprawdzMikro
from qgis.core import *  # noqa
from PyQt5.QtWidgets import *  # noqa
from PyQt5.QtCore import *  # noqa
from PyQt5.QtGui import *  # noqa


def mikro_data():
    klu = []

    sl_ops = {
        1: ['Ls', 'V', ''],
        2: ['Ls', 'VI', ''],
        3: ['Ls', 'I', 'Brak w bazie, '],
        4: ['Ps', 'V', 'Brak w bazie, '],
        5: ['Ls', 'VI', ''],
        6: ['Ls', 'VI', ''],
        7: ['Ł', 'III', 'Brak w bazie, '],
        8: ['Ls', 'V', ''],
        9: ['Ls', 'V', ''],
        10: ['Ls', 'II', 'Brak w bazie, '],
        11: ['W', '', 'Brak w bazie, '],
    }

    sl_geom = {
        1: [[QgsPointXY(0, 0),
             QgsPointXY(0, 30),
             QgsPointXY(30, 30),
             QgsPointXY(30, 0),
             QgsPointXY(0, 0),
             ]],

        2: [[QgsPointXY(30, 0),
             QgsPointXY(30, 40),
             QgsPointXY(50, 40),
             QgsPointXY(50, 0),
             QgsPointXY(30, 0),
             ]],

        3: [[QgsPointXY(0, 50),
             QgsPointXY(20, 50),
             QgsPointXY(20, 49),
             QgsPointXY(0, 49),
             QgsPointXY(0, 50),
             ]],

        4: [[QgsPointXY(29, 30),
             QgsPointXY(29, 45),
             QgsPointXY(30, 45),
             QgsPointXY(30, 30),
             QgsPointXY(29, 30),
             ]],

        5: [[QgsPointXY(49, 40),
             QgsPointXY(49, 50),
             QgsPointXY(50, 50),
             QgsPointXY(50, 40),
             QgsPointXY(49, 40),
             ]],

        6: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(1, 10),
             QgsPointXY(1, 0),
             QgsPointXY(0, 0),
             ]],

        7: [[QgsPointXY(25, 0),
             QgsPointXY(25, 1),
             QgsPointXY(41, 1),
             QgsPointXY(41, 0),
             QgsPointXY(25, 0),
             ]],

        8: [[QgsPointXY(0, 30),
             QgsPointXY(0, 20),
             QgsPointXY(1, 20),
             QgsPointXY(1, 30),
             QgsPointXY(0, 30),
             ]],

        9: [[QgsPointXY(0, 20),
             QgsPointXY(0, 10),
             QgsPointXY(1, 10),
             QgsPointXY(1, 20),
             QgsPointXY(0, 20),
            ]],

        10: [[QgsPointXY(0, 49),
              QgsPointXY(10, 49),
              QgsPointXY(10, 48),
              QgsPointXY(0, 48),
              QgsPointXY(0, 49),
              ]],

        11: [[QgsPointXY(0, 40),
              QgsPointXY(2, 40),
              QgsPointXY(2, 38),
              QgsPointXY(0, 38),
              QgsPointXY(0, 40),
              ]],
    }

    fields = QgsFields()
    fields.append(QgsField('PARCELID', QVariant.String, len=30))
    fields.append(QgsField('AU', QVariant.String, len=10))
    fields.append(QgsField('SQ', QVariant.String, len=10))
    fields.append(QgsField('UWAGI', QVariant.String, len=50))

    for fid in range(1, 12):
        f = QgsFeature(fid)
        f.setFields(fields)

        f.setAttribute(f.fieldNameIndex('PARCELID'), '1')
        f.setAttribute(f.fieldNameIndex('AU'), sl_ops[fid][0])
        f.setAttribute(f.fieldNameIndex('SQ'), sl_ops[fid][1])
        f.setAttribute(f.fieldNameIndex('UWAGI'), sl_ops[fid][2])

        f.setGeometry(QgsGeometry().fromPolygonXY(sl_geom[fid]))

        klu.append(f)

    return klu


def pp(md):
    d = md
    s = SprawdzMikro(d)
    s.przetworz()

    return s
    # s.is_valid()
    # s.zbuduj_strukture()
