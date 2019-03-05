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
edit ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_wyszukaj_lz.py
set splitbelow splitright
wincmd _ | wincmd |
vsplit
wincmd _ | wincmd |
vsplit
2wincmd h
wincmd w
wincmd w
set nosplitbelow
wincmd t
set winminheight=0
set winheight=1
set winminwidth=0
set winwidth=1
exe 'vert 1resize ' . ((&columns * 83 + 125) / 250)
exe 'vert 2resize ' . ((&columns * 82 + 125) / 250)
exe 'vert 3resize ' . ((&columns * 83 + 125) / 250)
argglobal
setlocal fdm=indent
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=2
setlocal fen
let s:l = 1 - ((0 * winheight(0) + 32) / 64)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
1
normal! 0
wincmd w
argglobal
if bufexists("~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py") | buffer ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py | else | edit ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py | endif
setlocal fdm=indent
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=2
setlocal fen
let s:l = 1 - ((0 * winheight(0) + 32) / 64)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
1
normal! 0
wincmd w
argglobal
if bufexists("~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py") | buffer ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py | else | edit ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py | endif
setlocal fdm=indent
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=2
setlocal fen
let s:l = 1 - ((0 * winheight(0) + 32) / 64)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
1
normal! 0
wincmd w
3wincmd w
exe 'vert 1resize ' . ((&columns * 83 + 125) / 250)
exe 'vert 2resize ' . ((&columns * 82 + 125) / 250)
exe 'vert 3resize ' . ((&columns * 83 + 125) / 250)
tabnext 1
badd +2 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_wyszukaj_lz.py
badd +55 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_spr_wlasn_wydz.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/testy/test_przetworzenia_bazy.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_dopisz_fochr.py
badd +30 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_dopisz_kody.py
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/shp_przygCiecie.py
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
badd +78 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_rozlicz_pow_wydz.py
badd +205 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_dopisz_wydz.py
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
