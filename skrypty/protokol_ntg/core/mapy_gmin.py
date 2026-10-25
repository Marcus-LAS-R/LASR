# -*- coding: utf-8 -*-
"""Mapy tematyczne gmin do prezentacji NTG (A4 poziomo): TSL, zabiegi,
formy ochrony przyrody.

Każda mapa to layout z atlasem po gminach (warstwa pokrycia NTG_G_GMIN,
jedna strona na gminę - filtr na pierwszy obiekt danego kodu, bo gminy
bywają zdublowane, i tylko gminy z obrębami w warstwie OBR). Kadr do
obrębów gminy obecnych w warstwie OBR (po "Przygotuj warstwy i bazę" -
tylko obręby z wydzieleniami) z małym marginesem, bez zaokrąglania skali
(zasięg jako wyrażenia - kadr_wyrazenia(); o skali mówi pasek).
Na mapie: tematyka i obręby przycięte do bieżącej gminy (przycinanie
atlasu), granice wszystkich gmin dla kontekstu, pod spodem nieprzycięty,
przybielony podkład topograficzny GUGiK; na mapie FOP etykiety z nazwą
formy ochrony. Panel jak w mapie ogólnej: tytuł, gmina, powiat,
legenda (tylko klasy widoczne na stronie), pasek skali.

Style tematyczne z qml/ wtyczki: WYDZ_STL.qml (pole STL), WYDZ_ZAB.qml
(pole ZABIEG) - obie na WYDZ_DOPISANE - i FOP.qml (F_OCHRONY, pole TYP).
Warstwy wejściowe bez zmian - kopie NTG_G_* w grupie GRUPA.
"""
import os

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsExpressionContextUtils,
    QgsLayerTreeLayer, QgsLayoutExporter, QgsLayoutObject,
    QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemPicture,
    QgsLayoutItemScaleBar, QgsLayoutMeasurement, QgsLegendStyle,
    QgsPalLayerSettings, QgsPrintLayout, QgsProperty, QgsScaleBarSettings,
    QgsUnitTypes, QgsVectorLayerSimpleLabeling, QgsApplication,
)
from qgis.PyQt.QtGui import QColor

from . import mapa_ogolna as mo

GRUPA = "NTG - mapy gmin"
KATALOG_QML = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "qml")

# klucz: (nazwa layoutu, tytuł, warstwa tematyczna, styl, opis w legendzie
#         dla warstw tła)
MAPY = {
    "TSL": ("NTG_TSL", "TYPY SIEDLISKOWE LASU", "TSL", "WYDZ_STL.qml"),
    "ZAB": ("NTG_Zabiegi", "ZABIEGI GOSPODARCZE", "ZAB", "WYDZ_ZAB.qml"),
    "FOP": ("NTG_FOP", "FORMY OCHRONY PRZYRODY", "FOP", "FOP.qml"),
}

POLA_WYDZ = ("STL", "ZABIEG")
POLE_FOP = "TYP"
POLE_FOP_NAZWA = "NAZWA"      # etykiety na mapie FOP (gdy pole jest)


# ---------------------------------------------------------------- warstwy

def _styl_qml(lyr, plik):
    lyr.loadNamedStyle(os.path.join(KATALOG_QML, plik))
    lyr.setLabelsEnabled(False)


def etykiety_fop(lyr):
    """Nazwa formy ochrony (POLE_FOP_NAZWA) - kursywa z białą obwódką,
    jedna etykieta na nazwę w obrębie strony."""
    pole = mo.pole(lyr, [POLE_FOP_NAZWA])
    if not pole:
        return False
    s = QgsPalLayerSettings()
    s.fieldName = pole
    s.isExpression = False
    s.setFormat(mo._format(7, QColor(90, 30, 30), pogrubiony=True,
                           kursywa=True, bufor=0.8))
    s.placement = QgsPalLayerSettings.Horizontal
    s.autoWrapLength = 22
    s.priority = 6
    s.displayAll = False
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(s))
    lyr.setLabelsEnabled(True)
    return True


def przygotuj_warstwy(projekt, gmin, obr, wydz, ls, fop=None,
                      z_podkladem=True):
    """Kopie NTG_G_* w grupie GRUPA (stara grupa usuwana) i ewentualnie
    podkład NTG_G_PODKLAD."""
    root = projekt.layerTreeRoot()
    stara = root.findGroup(GRUPA)
    if stara:
        for wezel in stara.findLayers():
            projekt.removeMapLayer(wezel.layerId())
        root.removeChildNode(stara)
    grupa = root.insertGroup(0, GRUPA)

    w = {
        "GMIN": mo._kopia(gmin, "NTG_G_GMIN"),
        "OBR": mo._kopia(obr, "NTG_G_OBR"),
        "TSL": mo._kopia(wydz, "NTG_G_TSL"),
        "ZAB": mo._kopia(wydz, "NTG_G_ZABIEGI"),
        "LS": mo._kopia(ls, "NTG_G_LS"),
    }
    if fop is not None:
        w["FOP"] = mo._kopia(fop, "NTG_G_FOP")

    mo.styl_gmin(w["GMIN"])
    mo.styl_obrebow(w["OBR"])
    mo.styl_ls(w["LS"])
    _styl_qml(w["TSL"], MAPY["TSL"][3])
    _styl_qml(w["ZAB"], MAPY["ZAB"][3])
    # reguła bez filtra z WYDZ_ZAB.qml - w legendzie czytelniej
    for r in w["ZAB"].renderer().rootRule().children():
        if r.label() == "Ramka":
            r.setLabel("Pozostałe wydzielenia")
    if fop is not None:
        _styl_qml(w["FOP"], MAPY["FOP"][3])
        w["FOP"].setOpacity(0.6)
        etykiety_fop(w["FOP"])
    if z_podkladem:
        w["PODKLAD"] = mo.podklad("NTG_G_PODKLAD")

    for k in ("GMIN", "OBR", "TSL", "ZAB", "FOP", "LS", "PODKLAD"):
        if k in w:
            projekt.addMapLayer(w[k], False)
            grupa.addChildNode(QgsLayerTreeLayer(w[k]))
    grupa.setItemVisibilityChecked(False)
    grupa.setExpanded(False)
    return w


def warstwy_mapy(klucz, w):
    """Zestaw warstw mapy od góry."""
    if klucz == "FOP":
        warstwy = [w["GMIN"], w["OBR"], w["FOP"], w["LS"]]
    else:
        warstwy = [w["GMIN"], w["OBR"], w[klucz]]
    if "PODKLAD" in w:
        warstwy.append(w["PODKLAD"])
    return warstwy


# ---------------------------------------------------------------- kadr

def _obreby_gminy(obr, pole_obr, kod_gminy, agregat, wyrazenie):
    """Agregat po obrębach warstwy obr, których kod TERYT (same cyfry)
    zaczyna się od 7 cyfr kod_gminy (wyrażenie)."""
    return (
        "aggregate(layer:='%s', aggregate:='%s', expression:=%s, "
        "filter:=left(regexp_replace(\"%s\", '[^0-9]', ''), 7) = "
        "left(regexp_replace(%s, '[^0-9]', ''), 7))"
        % (obr.id(), agregat, wyrazenie, pole_obr, kod_gminy))


def filtr_atlasu(obr, pole_obr, pole_gminy):
    """Jeden obiekt na gminę i tylko gminy z obrębami w warstwie obr.
    Kod gminy przez @parent - samo "pole" w filtrze agregatu odnosi się
    do obiektu warstwy obrębów."""
    return "%s AND coalesce(%s, 0) > 0" % (
        mo._jeden_na_jednostke(pole_gminy),
        _obreby_gminy(obr, pole_obr,
                      "attribute(@parent, '%s')" % pole_gminy, "count", "$id"))


def kadr_wyrazenia(obr, pole_obr, pole_gminy):
    """Wyrażenia zasięgu (xmin, xmax, ymin, ymax) mapy dla strony atlasu:
    zasięg obrębów gminy (_obreby_gminy) z marginesem; gdy brak takich
    obrębów - geometria gminy. Skala wynika z zasięgu (QGIS dopasowuje
    proporcje do ramki mapy)."""
    geom = "coalesce(%s, @atlas_geometry)" % _obreby_gminy(
        obr, pole_obr, "attribute(@atlas_feature, '%s')" % pole_gminy,
        "collect", "$geometry")
    m = mo.MARGINES_KADRU

    def z_geom(wyr):
        return "with_variable('g', %s, %s)" % (geom, wyr)

    xmin = z_geom("x_min(@g) - %s * (x_max(@g) - x_min(@g))" % m)
    xmax = z_geom("x_max(@g) + %s * (x_max(@g) - x_min(@g))" % m)
    ymin = z_geom("y_min(@g) - %s * (y_max(@g) - y_min(@g))" % m)
    ymax = z_geom("y_max(@g) + %s * (y_max(@g) - y_min(@g))" % m)
    return xmin, xmax, ymin, ymax


# ---------------------------------------------------------------- layout

def buduj_layout(projekt, klucz, w, powiat=""):
    nazwa, tytul, tem, _qml = MAPY[klucz]
    mgr = projekt.layoutManager()
    stary = mgr.layoutByName(nazwa)
    if stary:
        mgr.removeLayout(stary)

    layout = QgsPrintLayout(projekt)
    layout.initializeDefaults()
    layout.setName(nazwa)
    layout.pageCollection().page(0).setPageSize(
        mo._rozm(mo.STRONA_W, mo.STRONA_H))
    mgr.addLayout(layout)
    mo.ustaw_teksty(layout, tytul, powiat)

    gmin = w["GMIN"]
    pid = mo.pole(gmin, mo.POLA_ID_GMINY)
    pnaz = mo.pole(gmin, mo.POLA_NAZWY)

    atlas = layout.atlas()
    atlas.setCoverageLayer(gmin)
    atlas.setEnabled(True)
    atlas.setFilterFeatures(True)
    pole_obr = mo.pole(w["OBR"], mo.POLA_ID_OBREBU)
    atlas.setFilterExpression(filtr_atlasu(w["OBR"], pole_obr, pid))
    atlas.setSortFeatures(True)
    atlas.setSortExpression('"%s"' % pnaz)
    atlas.setPageNameExpression('"%s"' % pnaz)
    # <TERYT gminy>_<nazwa gminy>_<mapa>_NTG, np. 1804052_Laszki_FOP_NTG
    atlas.setFilenameExpression(
        "regexp_replace(\"%s\", '[^0-9]', '') || '_' || "
        "regexp_replace(\"%s\", '[^\\\\w-]+', '_') || '_%s_NTG'"
        % (pid, pnaz, nazwa[len("NTG_"):]))

    mapa_w = mo.STRONA_W - 2 * mo.MARG - mo.PANEL_W
    mapa_h = mo.STRONA_H - 2 * mo.MARG
    px = mo.MARG + mapa_w
    wx, ww = px + 3, mo.PANEL_W - 6

    m = QgsLayoutItemMap(layout)
    m.setId(mo.ID_MAPA)
    layout.addLayoutItem(m)
    m.attemptMove(mo._poz(mo.MARG, mo.MARG))
    m.attemptResize(mo._rozm(mapa_w, mapa_h))
    m.setCrs(QgsCoordinateReferenceSystem("EPSG:2180"))
    m.setLayers(warstwy_mapy(klucz, w))
    m.setKeepLayerSet(True)
    m.setFrameEnabled(True)
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))
    # kadr do obrębów gminy - zasięg z wyrażeń, nie z atlasu (atlas
    # kadruje tylko do geometrii obiektu pokrycia, czyli gminy)
    m.setAtlasDriven(False)
    xmin, xmax, ymin, ymax = kadr_wyrazenia(w["OBR"], pole_obr, pid)
    dd = m.dataDefinedProperties()
    for wl, wyr in ((QgsLayoutObject.MapXMin, xmin),
                    (QgsLayoutObject.MapXMax, xmax),
                    (QgsLayoutObject.MapYMin, ymin),
                    (QgsLayoutObject.MapYMax, ymax)):
        dd.setProperty(wl, QgsProperty.fromExpression(wyr))
    m.setDataDefinedProperties(dd)
    # tematyka i obręby tylko w bieżącej gminie; granice gmin i podkład -
    # na całej mapie
    przyc = m.atlasClippingSettings()
    przyc.setEnabled(True)
    przyc.setRestrictToLayers(True)
    przyc.setForceLabelsInsideFeature(True)
    przyc.setLayersToClip([lyr for lyr in warstwy_mapy(klucz, w)
                           if lyr is not w["GMIN"]
                           and lyr is not w.get("PODKLAD")])
    m.zoomToExtent(gmin.extent())

    sciezki_svg = QgsApplication.svgPaths()
    n = QgsLayoutItemPicture(layout)
    n.setId("NORTH_ARROW")
    if sciezki_svg:
        n.setPicturePath(os.path.join(sciezki_svg[0], "arrows",
                                      "NorthArrow_02.svg"))
    n.setLinkedMap(m)
    n.setNorthMode(QgsLayoutItemPicture.GridNorth)
    layout.addLayoutItem(n)
    n.attemptMove(mo._poz(mo.MARG + 4, mo.MARG + 4))
    n.attemptResize(mo._rozm(11, 15))

    mo._prostokat(layout, "ramkaP", px, mo.MARG, mo.PANEL_W, mapa_h,
                  wypelnienie="solid")
    y = mo.MARG + 4
    mo._etykieta(layout, "tytul", "[% @ntg_tytul %]", wx, y, ww, 18, 15,
                 True, font=mo.FONT_W)
    y += 20
    mo._prostokat(layout, "kreska1", wx, y, ww, 0.01, grubosc="0.2")
    y += 3
    mo._etykieta(layout, "gmina_tytul_ops", "GMINA", wx, y, ww, 4, 8)
    y += 4
    mo._etykieta(layout, "zm-gmina",
                 "[%% attribute(@atlas_feature, '%s') %%]" % pnaz,
                 wx, y, ww, 6, 12, True)
    y += 7
    mo._etykieta(layout, "powiat_tytul_ops", "POWIAT", wx, y, ww, 4, 8)
    y += 4
    mo._etykieta(layout, "zm-powiat", "[% @ntg_powiat %]", wx, y, ww, 6, 11,
                 True)
    y += 8
    mo._prostokat(layout, "kreska2", wx, y, ww, 0.01, grubosc="0.2")
    y += 3

    lg = QgsLayoutItemLegend(layout)
    lg.setId(mo.ID_LEGENDA)
    lg.setTitle("Legenda")
    lg.setLinkedMap(m)
    lg.setAutoUpdateModel(False)
    lg.setResizeToContents(False)
    lg.setLegendFilterByMapEnabled(True)
    lg.rstyle(QgsLegendStyle.Title).setTextFormat(
        mo._format(11, QColor(0, 0, 0), pogrubiony=True))
    lg.rstyle(QgsLegendStyle.Group).setTextFormat(
        mo._format(8, QColor(0, 0, 0), pogrubiony=True))
    lg.rstyle(QgsLegendStyle.Subgroup).setTextFormat(
        mo._format(8, QColor(0, 0, 0), pogrubiony=True))
    lg.rstyle(QgsLegendStyle.SymbolLabel).setTextFormat(
        mo._format(7, QColor(0, 0, 0)))
    lg.setSymbolWidth(7)
    lg.setSymbolHeight(3.5)
    lg.setBoxSpace(1)
    lg.setWrapString("|")
    layout.addLayoutItem(lg)
    korzen = lg.model().rootGroup()
    korzen.removeAllChildren()
    opisy = [(tem, {"TSL": "Typ siedliskowy lasu", "ZAB": "Zabiegi",
                    "FOP": "Formy ochrony przyrody"}[klucz])]
    if klucz == "FOP":
        opisy.append(("LS", "Grunty leśne|objęte opracowaniem"))
    opisy += [("GMIN", "Granica gminy"),
              ("OBR", "Granica obrębu|ewidencyjnego")]
    for k, opis in opisy:
        wz = korzen.addLayer(w[k])
        wz.setUseLayerName(False)
        wz.setName(opis)
        wz.setCustomProperty("legend/title-label", opis)
        lg.model().refreshLayerLegend(wz)
    lg.updateLegend()
    lg.attemptMove(mo._poz(wx, y))
    lg.attemptResize(mo._rozm(ww, mo.MARG + mapa_h - 22 - y))

    sb = QgsLayoutItemScaleBar(layout)
    sb.setId(mo.ID_SKALA)
    sb.setStyle("Single Box")
    sb.setLinkedMap(m)
    sb.setUnits(QgsUnitTypes.DistanceKilometers)
    sb.setUnitLabel("km")
    sb.setNumberOfSegmentsLeft(0)
    sb.setNumberOfSegments(4)
    sb.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFitWidth)
    sb.setMinimumBarWidth(ww * 0.6)
    sb.setMaximumBarWidth(ww * 0.85)
    sb.setHeight(2)
    sb.setTextFormat(mo._format(8, QColor(0, 0, 0)))
    layout.addLayoutItem(sb)
    sb.attemptMove(mo._poz(wx + 3, mo.MARG + mapa_h - 16))

    mo._prostokat(layout, "ramka", mo.MARG, mo.MARG,
                  mo.STRONA_W - 2 * mo.MARG, mapa_h, grubosc="0.5")
    return layout


# ---------------------------------------------------------------- API

def eksportuj_png(layout, folder, dpi=300):
    """PNG na każdą gminę atlasu. Zwraca (ok, komunikat)."""
    ust = QgsLayoutExporter.ImageExportSettings()
    ust.dpi = dpi
    wynik, blad = QgsLayoutExporter.exportToImage(
        layout.atlas(), os.path.join(folder, ""), "png", ust)
    return wynik == QgsLayoutExporter.Success, blad


def generuj(projekt, klucze, gmin, obr, wydz, ls, fop=None, powiat="",
            folder_png=None, z_podkladem=True):
    """Layouty dla wybranych kluczy (TSL/ZAB/FOP). Zwraca
    [(layout, ok_png, komunikat)]."""
    QgsExpressionContextUtils.setProjectVariable(projekt, "ntg_powiat",
                                                 powiat)
    w = przygotuj_warstwy(projekt, gmin, obr, wydz, ls, fop, z_podkladem)
    wyniki = []
    for k in klucze:
        if k == "FOP" and fop is None:
            continue
        layout = buduj_layout(projekt, k, w, powiat)
        ok, kom = (None, "")
        if folder_png:
            ok, kom = eksportuj_png(layout, folder_png)
        wyniki.append((layout, ok, kom))
    return wyniki
