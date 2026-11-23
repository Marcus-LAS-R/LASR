# -*- coding: utf-8 -*-
"""Zestawienia raportów TPU - część bez QGIS-a (testowalna:
testy/test_tpu_raporty.py): raporty Taksatora PU, nazwy i foldery wyników,
plan, pomocnik .NET (kompilacja, uruchamianie), Excel (składanie zestawienia,
zapis xlsx) i raporty na płyty (bez danych osobowych).

Raporty generuje biblioteka Taksatora PU (ReportsHelper.dll) przez pomocnika
tpu_raporty_pomocnik.cs - bez otwierania Taksatora; wynik identyczny jak
z Taksatora (sprawdzone na 2.0.56). "Zestawienie raportów" = 16 raportów
jako arkusze jednego pliku, w kolejności i z nazwami arkuszy jak w
Taksatorze (ZESTAWIENIE, ARKUSZE).

Wynik: <folder bazy>/Raporty_TPU/<folder raportu>/<gmina>-<obręb>-<nazwa
obrębu>.xlsx (nazwy plików jak w Taksatorze, np. 115-0001-Białęgi.xlsx).
"""
import hashlib
import os
import re
import shutil
import subprocess

FOLDER_RAPORTOW = 'Raporty_TPU'
ZESTAWIENIE = 0  # id "Zestawienie raportów" (nie jest raportem Taksatora)

# (id, nazwa jak w Taksatorze, folder wyników, dane osobowe)
RAPORTY = (
    (ZESTAWIENIE, 'Zestawienie raportów', 'Zestawienie_raportow', True),
    (1, 'Zestawienie powierzchni i miąższości gatunków panujących w klasach '
        'i podklasach wieku wg głównej funkcji lasu',
     'Gatunki_panujace_wg_funkcji_lasu', False),
    (2, 'Zestawienie powierzchni i miąższości gatunków panujących w TSL wg '
        'klas i podklas wieku', 'Gatunki_panujace_wg_TSL', False),
    (3, 'Rejestr działek leśnych i gruntów przeznaczonych do zalesienia oraz '
        'ich właścicieli', 'Rejestr_dzialek_i_wlascicieli', True),
    (4, 'Opis taksacyjny lasów i gruntów przeznaczonych do zalesienia',
     'Opis_taksacyjny', False),
    (5, 'Zadania w zakresie gospodarki leśnej dla właścicieli',
     'Zadania_dla_wlascicieli', True),
    (6, 'Zestawienie zadań gospodarczych projektowanych do wykonania',
     'Zadania_gospodarcze', False),
    (7, 'Wykaz działek', 'Wykaz_dzialek', False),
    (8, 'Wykaz właścicieli', 'Wykaz_wlascicieli', True),
    (9, 'Wykaz zmian powierzchni leśnej w stosunku do rejestru gruntów '
        '(wzór)', 'Wykaz_zmian_powierzchni_lesnej', False),
    (10, 'Wykaz skrótów i symboli', 'Wykaz_skrotow', False),
    (11, 'Wykaz powierzchni leśnych niezalesionych',
     'Wykaz_pow_lesnych_niezalesionych', False),
    (12, 'Wykaz gruntów do zalesienia', 'Wykaz_gruntow_do_zalesienia', False),
    (13, 'Zestawienie powierzchni lasu na nieleśnych użytkach gruntowych',
     'Las_na_nielesnych_uzytkach', False),
    (14, 'Zestawienie walorów przyrodniczych', 'Walory_przyrodnicze', False),
    (15, 'Etaty', 'Etaty', False),
    (16, 'Zestawienie zabiegów hodowli lasu', 'Hodowla_lasu', False),
    (17, 'Miąższość drzewostanów zaprojektowanych do użytkowania '
         'przedrębnego', 'Uzytkowanie_przedrebne', False),
    (18, 'Zestawienie gruntów związanych z gospodarką leśną',
     'Grunty_zwiazane_z_gosp_lesna', False),
)
NAZWY = {i: n for i, n, _, _ in RAPORTY}
FOLDERY = {i: f for i, _, f, _ in RAPORTY}
OSOBOWE = {i for i, _, _, o in RAPORTY if o and i != ZESTAWIENIE}

# Zestawienie raportów: kolejność raportów i nazwy arkuszy jak w Taksatorze
ZESTAWIENIE_ARKUSZE = (
    (4, 'OT'), (1, 'TPM_FL'), (2, 'TPM_TH'), (3, 'Sheet4'), (5, 'WzUPUL'),
    (6, 'Zestawienie'), (7, 'WykazDzialek'), (8, 'WykazWlasc'),
    (10, 'Skroty'), (11, 'WykazPow'), (12, 'WykazDoZal'),
    (13, 'ZestLasNLas'), (16, 'Hodowla'), (17, 'Przedrebne'),
    (14, 'OchrPrzyrody'), (15, 'Etaty'),
)
ARKUSZE = dict(ZESTAWIENIE_ARKUSZE)
# arkusze zestawienia z danymi osobowymi - wycinane na płyty
ARKUSZE_OSOBOWE = tuple(a for i, a in ZESTAWIENIE_ARKUSZE if i in OSOBOWE)

XLSX = 51  # Excel xlOpenXMLWorkbook
KLUCZ_REJESTRU = r'SOFTWARE\TaksatorPU\x64'
KATALOG_DOMYSLNY = r'C:\Program Files\TaksatorPU'
POMOCNIK_ZRODLO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'tpu_raporty_pomocnik.cs')
_BEZ_OKNA = 0x08000000  # CREATE_NO_WINDOW


class BladPomocnika(Exception):
    """Pomocnik/Taksator zgłosił błąd."""


# Po WinError 87 (raz w sesji QGIS) programy uruchamiane przez cmd /c.
_PRZEZ_CMD = [False]


def komenda_cmd(argumenty):
    """[program, argumenty...] -> 'cmd.exe /d /s /c ""program" "arg" ..."'
    (/s - cmd zdejmuje tylko zewnętrzne cudzysłowy, każdy argument
    w swoich - spacje, polskie znaki)."""
    cmd = os.environ.get('COMSPEC') or 'cmd.exe'
    srodek = ' '.join(f'"{a}"' for a in argumenty)
    return f'"{cmd}" /d /s /c "{srodek}"'


def _start(funkcja, argumenty, **kw):
    """subprocess.run/Popen z pustym wejściem i bez okna konsoli.
    Na części komputerów (Windows 10, prawdopodobnie antywirus) QGIS nie
    może uruchomić niepodpisanego pomocnika z przekierowanym wyjściem:
    CreateProcess -> WinError 87, a przez cmd /c działa (diagnoza
    w konsoli Pythona QGIS 2026-11-23). Przy WinError 87 - ponownie przez
    cmd /c i tak już do końca sesji."""
    kw.setdefault('stdin', subprocess.DEVNULL)
    if not _PRZEZ_CMD[0]:
        try:
            return funkcja(argumenty, creationflags=_BEZ_OKNA, **kw)
        except OSError as e:
            if getattr(e, 'winerror', None) != 87:
                raise
            _PRZEZ_CMD[0] = True
    return funkcja(komenda_cmd(argumenty), creationflags=_BEZ_OKNA, **kw)


def zakoncz(proc):
    """Zabija proces razem z potomkami (przez cmd /c pomocnik jest
    potomkiem cmd - samo kill zostawiłoby go w tle)."""
    try:
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       creationflags=_BEZ_OKNA, timeout=30)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


# ------------------------------------------------------------------ nazwy

def nazwa_pliku(municip, community, nazwa):
    """'115', '0001', 'Białęgi' -> '115-0001-Białęgi' (jak w Taksatorze);
    znaki niedozwolone w nazwach plików -> '_'."""
    tekst = f'{municip}-{community}-{(nazwa or "").strip()}'.rstrip('-')
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', tekst).rstrip('. ')


def folder_raportow(baza):
    """<folder bazy>/Raporty_TPU."""
    return os.path.join(os.path.dirname(os.path.abspath(baza)),
                        FOLDER_RAPORTOW)


def obreby_z_bazy(wiersze):
    """Wiersze F_COMMUNITY (COUNTY, DISTRICT, MUNICIPALITY, COMMUNITY,
    NAME) -> [{municip, community, nazwa}] posortowane, bez powtórzeń."""
    wyn, widziane = [], set()
    for w in wiersze or []:
        municip, community = str(w[2] or '').strip(), str(w[3] or '').strip()
        if not community or (municip, community) in widziane:
            continue
        widziane.add((municip, community))
        wyn.append({'municip': municip, 'community': community,
                    'nazwa': str(w[4] or '').strip()})
    return sorted(wyn, key=lambda o: (o['municip'], o['community']))


def powtorzone_obreby(obreby):
    """Numery obrębów występujące w kilku gminach bazy - biblioteka
    Taksatora przyjmuje sam numer obrębu, więc takie raporty mogą
    obejmować obie gminy."""
    licz = {}
    for o in obreby:
        licz.setdefault(o['community'], set()).add(o['municip'])
    return sorted(c for c, g in licz.items() if len(g) > 1)


# ------------------------------------------------------------------- plan

def zaplanuj(baza, raporty, obreby, tymczasowy):
    """Plan dla wybranych raportów (id, ZESTAWIENIE = 0) i obrębów.
    Zwraca (wyniki, zadania):
      wyniki: [{raport, obreb, cel (.xlsx), zrodla: [(id, .xls)]}] -
              zestawienie ma 16 źródeł (ZESTAWIENIE_ARKUSZE), raport jedno,
      zadania: [(nr, id, community, .xls)] dla pomocnika - każdy raport
              obrębu raz (wspólny dla zestawienia i pojedynczego raportu).
    """
    kat = folder_raportow(baza)
    wyniki, xls = [], {}

    def _xls(ob, rid):
        k = (ob['municip'], ob['community'], rid)
        if k not in xls:
            xls[k] = os.path.join(
                tymczasowy, f"{ob['municip']}_{ob['community']}_{rid}.xls")
        return xls[k]

    for rid in sorted(raporty, key=lambda r: [i for i, *_ in RAPORTY]
                      .index(r)):
        for ob in obreby:
            cel = os.path.join(kat, FOLDERY[rid], nazwa_pliku(
                ob['municip'], ob['community'], ob['nazwa']) + '.xlsx')
            ids = ([i for i, _ in ZESTAWIENIE_ARKUSZE] if rid == ZESTAWIENIE
                   else [rid])
            wyniki.append({'raport': rid, 'obreb': ob, 'cel': cel,
                           'zrodla': [(i, _xls(ob, i)) for i in ids]})
    zadania = [(nr, rid, community, sc) for nr, ((_, community, rid), sc)
               in enumerate(xls.items(), 1)]
    return wyniki, zadania


def zapisz_zadania(zadania, sciezka):
    with open(sciezka, 'w', encoding='utf-8', newline='\n') as f:
        for nr, rid, community, sc in zadania:
            f.write(f'{nr}\t{rid}\t{community}\t{sc}\n')


def istniejace(wyniki):
    return [w['cel'] for w in wyniki if os.path.exists(w['cel'])]


def opis_wynikow(wyniki, bledy_zadan, bledy_excel):
    """Tekst raportu: dla każdego raportu liczba plików i błędy."""
    L = []
    for rid in dict.fromkeys(w['raport'] for w in wyniki):
        ws = [w for w in wyniki if w['raport'] == rid]
        ok = [w for w in ws if w['cel'] not in bledy_excel and
              not any(sc in bledy_zadan for _, sc in w['zrodla'])]
        L.append(f'{NAZWY[rid]} -> {FOLDER_RAPORTOW}\\{FOLDERY[rid]}: '
                 f'{len(ok)}/{len(ws)}')
        for w in ws:
            if w in ok:
                continue
            ob = w['obreb']
            opisy = [f'raport {i}: {bledy_zadan[sc]}' for i, sc in
                     w['zrodla'] if sc in bledy_zadan]
            if w['cel'] in bledy_excel:
                opisy.append(f"Excel: {bledy_excel[w['cel']]}")
            L.append(f"  BŁĄD {ob['municip']}-{ob['community']} "
                     f"{ob['nazwa']}: " + '; '.join(opisy))
    return '\n'.join(L) + '\n'


# ---------------------------------------------------------------- Taksator

def katalog_taksatora():
    """Katalog Taksatora PU z rejestru (jak instalator: HKLM\\SOFTWARE\\
    TaksatorPU\\x64, installPath), rezerwowo Program Files; None - brak
    ReportsHelper.dll."""
    kandydaci = []
    try:
        import winreg
        for widok in (winreg.KEY_WOW64_64KEY, 0):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                    KLUCZ_REJESTRU, 0,
                                    winreg.KEY_READ | widok) as k:
                    kandydaci.append(winreg.QueryValueEx(k, 'installPath')[0])
            except OSError:
                pass
    except ImportError:
        pass
    kandydaci.append(KATALOG_DOMYSLNY)
    for kat in kandydaci:
        if kat and os.path.isfile(os.path.join(kat, 'ReportsHelper.dll')):
            return kat
    return None


def kompilator():
    """csc.exe .NET Framework 4 (64-bit) z Windows; None - brak."""
    sc = os.path.join(os.environ.get('WINDIR', r'C:\Windows'),
                      'Microsoft.NET', 'Framework64', 'v4.0.30319', 'csc.exe')
    return sc if os.path.isfile(sc) else None


def katalog_pomocnika():
    baza = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    return os.path.join(baza, 'LasR', 'tpu_raporty')


def kompiluj_pomocnika(katalog=None, zrodlo=POMOCNIK_ZRODLO):
    """Pomocnik .exe w katalogu roboczym (domyślnie %LOCALAPPDATA%\\LasR\\
    tpu_raporty) - kompilowany przy pierwszym użyciu i po zmianie źródła
    (skrót SHA-1 obok). Zwraca ścieżkę .exe; BladPomocnika przy błędzie."""
    katalog = katalog or katalog_pomocnika()
    exe = os.path.join(katalog, 'tpu_raporty.exe')
    with open(zrodlo, 'rb') as f:
        skrot = hashlib.sha1(f.read()).hexdigest()
    plik_skrotu = exe + '.sha1'
    try:
        with open(plik_skrotu, encoding='ascii') as f:
            if f.read().strip() == skrot and os.path.isfile(exe):
                return exe
    except OSError:
        pass
    csc = kompilator()
    if not csc:
        raise BladPomocnika('brak kompilatora .NET Framework 4 (csc.exe)')
    os.makedirs(katalog, exist_ok=True)
    w = _start(subprocess.run, [csc, '-nologo', '-platform:x64', '-optimize',
                                f'-out:{exe}', zrodlo], capture_output=True)
    if w.returncode != 0 or not os.path.isfile(exe):
        raise BladPomocnika('kompilacja pomocnika nie powiodła się: ' +
                            _tekst(w.stdout + w.stderr).strip())
    with open(plik_skrotu, 'w', encoding='ascii') as f:
        f.write(skrot)
    return exe


def _tekst(b):
    for kod in ('utf-8', 'cp1250', 'cp852'):
        try:
            return b.decode(kod)
        except UnicodeDecodeError:
            pass
    return b.decode('utf-8', 'replace')


def parsuj(linia):
    """'OK\\t3' -> ('OK', '3', ''); 'BLAD\\t3\\topis' -> ('BLAD', '3',
    'opis'); inne -> (pierwsze pole, reszta...)."""
    p = linia.rstrip('\r\n').split('\t')
    return tuple(p + [''] * (3 - len(p)))


def _polecenie(exe, taksator, *argumenty, timeout=600):
    w = _start(subprocess.run, [exe, taksator] + list(argumenty),
               capture_output=True, timeout=timeout)
    linie = _tekst(w.stdout).splitlines()
    for linia in linie:
        p = parsuj(linia)
        if p[0] == 'BLAD':
            raise BladPomocnika(p[2] or p[1])
    if w.returncode != 0:
        raise BladPomocnika(_tekst(w.stdout + w.stderr).strip() or
                            f'kod wyjścia {w.returncode}')
    return [parsuj(x) for x in linie]


def lista_raportow(exe, taksator):
    """{id: nazwa} z biblioteki Taksatora."""
    return {int(p[1]): p[2] for p in _polecenie(exe, taksator, 'lista')
            if p[0] == 'RAPORT'}


def wersja_bazy(exe, taksator, baza):
    """(wersja bazy, wersja wymagana przez Taksatora)."""
    for p in _polecenie(exe, taksator, 'wersja', baza):
        if p[0] == 'WERSJA':
            return int(p[1]), int(p[2])
    raise BladPomocnika('pomocnik nie podał wersji bazy')


def aktualizuj_baze(exe, taksator, baza):
    """Aktualizacja struktury bazy procedurą Taksatora - TYLKO kopia.
    Zwraca (przed, po)."""
    for p in _polecenie(exe, taksator, 'aktualizuj', baza):
        if p[0] == 'WERSJA':
            return int(p[1]), int(p[2])
    raise BladPomocnika('pomocnik nie podał wersji bazy')


def proces_raportow(exe, taksator, baza, plik_zadan):
    """Popen pomocnika generującego raporty (stdout: OK/BLAD <nr> ...)."""
    return _start(subprocess.Popen,
                  [exe, taksator, 'raporty', baza, plik_zadan],
                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


# ------------------------------------------------------------------- Excel

class Excel:
    """Excel w tle (with Excel() as xl: ...), zamykany na końcu."""

    def __enter__(self):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        self.app = win32com.client.DispatchEx('Excel.Application')
        self.app.Visible = False
        self.app.DisplayAlerts = False
        self.app.ScreenUpdating = False
        return self

    def __exit__(self, *_):
        try:
            for wb in list(self.app.Workbooks):
                wb.Close(False)
        except Exception:
            pass
        try:
            self.app.Quit()
        except Exception:
            pass
        self.app = None
        return False

    def _otworz(self, sc):
        return self.app.Workbooks.Open(os.path.abspath(sc), 0, True)

    def _zapisz(self, wb, cel):
        cel = os.path.abspath(cel)
        os.makedirs(os.path.dirname(cel), exist_ok=True)
        if os.path.exists(cel):
            os.remove(cel)
        wb.SaveAs(cel, XLSX)

    def zapisz_xlsx(self, xls, cel):
        """Pojedynczy raport .xls -> .xlsx."""
        wb = self._otworz(xls)
        try:
            self._zapisz(wb, cel)
        finally:
            wb.Close(False)

    def zloz(self, zrodla, cel):
        """Zestawienie: pierwsze arkusze plików [(id, .xls)] jako kolejne
        arkusze jednego .xlsx, nazwy arkuszy z ARKUSZE."""
        wb = self.app.Workbooks.Add()
        try:
            puste = wb.Worksheets.Count
            for rid, sc in zrodla:
                zr = self._otworz(sc)
                try:
                    zr.Worksheets(1).Copy(None, wb.Sheets(wb.Sheets.Count))
                finally:
                    zr.Close(False)
                wb.Sheets(wb.Sheets.Count).Name = ARKUSZE.get(rid, str(rid))
            for _ in range(puste):
                wb.Sheets(1).Delete()
            wb.Sheets(1).Activate()
            self._zapisz(wb, cel)
        finally:
            wb.Close(False)


# -------------------------------------------------------------------- płyty

def raporty_na_plyte(folder, municip, communities):
    """Raporty TPU części na płytę: z <folder>/Raporty_TPU, pliki
    <MUNICIP>-<obręb>-*.xlsx obrębów części, bez raportów z danymi
    osobowymi (3, 5, 8); Zestawienie raportów - z wyciętymi arkuszami
    ARKUSZE_OSOBOWE. Zwraca [(źródło, ścieżka względna w folderze
    Raporty, arkusze do wycięcia)]."""
    kat = os.path.join(folder, FOLDER_RAPORTOW)
    wzor = re.compile(r'^%s-(\d+)-.*\.xlsx$' % re.escape(municip),
                      re.IGNORECASE)
    obr = set(communities)
    wyn = []
    for rid, _, podf, _ in RAPORTY:
        if rid in OSOBOWE:
            continue
        try:
            pliki = sorted(os.listdir(os.path.join(kat, podf)))
        except OSError:
            continue
        for p in pliki:
            m = wzor.match(p)
            if m and m.group(1) in obr and not p.startswith('~$'):
                wyn.append((os.path.join(kat, podf, p),
                            os.path.join(podf, p),
                            ARKUSZE_OSOBOWE if rid == ZESTAWIENIE else ()))
    return wyn


def kopiuj_bez_arkuszy(zrodlo, cel, arkusze):
    """Kopia .xlsx bez podanych arkuszy (openpyxl; reszta bez zmian).
    Bez arkuszy do wycięcia - zwykła kopia."""
    os.makedirs(os.path.dirname(cel), exist_ok=True)
    if not arkusze:
        shutil.copy2(zrodlo, cel)
        return
    import openpyxl
    wb = openpyxl.load_workbook(zrodlo)
    for a in arkusze:
        if a in wb.sheetnames:
            wb.remove(wb[a])
    if not wb.sheetnames:
        raise ValueError('po wycięciu danych osobowych nie zostaje żaden '
                         'arkusz')
    wb.active = 0
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = False
    wb.worksheets[0].sheet_view.tabSelected = True
    wb.save(cel)
