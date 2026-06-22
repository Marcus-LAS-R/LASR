""" Pokrywanie zbioru prostokątów (np. bbox wydzieleń) minimalną liczbą
kafli o ustalonym rozmiarze (np. stron atlasu), tak żeby każdy prostokąt
zmieścił się w całości w jednym kaflu - bez przecinania krawędzią.
Kafle mogą się nachodzić tam, gdzie obiekty leżą blisko siebie.

Logika nie zależy od qgis.core - operuje na zwykłych krotkach
(xmin, ymin, xmax, ymax), żeby można ją wykorzystać w różnych skryptach
(np. shp_obszary_ciecia.py, shp_atlasuj.py).
"""


def rozmiar_kafla_z_skali(papier_mm, skala, margines_mm=30):
    """ Rozmiar kafla w metrach [szer, wys] na podstawie formatu papieru
    w mm (np. A3 w poziomie = [420, 297]), skali mapy i marginesu
    (zakładki) w mm odejmowanego z każdej strony łącznie.
    """
    return [
        (((papier_mm[0] - margines_mm) / 10) * skala) / 100,
        (((papier_mm[1] - margines_mm) / 10) * skala) / 100,
    ]


def _max_y_overlap(przedzialy):
    """ (licznik, y) punktu o maksymalnym pokryciu wśród podanych
    przedziałów [y0, y1] (domkniętych). """
    eventy = []
    for (y0, y1) in przedzialy:
        eventy.append((y0, 0))
        eventy.append((y1, 1))
    eventy.sort()

    best_cnt, cnt = 0, 0
    best_y = eventy[0][0] if eventy else 0
    i, n = 0, len(eventy)
    while i < n:
        y_cur = eventy[i][0]
        starty = konce = 0
        while i < n and eventy[i][0] == y_cur:
            if eventy[i][1] == 0:
                starty += 1
            else:
                konce += 1
            i += 1
        cnt += starty
        if cnt > best_cnt:
            best_cnt, best_y = cnt, y_cur
        cnt -= konce
    return best_cnt, best_y


def _najlepszy_kafel(anchor, kandydaci, w, h):
    """ Pozycja (wx, wy) lewego-dolnego rogu kafla WxH, który w całości
    obejmuje anchor i maksymalizuje liczbę pokrytych kandydatów. """
    ax0, ay0, ax1, ay1 = anchor
    wx_lo, wx_hi = ax1 - w, ax0
    wy_lo, wy_hi = ay1 - h, ay0

    items = []
    for b in kandydaci:
        x0 = max(b[2] - w, wx_lo)
        x1 = min(b[0], wx_hi)
        if x0 > x1:
            continue
        y0 = max(b[3] - h, wy_lo)
        y1 = min(b[1], wy_hi)
        if y0 > y1:
            continue
        items.append((x0, x1, y0, y1))

    eventy_x = []
    for i, (x0, x1, _, _) in enumerate(items):
        eventy_x.append((x0, 0, i))
        eventy_x.append((x1, 1, i))
    eventy_x.sort()

    aktywne = {}
    best_cnt = 0
    best_wx, best_wy = (wx_lo + wx_hi) / 2, (wy_lo + wy_hi) / 2
    i, n = 0, len(eventy_x)
    while i < n:
        x_cur = eventy_x[i][0]
        starty, konce = [], []
        while i < n and eventy_x[i][0] == x_cur:
            _, typ, idx = eventy_x[i]
            (starty if typ == 0 else konce).append(idx)
            i += 1

        for idx in starty:
            aktywne[idx] = (items[idx][2], items[idx][3])

        if aktywne:
            cnt, y_best = _max_y_overlap(list(aktywne.values()))
            if cnt > best_cnt:
                best_cnt, best_wx, best_wy = cnt, x_cur, y_best

        for idx in konce:
            aktywne.pop(idx, None)

    # wsrod (wx, wy) o tym samym max. pokryciu wybierany jest dowolny
    # punkt skrajny (krawedz jakiegos kandydata) - przez to maly klaster
    # potrafi wyladowac w samym rogu duzego kafla. Wycentruj kafel na
    # obwiedni faktycznie pokrytych kandydatow - nie zmienia to ktore
    # kandydaci sa pokryci (ich obwiednia z definicji miesci sie w wxh),
    # tylko poprawia wygodne wycentrowanie.
    pokryte = [
        b for b in kandydaci
        if best_wx <= b[0] and b[2] <= best_wx + w and
        best_wy <= b[1] and b[3] <= best_wy + h
    ]
    if pokryte:
        ux0 = min(b[0] for b in pokryte)
        uy0 = min(b[1] for b in pokryte)
        ux1 = max(b[2] for b in pokryte)
        uy1 = max(b[3] for b in pokryte)
        best_wx = (ux0 + ux1) / 2 - w / 2
        best_wy = (uy0 + uy1) / 2 - h / 2

    return best_wx, best_wy


def pokryj_kaflami(bboxy, w, h):
    """ Zachłannie pokrywa zbiór prostokątów `bboxy`
    (lista (xmin, ymin, xmax, ymax)) minimalną liczbą kafli o rozmiarze
    w x h. Każdy kolejny kafel jest tak ustawiony, by w całości objąć
    "kotwicę" (pierwszy z kolei nieobsłużony prostokąt, w porządku
    góra-dół/lewo-prawo) i jednocześnie pokryć maksymalną liczbę innych
    pozostałych nieobsłużonych prostokątów.

    Zwraca listę kafli (xmin, ymin, xmax, ymax) w kolejności powstawania.
    Kafle mogą się nachodzić.
    """
    nieobsluzone = sorted(
        bboxy, key=lambda b: (-((b[1] + b[3]) / 2), (b[0] + b[2]) / 2))

    kafle = []
    while nieobsluzone:
        anchor = nieobsluzone[0]
        ax0, ay0, ax1, ay1 = anchor

        kandydaci = [
            b for b in nieobsluzone
            if max(ax1, b[2]) - min(ax0, b[0]) <= w and
            max(ay1, b[3]) - min(ay0, b[1]) <= h
        ]

        wx, wy = _najlepszy_kafel(anchor, kandydaci, w, h)
        kafel = (wx, wy, wx + w, wy + h)
        kafle.append(kafel)

        rx0, ry0, rx1, ry1 = kafel
        nieobsluzone = [
            b for b in nieobsluzone
            if not (rx0 <= b[0] and b[2] <= rx1 and
                    ry0 <= b[1] and b[3] <= ry1)
        ]

    return kafle
