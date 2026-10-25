# -*- coding: utf-8 -*-
"""Mapa ogólna obiektu do prezentacji NTG - layout "NTG_Ogolna" (A4 poziomo).

Mapa: obszar opracowania (Ls), granice gmin i obrębów, zasięgi nadleśnictw,
rozbielenie poza gminami obiektu, pod spodem mocno przybielony podkład
topograficzny GUGiK (WMTS - podklad()). Kadr do Ls z małym marginesem, bez
zaokrąglania skali (o skali mówi pasek). Panel po prawej: tytuł, powiat,
legenda, pasek skali.

Warstwy wejściowe nie są przestylowywane - do projektu trafiają ich kopie
NTG_* w grupie GRUPA (przebudowywanej przy każdym uruchomieniu), wyłączone
w drzewie, bo layout ma zablokowany zestaw warstw.

Teksty panelu to zmienne layoutu @ntg_tytul / @ntg_powiat - do zmiany
z poziomu skryptu bez szukania etykiet (ustaw_teksty()).
"""
import os

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsExpressionContextUtils, QgsFillSymbol,
    QgsGeometryGeneratorSymbolLayer, QgsInvertedPolygonRenderer,
    QgsLayerTreeLayer, QgsLayoutExporter, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemPicture,
    QgsLayoutItemScaleBar, QgsLayoutItemShape, QgsLayoutMeasurement,
    QgsLayoutPoint, QgsLayoutSize, QgsLegendStyle, QgsLineSymbol,
    QgsPalLayerSettings, QgsPrintLayout, QgsProperty, QgsRectangle,
    QgsRasterLayer, QgsRuleBasedRenderer, QgsSimpleFillSymbolLayer,
    QgsSingleSymbolRenderer, QgsTextBufferSettings, QgsTextFormat,
    QgsUnitTypes, QgsVectorLayer,
    QgsVectorLayerSimpleLabeling, QgsApplication,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont

NAZWA_LAYOUTU = "NTG_Ogolna"
GRUPA = "NTG - mapa ogólna"

ID_MAPA = "MAPA"
ID_LEGENDA = "LEGENDA"
ID_SKALA = "skala_bar"

TYTUL_DOMYSLNY = "MAPA OGÓLNA OBIEKTU"

# pola kodu i nazwy jednostki: EGiB (PZGiK) / PRG
POLA_ID_GMINY = ["IDJEDNOSTK", "JPT_KOD_JE", "TERYT"]
POLA_ID_OBREBU = ["IDOBREBU", "JPT_KOD_JE", "TERYT"]
POLA_NAZWY = ["NAZWAWLASN", "JPT_NAZWA_", "NAZWA", "NAME"]
POLE_NAZWA_NADL = "ins_name"

# kolory jak w szablonach MAPA_OGOLNA / MAPA_PRZEGLADOWA
KOLOR_GMINA = "149,23,149"
KOLOR_GMINA_ETYK = QColor(141, 63, 133)
KOLOR_OBREB = "203,37,184"
KOLOR_OBREB_ETYK = QColor(220, 95, 195)
KOLOR_LS = "10,159,25"
KOLOR_NADL = "0,100,0"

FONT = "Arial"
FONT_W = "Arial Narrow"

# A4 poziomo, mm
STRONA_W, STRONA_H = 297.0, 210.0
MARG = 5.0
PANEL_W = 58.0

MARGINES_KADRU = 0.03   # część szerokości/wysokości kadrowanych obiektów

# podkład: mapa topograficzna GUGiK (WMTS, EPSG:2180), mocno przybielona
PODKLAD_URI = (
    "contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10"
    "&format=image/jpeg&layers=MAPA%20TOPOGRAFICZNA&styles=default"
    "&tileMatrixSet=EPSG:2180&url=https://mapy.geoportal.gov.pl/wss/service/"
    "WMTS/guest/wmts/TOPO?SERVICE%3DWMTS%26REQUEST%3DGetCapabilities")
PODKLAD_KRYCIE = 0.3


def pole(lyr, kandydaci):
    """Pierwsze pole z listy obecne w warstwie (bez wielkości liter)."""
    nazwy = {f.name().upper(): f.name() for f in lyr.fields()}
    for k in kandydaci:
        if k.upper() in nazwy:
            return nazwy[k.upper()]
    return None


# ---------------------------------------------------------------- style

def _format(rozmiar, kolor, pogrubiony=False, kursywa=False, bufor=0.0,
            font=FONT):
    f = QgsTextFormat()
    q = QFont(font)
    q.setBold(pogrubiony)
    q.setItalic(kursywa)
    f.setFont(q)
    f.setSize(rozmiar)
    f.setSizeUnit(QgsUnitTypes.RenderPoints)
    f.setColor(kolor)
    if bufor:
        b = QgsTextBufferSettings()
        b.setEnabled(True)
        b.setSize(bufor)
        b.setSizeUnit(QgsUnitTypes.RenderMillimeters)
        b.setColor(QColor(255, 255, 255))
        f.setBuffer(b)
    return f


def _jeden_na_jednostke(pole_id):
    # warstwy EGiB bywają podzielone na części albo zdublowane po scalaniu
    # SHP z kilku folderów - rysujemy/opisujemy jeden obiekt na jednostkę
    return '$id = minimum($id, group_by:="%s")' % pole_id


def _etykiety(lyr, wyrazenie, fmt, priorytet=5, zawijanie=14, pole_id=None):
    s = QgsPalLayerSettings()
    s.fieldName = wyrazenie
    s.isExpression = True
    s.setFormat(fmt)
    s.placement = QgsPalLayerSettings.Horizontal
    s.priority = priorytet
    s.autoWrapLength = zawijanie
    if pole_id:
        dd = s.dataDefinedProperties()
        dd.setProperty(QgsPalLayerSettings.Show,
                       QgsProperty.fromExpression(_jeden_na_jednostke(pole_id)))
        s.setDataDefinedProperties(dd)
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(s))
    lyr.setLabelsEnabled(True)


def _granica_scalona(kolor, grubosc, pole_id, styl_linii="solid"):
    """Obrys jednostki ze scalonych obiektów, rysowany raz na jednostkę."""
    linia = QgsLineSymbol.createSimple({
        "line_color": kolor, "line_width": str(grubosc),
        "line_width_unit": "MM", "line_style": styl_linii,
        "joinstyle": "round", "capstyle": "round",
    })
    gen = QgsGeometryGeneratorSymbolLayer.create({
        "geometryModifier":
            'boundary(buffer(collect($geometry, group_by:="%s"), 0))'
            % pole_id,
        "SymbolType": "Line",
    })
    gen.setSubSymbol(linia)
    sym = QgsFillSymbol()
    sym.changeSymbolLayer(0, gen)
    korzen = QgsRuleBasedRenderer.Rule(None)
    korzen.appendChild(QgsRuleBasedRenderer.Rule(
        sym, filterExp=_jeden_na_jednostke(pole_id)))
    return QgsRuleBasedRenderer(korzen)


def styl_gmin(lyr):
    pid, pnaz = pole(lyr, POLA_ID_GMINY), pole(lyr, POLA_NAZWY)
    lyr.setRenderer(_granica_scalona(KOLOR_GMINA, 0.7, pid))
    # *_1 = gmina miejska; nazwa bez "Miasto" (np. Jarosław) dostaje "m."
    _etykiety(lyr,
              "CASE WHEN right(\"%s\", 1) = '1' AND \"%s\" NOT ILIKE "
              "'miasto%%' THEN 'm. ' ELSE 'gm. ' END || \"%s\""
              % (pid, pnaz, pnaz),
              _format(9, KOLOR_GMINA_ETYK, pogrubiony=True, bufor=1.0),
              priorytet=9, pole_id=pid)


def styl_obrebow(lyr):
    pid, pnaz = pole(lyr, POLA_ID_OBREBU), pole(lyr, POLA_NAZWY)
    lyr.setRenderer(_granica_scalona(KOLOR_OBREB, 0.2, pid, "dash"))
    _etykiety(lyr, '"%s"' % pnaz, _format(5, KOLOR_OBREB_ETYK, bufor=0.5),
              priorytet=3, pole_id=pid)


def styl_ls(lyr):
    lyr.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({
        "color": KOLOR_LS, "style": "solid", "outline_color": KOLOR_LS,
        "outline_width": "0.1", "outline_width_unit": "MM",
    })))
    lyr.setOpacity(1.0)
    lyr.setLabelsEnabled(False)


def styl_nadlesnictw(lyr):
    # jasna, szeroka wstęga pod kreskowaną linią
    sym = QgsFillSymbol.createSimple({
        "style": "no", "outline_color": "120,190,120,140",
        "outline_width": "2.2", "outline_width_unit": "MM",
    })
    sym.appendSymbolLayer(QgsSimpleFillSymbolLayer.create({
        "style": "no", "outline_color": KOLOR_NADL, "outline_width": "0.5",
        "outline_width_unit": "MM", "outline_style": "dash",
    }))
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    _etykiety(lyr, "'Nadl. ' || title(lower(\"%s\"))" % POLE_NAZWA_NADL,
              _format(9, QColor(0, 100, 0), kursywa=True, bufor=1.0),
              priorytet=7, zawijanie=0)


def styl_maski(lyr):
    """Rozbielenie poza gminami obiektu. Jeden obiekt na gminę - przy
    zdublowanych gminach (np. 8 kopii po scalaniu SHP) parzysta liczba
    nakładających się obiektów dawała w odwróconym wielokącie "zewnątrz"
    i bieliło się też wnętrze gmin."""
    sym = QgsFillSymbol.createSimple({
        "color": "255,255,255,150", "style": "solid", "outline_style": "no",
    })
    korzen = QgsRuleBasedRenderer.Rule(None)
    korzen.appendChild(QgsRuleBasedRenderer.Rule(
        sym, filterExp=_jeden_na_jednostke(pole(lyr, POLA_ID_GMINY))))
    lyr.setRenderer(QgsInvertedPolygonRenderer(QgsRuleBasedRenderer(korzen)))
    lyr.setLabelsEnabled(False)


# ---------------------------------------------------------------- warstwy

def podklad(nazwa):
    """Warstwa podkładu topograficznego (WMTS GUGiK), przybielona - krycie
    PODKLAD_KRYCIE na białym tle. Zgłasza RuntimeError, gdy usługa nie
    odpowiada."""
    lyr = QgsRasterLayer(PODKLAD_URI, nazwa, "wms")
    if not lyr.isValid():
        raise RuntimeError(
            "Nie udało się wczytać podkładu topograficznego GUGiK (WMTS). "
            "Sprawdź połączenie z internetem albo wyłącz podkład.")
    lyr.renderer().setOpacity(PODKLAD_KRYCIE)
    return lyr


def _kopia(zrodlo, nazwa):
    lyr = QgsVectorLayer(zrodlo.source(), nazwa, zrodlo.providerType())
    if not lyr.isValid():
        raise RuntimeError("Nie udało się wczytać warstwy " + zrodlo.source())
    return lyr


def przygotuj_warstwy(projekt, gmin, obr, ls, nadl, z_podkladem=True):
    """Kopie NTG_* w grupie GRUPA (stara grupa usuwana) i ewentualnie
    podkład NTG_PODKLAD. Zwraca słownik."""
    root = projekt.layerTreeRoot()
    stara = root.findGroup(GRUPA)
    if stara:
        for wezel in stara.findLayers():
            projekt.removeMapLayer(wezel.layerId())
        root.removeChildNode(stara)
    grupa = root.insertGroup(0, GRUPA)

    w = {
        "NADL": _kopia(nadl, "NTG_NADL"),
        "GMIN": _kopia(gmin, "NTG_GMIN"),
        "OBR": _kopia(obr, "NTG_OBR"),
        "MASKA": _kopia(gmin, "NTG_MASKA"),
        "LS": _kopia(ls, "NTG_LS"),
    }
    styl_nadlesnictw(w["NADL"])
    styl_gmin(w["GMIN"])
    styl_obrebow(w["OBR"])
    styl_maski(w["MASKA"])
    styl_ls(w["LS"])
    if z_podkladem:
        w["PODKLAD"] = podklad("NTG_PODKLAD")
    for k in ("NADL", "GMIN", "OBR", "MASKA", "LS", "PODKLAD"):
        if k in w:
            projekt.addMapLayer(w[k], False)
            grupa.addChildNode(QgsLayerTreeLayer(w[k]))
    grupa.setItemVisibilityChecked(False)
    grupa.setExpanded(False)
    return w


# ---------------------------------------------------------------- layout

def _poz(x, y):
    return QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters)


def _rozm(w, h):
    return QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters)


def _etykieta(layout, id_, tekst, x, y, w, h, rozmiar, pogrubiony=False,
              font=FONT):
    e = QgsLayoutItemLabel(layout)
    e.setId(id_)
    e.setText(tekst)
    e.setTextFormat(_format(rozmiar, QColor(0, 0, 0), pogrubiony, font=font))
    e.setHAlign(Qt.AlignHCenter)
    e.setVAlign(Qt.AlignVCenter)
    e.setMarginX(0)
    e.setMarginY(0)
    layout.addLayoutItem(e)
    e.attemptMove(_poz(x, y))
    e.attemptResize(_rozm(w, h))
    return e


def _prostokat(layout, id_, x, y, w, h, wypelnienie="no", grubosc="0.3"):
    s = QgsLayoutItemShape(layout)
    s.setShapeType(QgsLayoutItemShape.Rectangle)
    s.setId(id_)
    s.setSymbol(QgsFillSymbol.createSimple({
        "color": "255,255,255", "style": wypelnienie,
        "outline_color": "0,0,0", "outline_width": grubosc,
    }))
    layout.addLayoutItem(s)
    s.attemptMove(_poz(x, y))
    s.attemptResize(_rozm(w, h))
    return s


def buduj_layout(projekt, w, tytul=TYTUL_DOMYSLNY, powiat=""):
    mgr = projekt.layoutManager()
    stary = mgr.layoutByName(NAZWA_LAYOUTU)
    if stary:
        mgr.removeLayout(stary)

    layout = QgsPrintLayout(projekt)
    layout.initializeDefaults()
    layout.setName(NAZWA_LAYOUTU)
    layout.pageCollection().page(0).setPageSize(_rozm(STRONA_W, STRONA_H))
    mgr.addLayout(layout)
    ustaw_teksty(layout, tytul, powiat)

    mapa_w = STRONA_W - 2 * MARG - PANEL_W
    mapa_h = STRONA_H - 2 * MARG
    px = MARG + mapa_w
    wx, ww = px + 3, PANEL_W - 6

    m = QgsLayoutItemMap(layout)
    m.setId(ID_MAPA)
    layout.addLayoutItem(m)
    m.attemptMove(_poz(MARG, MARG))
    m.attemptResize(_rozm(mapa_w, mapa_h))
    m.setCrs(QgsCoordinateReferenceSystem("EPSG:2180"))
    m.setLayers([w[k] for k in ("NADL", "GMIN", "OBR", "MASKA", "LS",
                                "PODKLAD") if k in w])
    m.setKeepLayerSet(True)
    m.setFrameEnabled(True)
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))

    sciezki_svg = QgsApplication.svgPaths()
    n = QgsLayoutItemPicture(layout)
    n.setId("NORTH_ARROW")
    if sciezki_svg:
        n.setPicturePath(os.path.join(sciezki_svg[0], "arrows",
                                      "NorthArrow_02.svg"))
    n.setLinkedMap(m)
    n.setNorthMode(QgsLayoutItemPicture.GridNorth)
    layout.addLayoutItem(n)
    n.attemptMove(_poz(MARG + 4, MARG + 4))
    n.attemptResize(_rozm(11, 15))

    _prostokat(layout, "ramkaP", px, MARG, PANEL_W, mapa_h,
               wypelnienie="solid")

    y = MARG + 4
    _etykieta(layout, "tytul", "[% @ntg_tytul %]", wx, y, ww, 22, 16, True,
              font=FONT_W)
    y += 24
    _prostokat(layout, "kreska1", wx, y, ww, 0.01, grubosc="0.2")
    y += 4
    _etykieta(layout, "powiat_tytul_ops", "POWIAT", wx, y, ww, 4, 8)
    y += 4
    _etykieta(layout, "zm-powiat", "[% @ntg_powiat %]", wx, y, ww, 6, 12,
              True)
    y += 9
    _prostokat(layout, "kreska2", wx, y, ww, 0.01, grubosc="0.2")
    y += 4

    lg = QgsLayoutItemLegend(layout)
    lg.setId(ID_LEGENDA)
    lg.setTitle("Legenda")
    lg.setLinkedMap(m)
    lg.setAutoUpdateModel(False)
    lg.setResizeToContents(False)
    lg.rstyle(QgsLegendStyle.Title).setTextFormat(
        _format(11, QColor(0, 0, 0), pogrubiony=True))
    lg.rstyle(QgsLegendStyle.SymbolLabel).setTextFormat(
        _format(8, QColor(0, 0, 0)))
    lg.setSymbolWidth(9)
    lg.setSymbolHeight(4)
    lg.setBoxSpace(1)
    lg.setWrapString("|")
    layout.addLayoutItem(lg)
    korzen = lg.model().rootGroup()
    korzen.removeAllChildren()
    for k, opis in (("LS", "Grunty leśne|objęte opracowaniem"),
                    ("GMIN", "Granica gminy"),
                    ("OBR", "Granica obrębu|ewidencyjnego"),
                    ("NADL", "Granica nadleśnictwa")):
        wz = korzen.addLayer(w[k])
        wz.setUseLayerName(False)
        wz.setName(opis)
        wz.setCustomProperty("legend/title-label", opis)
        lg.model().refreshLayerLegend(wz)
    lg.updateLegend()
    lg.attemptMove(_poz(wx, y))
    lg.attemptResize(_rozm(ww, 60))

    sb = QgsLayoutItemScaleBar(layout)
    sb.setId(ID_SKALA)
    sb.setStyle("Single Box")
    sb.setLinkedMap(m)
    sb.setUnits(QgsUnitTypes.DistanceKilometers)
    sb.setUnitLabel("km")
    sb.setNumberOfSegmentsLeft(0)
    sb.setNumberOfSegments(4)
    sb.setHeight(2)
    sb.setTextFormat(_format(8, QColor(0, 0, 0)))
    layout.addLayoutItem(sb)
    sb.attemptMove(_poz(wx, MARG + mapa_h - 16))

    _prostokat(layout, "ramka", MARG, MARG, STRONA_W - 2 * MARG, mapa_h,
               grubosc="0.5")
    return layout


# ---------------------------------------------------------------- API

def ustaw_teksty(layout, tytul=None, powiat=None):
    if tytul is not None:
        QgsExpressionContextUtils.setLayoutVariable(layout, "ntg_tytul", tytul)
    if powiat is not None:
        QgsExpressionContextUtils.setLayoutVariable(layout, "ntg_powiat",
                                                    powiat)
    layout.refresh()


def ustaw_zasieg(layout, zasieg, margines=MARGINES_KADRU):
    """Kadruje mapę do zasięgu z marginesem (skala wynikowa, bez
    zaokrąglania) i dopasowuje pasek skali."""
    m = layout.itemById(ID_MAPA)
    r = QgsRectangle(zasieg)
    r.grow(max(r.width(), r.height()) * margines)
    m.zoomToExtent(r)
    sb = layout.itemById(ID_SKALA)
    if sb:
        dopasuj_pasek_skali(sb)


def dopasuj_pasek_skali(sb):
    """Segment 1/2/2,5/5 x 10^n km - 4 segmenty na ~80% szerokości panelu,
    pasek wyśrodkowany w panelu."""
    m = sb.linkedMap()
    px = STRONA_W - MARG - PANEL_W
    km_na_mm = m.scale() / 1e6
    cel = (PANEL_W - 6) * 0.8 / sb.numberOfSegments() * km_na_mm
    kandydaci = [k * 10 ** e for e in range(-2, 4) for k in (1, 2, 2.5, 5)]
    sb.setUnitsPerSegment(
        max([k for k in kandydaci if k <= cel] or [kandydaci[0]]))
    sb.refreshItemSize()
    w = sb.sizeWithUnits().width()
    sb.attemptMove(_poz(px + (PANEL_W - w) / 2, sb.positionWithUnits().y()))


def eksportuj_png(layout, sciezka, dpi=300):
    ust = QgsLayoutExporter.ImageExportSettings()
    ust.dpi = dpi
    wynik = QgsLayoutExporter(layout).exportToImage(sciezka, ust)
    return wynik == QgsLayoutExporter.Success


def generuj(projekt, gmin, obr, ls, nadl, tytul=TYTUL_DOMYSLNY, powiat="",
            png=None, z_podkladem=True):
    """Całość: kopie warstw ze stylami, layout, zasięg wg Ls, opcjonalnie PNG.
    Zwraca (layout, png_ok)."""
    w = przygotuj_warstwy(projekt, gmin, obr, ls, nadl, z_podkladem)
    layout = buduj_layout(projekt, w, tytul, powiat)
    ustaw_zasieg(layout, w["LS"].extent())
    png_ok = eksportuj_png(layout, png) if png else None
    return layout, png_ok
