let SessionLoad = 1
if &cp | set nocp | endif
let s:so_save = &so | let s:siso_save = &siso | set so=0 siso=0
let v:this_session=expand("<sfile>:p")
silent only
silent tabonly
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty
if expand('%') == '' && !&modified && line('$') <= 1 && getline(1) == ''
  let s:wipebuf = bufnr('%')
endif
set shortmess=aoO
argglobal
%argdel
edit ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_usun_op.py
set splitbelow splitright
wincmd _ | wincmd |
vsplit
1wincmd h
wincmd w
set nosplitbelow
wincmd t
set winminheight=0
set winheight=1
set winminwidth=0
set winwidth=1
exe 'vert 1resize ' . ((&columns * 125 + 125) / 250)
exe 'vert 2resize ' . ((&columns * 124 + 125) / 250)
argglobal
setlocal fdm=indent
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=2
setlocal fen
10
normal! zo
11
normal! zo
16
normal! zo
24
normal! zo
32
normal! zo
34
normal! zo
40
normal! zo
51
normal! zo
58
normal! zo
let s:l = 50 - ((48 * winheight(0) + 32) / 64)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
50
normal! 025|
wincmd w
argglobal
if bufexists("~/lasr/lch/lch/SKRYPTY/usunOP.py") | buffer ~/lasr/lch/lch/SKRYPTY/usunOP.py | else | edit ~/lasr/lch/lch/SKRYPTY/usunOP.py | endif
setlocal fdm=indent
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=2
setlocal fml=1
setlocal fdn=2
setlocal fen
16
normal! zo
let s:l = 58 - ((50 * winheight(0) + 32) / 64)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
58
normal! 030|
wincmd w
exe 'vert 1resize ' . ((&columns * 125 + 125) / 250)
exe 'vert 2resize ' . ((&columns * 124 + 125) / 250)
tabnext 1
badd +0 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_usun_op.py
badd +1 ~/lasr/lch/lch/SKRYPTY/usunOP.py
badd +678 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_wyszukaj_lz.py
badd +120 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_spr_wlasn_wydz.py
badd +189 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/testy/test_przetworzenia_bazy.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_dopisz_fochr.py
badd +30 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_dopisz_kody.py
badd +53 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_przygCiecie.py
badd +9 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdzenia_warstw.py
badd +58 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/spr_wydzielen.py
badd +2 ~/lasr/LasR-NAKLEJKI/naklejki.py
badd +1102 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/naklejki.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_numeruj.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_literkuj.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/testy/test_polaczen_do_bazy.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/pw.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_eksport_kml.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_dopOddzWydz.py
badd +212 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_sprWydzOddz.py
badd +24 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_sprawdz_rozl.py
badd +81 ~/lasr/lch/lch/SKRYPTY/dopisz_wydz_do_bazy_nowe.py
badd +114 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przeliterkuj.py
badd +4 ~/lasr/lch/lch/SKRYPTY/kopiuj_wydz.py
badd +328 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_rozlicz_pow_wydz.py
badd +205 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_dopisz_wydz.py
badd +526 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_klonuj_wydz.py
badd +3 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/.git/COMMIT_EDITMSG
badd +74 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdz_dzkat.py
badd +60 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_symbolizacja.py
badd +250 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/funkcje.py
if exists('s:wipebuf') && len(win_findbuf(s:wipebuf)) == 0
  silent exe 'bwipe ' . s:wipebuf
endif
unlet! s:wipebuf
set winheight=1 winwidth=20 shortmess=filnxtToOc
set winminheight=1 winminwidth=1
let s:sx = expand("<sfile>:p:r")."x.vim"
if file_readable(s:sx)
  exe "source " . fnameescape(s:sx)
endif
let &so = s:so_save | let &siso = s:siso_save
nohlsearch
doautoall SessionLoadPost
unlet SessionLoad
" vim: set ft=vim :
