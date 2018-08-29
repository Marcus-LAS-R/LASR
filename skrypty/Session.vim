let SessionLoad = 1
if &cp | set nocp | endif
let s:cpo_save=&cpo
set cpo&vim
imap <Nul> <C-Space>
inoremap <expr> <Up> pumvisible() ? "\" : "\<Up>"
inoremap <expr> <Down> pumvisible() ? "\" : "\<Down>"
inoremap <expr> <S-Tab> pumvisible() ? "\" : "\<S-Tab>"
inoremap <Plug>(emmet-anchorize-summary) =emmet#util#closePopup()=emmet#anchorizeURL(1)
inoremap <Plug>(emmet-anchorize-url) =emmet#util#closePopup()=emmet#anchorizeURL(0)
inoremap <Plug>(emmet-remove-tag) =emmet#util#closePopup()=emmet#removeTag()
inoremap <Plug>(emmet-split-join-tag) :call emmet#splitJoinTag()
inoremap <Plug>(emmet-toggle-comment) =emmet#util#closePopup()=emmet#toggleComment()
inoremap <Plug>(emmet-image-size) =emmet#util#closePopup()=emmet#imageSize()
inoremap <Plug>(emmet-move-prev-item) :call emmet#moveNextPrevItem(1)
inoremap <Plug>(emmet-move-next-item) :call emmet#moveNextPrevItem(0)
inoremap <Plug>(emmet-move-prev) :call emmet#moveNextPrev(1)
inoremap <Plug>(emmet-move-next) :call emmet#moveNextPrev(0)
inoremap <Plug>(emmet-balance-tag-outword) :call emmet#balanceTag(-1)
inoremap <Plug>(emmet-balance-tag-inward) :call emmet#balanceTag(1)
inoremap <Plug>(emmet-update-tag) =emmet#util#closePopup()=emmet#updateTag()
inoremap <Plug>(emmet-expand-word) =emmet#util#closePopup()=emmet#expandAbbr(1,"")
inoremap <Plug>(emmet-expand-abbr) =emmet#util#closePopup()=emmet#expandAbbr(0,"")
inoremap <silent> <Plug>snipMateShow =snipMate#ShowAvailableSnips()
inoremap <silent> <Plug>snipMateBack =snipMate#BackwardsSnippet()
inoremap <silent> <Plug>snipMateTrigger =snipMate#TriggerSnippet(1)
inoremap <silent> <Plug>snipMateNextOrTrigger =snipMate#TriggerSnippet()
inoremap <silent> <Plug>NERDCommenterInsert  <BS>:call NERDComment('i', "insert")
map  h
xmap 	 <Plug>snipMateVisual
smap 	 <Plug>snipMateNextOrTrigger
map <NL> j
map  k
map  l
vnoremap  :nohl
nnoremap  :nohl
onoremap  :nohl
nmap a _|
vmap c <Plug>(emmet-code-pretty)
vmap m <Plug>(emmet-merge-lines)
nmap A <Plug>(emmet-anchorize-summary)
nmap a <Plug>(emmet-anchorize-url)
nmap k <Plug>(emmet-remove-tag)
nmap j <Plug>(emmet-split-join-tag)
nmap / <Plug>(emmet-toggle-comment)
nmap i <Plug>(emmet-image-size)
nmap N <Plug>(emmet-move-prev)
nmap n <Plug>(emmet-move-next)
vmap D <Plug>(emmet-balance-tag-outword)
nmap D <Plug>(emmet-balance-tag-outword)
vmap d <Plug>(emmet-balance-tag-inward)
nmap d <Plug>(emmet-balance-tag-inward)
nmap u <Plug>(emmet-update-tag)
nmap ; <Plug>(emmet-expand-word)
vmap , <Plug>(emmet-expand-abbr)
nmap , <Plug>(emmet-expand-abbr)
vnoremap  :update
nnoremap  :update
onoremap  :update
nmap <silent> # <Plug>MarkSearchPrev
nnoremap <silent> '[ :call signature#mark#Goto("prev", "line", "alpha")
nnoremap <silent> '] :call signature#mark#Goto("next", "line", "alpha")
nmap <silent> * <Plug>MarkSearchNext
nnoremap ,d :YcmShowDetailedDiagnostic
nmap <silent> ,? <Plug>MarkSearchAnyPrev
nmap <silent> ,/ <Plug>MarkSearchAnyNext
nmap <silent> ,# <Plug>MarkSearchCurrentPrev
nmap <silent> ,* <Plug>MarkSearchCurrentNext
nmap <silent> ,n <Plug>MarkClear
vmap <silent> ,r <Plug>MarkRegex
nmap <silent> ,r <Plug>MarkRegex
vmap <silent> ,m <Plug>MarkSet
nmap <silent> ,m <Plug>MarkSet
nmap ,ca <Plug>NERDCommenterAltDelims
xmap ,cu <Plug>NERDCommenterUncomment
nmap ,cu <Plug>NERDCommenterUncomment
xmap ,cb <Plug>NERDCommenterAlignBoth
nmap ,cb <Plug>NERDCommenterAlignBoth
xmap ,cl <Plug>NERDCommenterAlignLeft
nmap ,cl <Plug>NERDCommenterAlignLeft
nmap ,cA <Plug>NERDCommenterAppend
xmap ,cy <Plug>NERDCommenterYank
nmap ,cy <Plug>NERDCommenterYank
xmap ,cs <Plug>NERDCommenterSexy
nmap ,cs <Plug>NERDCommenterSexy
xmap ,ci <Plug>NERDCommenterInvert
nmap ,ci <Plug>NERDCommenterInvert
nmap ,c$ <Plug>NERDCommenterToEOL
xmap ,cn <Plug>NERDCommenterNested
nmap ,cn <Plug>NERDCommenterNested
xmap ,cm <Plug>NERDCommenterMinimal
nmap ,cm <Plug>NERDCommenterMinimal
xmap ,c  <Plug>NERDCommenterToggle
nmap ,c  <Plug>NERDCommenterToggle
xmap ,cc <Plug>NERDCommenterComment
nmap ,cc <Plug>NERDCommenterComment
map ,g :call RopeGotoDefinition()
nmap ,t :NERDTree
nmap ,a :Ag!
nnoremap ,s :mksession!
nmap <silent> ,sv :so $MYVIMRC
nnoremap ,ev :vsp ~/.vim/vimrc
nnoremap ,u :GundoToggle
nnoremap ,z :%s#\<=expand("<cword>")\>#
vnoremap ,e :call ToggleNumber()
nnoremap ,e :call ToggleNumber()
nmap ,T :enew
nmap ,h :bprevious
nmap ,l :bnext
map ; :
vnoremap < <gv
nnoremap < <<_
vnoremap > >gv			
nnoremap > >>_
nnoremap Q <Nop>
xmap S <Plug>VSurround
nnoremap <silent> [= :call signature#marker#Goto("prev", "any",  v:count)
nnoremap <silent> [- :call signature#marker#Goto("prev", "same", v:count)
nnoremap <silent> [` :call signature#mark#Goto("prev", "spot", "pos")
nnoremap <silent> [' :call signature#mark#Goto("prev", "line", "pos")
nnoremap <silent> [  :put! =repeat(nr2char(10), v:count1)
nnoremap <silent> ]= :call signature#marker#Goto("next", "any",  v:count)
nnoremap <silent> ]- :call signature#marker#Goto("next", "same", v:count)
nnoremap <silent> ]` :call signature#mark#Goto("next", "spot", "pos")
nnoremap <silent> ]' :call signature#mark#Goto("next", "line", "pos")
nnoremap <silent> ]  :put =repeat(nr2char(10), v:count1)
nnoremap <silent> `[ :call signature#mark#Goto("prev", "spot", "alpha")
nnoremap <silent> `] :call signature#mark#Goto("next", "spot", "alpha")
nmap cS <Plug>CSurround
nmap cs <Plug>Csurround
nmap ds <Plug>Dsurround
nnoremap <silent> dm :call signature#utils#Remove(v:count)
vmap gx <Plug>NetrwBrowseXVis
nmap gx <Plug>NetrwBrowseX
xmap gS <Plug>VgSurround
nnoremap gQ <Nop>
vnoremap jk 
nnoremap j gj
nnoremap k gk
nnoremap <silent> m? :call signature#marker#List(v:count, 0)
nnoremap <silent> m/ :call signature#mark#List(0, 0)
nnoremap <silent> m<BS> :call signature#marker#Purge()
nnoremap <silent> m  :call signature#mark#Purge("all")
nnoremap <silent> m- :call signature#mark#Purge("line")
nnoremap <silent> m. :call signature#mark#ToggleAtLine()
nnoremap <silent> m, :call signature#mark#Toggle("next")
nnoremap <silent> m :call signature#utils#Input()
nmap ySS <Plug>YSsurround
nmap ySs <Plug>YSsurround
nmap yss <Plug>Yssurround
nmap yS <Plug>YSurround
nmap ys <Plug>Ysurround
nnoremap <SNR>86_: :=v:count ? v:count : ''
smap <S-Tab> <Plug>snipMateBack
vnoremap <silent> <Plug>NetrwBrowseXVis :call netrw#BrowseXVis()
nnoremap <silent> <Plug>NetrwBrowseX :call netrw#BrowseX(expand((exists("g:netrw_gx")? g:netrw_gx : '<cfile>')),netrw#CheckIfRemote())
vnoremap <Plug>(emmet-code-pretty) :call emmet#codePretty()
vnoremap <Plug>(emmet-merge-lines) :call emmet#mergeLines()
nnoremap <Plug>(emmet-anchorize-summary) :call emmet#anchorizeURL(1)
nnoremap <Plug>(emmet-anchorize-url) :call emmet#anchorizeURL(0)
nnoremap <Plug>(emmet-remove-tag) :call emmet#removeTag()
nnoremap <Plug>(emmet-split-join-tag) :call emmet#splitJoinTag()
nnoremap <Plug>(emmet-toggle-comment) :call emmet#toggleComment()
nnoremap <Plug>(emmet-image-size) :call emmet#imageSize()
nnoremap <Plug>(emmet-move-prev-item) :call emmet#moveNextPrevItem(1)
nnoremap <Plug>(emmet-move-next-item) :call emmet#moveNextPrevItem(0)
nnoremap <Plug>(emmet-move-prev) :call emmet#moveNextPrev(1)
nnoremap <Plug>(emmet-move-next) :call emmet#moveNextPrev(0)
vnoremap <Plug>(emmet-balance-tag-outword) :call emmet#balanceTag(-2)
nnoremap <Plug>(emmet-balance-tag-outword) :call emmet#balanceTag(-1)
vnoremap <Plug>(emmet-balance-tag-inward) :call emmet#balanceTag(2)
nnoremap <Plug>(emmet-balance-tag-inward) :call emmet#balanceTag(1)
nnoremap <Plug>(emmet-update-tag) :call emmet#updateTag()
nnoremap <Plug>(emmet-expand-word) :call emmet#expandAbbr(1,"")
vnoremap <Plug>(emmet-expand-abbr) :call emmet#expandAbbr(2,"")
nnoremap <Plug>(emmet-expand-abbr) :call emmet#expandAbbr(3,"")
nnoremap <silent> <Plug>SurroundRepeat .
snoremap <silent> <Plug>snipMateBack a=snipMate#BackwardsSnippet()
snoremap <silent> <Plug>snipMateNextOrTrigger a=snipMate#TriggerSnippet()
nnoremap <silent> <Plug>MarkSearchPrev :if !mark#SearchNext(1)|execute 'normal! #zv'|endif
nnoremap <silent> <Plug>MarkSearchNext :if !mark#SearchNext(0)|execute 'normal! *zv'|endif
nnoremap <silent> <Plug>MarkSearchAnyPrev :call mark#SearchAnyMark(1)
nnoremap <silent> <Plug>MarkSearchAnyNext :call mark#SearchAnyMark(0)
nnoremap <silent> <Plug>MarkSearchCurrentPrev :call mark#SearchCurrentMark(1)
nnoremap <silent> <Plug>MarkSearchCurrentNext :call mark#SearchCurrentMark(0)
nnoremap <silent> <Plug>MarkToggle :call mark#Toggle()
nnoremap <silent> <Plug>MarkAllClear :call mark#ClearAll()
nnoremap <silent> <Plug>MarkClear :call mark#DoMark(mark#CurrentMark()[0])
vnoremap <silent> <Plug>MarkRegex :call mark#MarkRegex(mark#GetVisualSelectionAsRegexp())
nnoremap <silent> <Plug>MarkRegex :call mark#MarkRegex('')
vnoremap <silent> <Plug>MarkSet :call mark#DoMark(mark#GetVisualSelectionAsLiteralPattern())
nnoremap <silent> <Plug>MarkSet :call mark#MarkCurrentWord()
xnoremap <silent> <Plug>NERDCommenterUncomment :call NERDComment("x", "Uncomment")
nnoremap <silent> <Plug>NERDCommenterUncomment :call NERDComment("n", "Uncomment")
xnoremap <silent> <Plug>NERDCommenterAlignBoth :call NERDComment("x", "AlignBoth")
nnoremap <silent> <Plug>NERDCommenterAlignBoth :call NERDComment("n", "AlignBoth")
xnoremap <silent> <Plug>NERDCommenterAlignLeft :call NERDComment("x", "AlignLeft")
nnoremap <silent> <Plug>NERDCommenterAlignLeft :call NERDComment("n", "AlignLeft")
nnoremap <silent> <Plug>NERDCommenterAppend :call NERDComment("n", "Append")
xnoremap <silent> <Plug>NERDCommenterYank :call NERDComment("x", "Yank")
nnoremap <silent> <Plug>NERDCommenterYank :call NERDComment("n", "Yank")
xnoremap <silent> <Plug>NERDCommenterSexy :call NERDComment("x", "Sexy")
nnoremap <silent> <Plug>NERDCommenterSexy :call NERDComment("n", "Sexy")
xnoremap <silent> <Plug>NERDCommenterInvert :call NERDComment("x", "Invert")
nnoremap <silent> <Plug>NERDCommenterInvert :call NERDComment("n", "Invert")
nnoremap <silent> <Plug>NERDCommenterToEOL :call NERDComment("n", "ToEOL")
xnoremap <silent> <Plug>NERDCommenterNested :call NERDComment("x", "Nested")
nnoremap <silent> <Plug>NERDCommenterNested :call NERDComment("n", "Nested")
xnoremap <silent> <Plug>NERDCommenterMinimal :call NERDComment("x", "Minimal")
nnoremap <silent> <Plug>NERDCommenterMinimal :call NERDComment("n", "Minimal")
xnoremap <silent> <Plug>NERDCommenterToggle :call NERDComment("x", "Toggle")
nnoremap <silent> <Plug>NERDCommenterToggle :call NERDComment("n", "Toggle")
xnoremap <silent> <Plug>NERDCommenterComment :call NERDComment("x", "Comment")
nnoremap <silent> <Plug>NERDCommenterComment :call NERDComment("n", "Comment")
nnoremap <silent> <F8> :TlistToggle 
imap S <Plug>ISurround
imap s <Plug>Isurround
inoremap <expr> 	 pumvisible() ? "\" : "\	"
inoremap <silent> <NL> =OmniPopup('j')
inoremap <silent>  =OmniPopup('k')
inoremap  :nohl
imap 	 <Plug>snipMateShow
imap  <Plug>Isurround
imap A <Plug>(emmet-anchorize-summary)
imap a <Plug>(emmet-anchorize-url)
imap k <Plug>(emmet-remove-tag)
imap j <Plug>(emmet-split-join-tag)
imap / <Plug>(emmet-toggle-comment)
imap i <Plug>(emmet-image-size)
imap N <Plug>(emmet-move-prev)
imap n <Plug>(emmet-move-next)
imap D <Plug>(emmet-balance-tag-outword)
imap d <Plug>(emmet-balance-tag-inward)
imap u <Plug>(emmet-update-tag)
imap ; <Plug>(emmet-expand-word)
imap , <Plug>(emmet-expand-abbr)
inoremap  :update
imap ,	 <Plug>snipMateNextOrTrigger
imap ,{ {}i
imap ,[ []i
imap ,( ()i
imap ," ""i
imap ,' ''i
inoremap jk 
let &cpo=s:cpo_save
unlet s:cpo_save
set autochdir
set background=dark
set backspace=2
set backupdir=~/.cache/vim/backup//
set completefunc=youcompleteme#CompleteFunc
set completeopt=menuone
set diffopt=filler,vertical
set directory=~/.cache/vim/swap//
set expandtab
set fileencodings=ucs-bom,utf-8,default,latin1
set helplang=pl
set hidden
set history=1000
set incsearch
set laststatus=2
set listchars=tab:>-,trail:·,eol:¬,space:␣
set mouse=a
set pastetoggle=<F2>
set pyxversion=3
set ruler
set runtimepath=~/.vim,~/.vim/bundle/Vundle.vim,~/.vim/bundle/vim-fugitive,~/.vim/bundle/YouCompleteMe,~/.vim/bundle/vim-airline,~/.vim/bundle/nerdtree,~/.vim/bundle/python-mode,~/.vim/bundle/nerdcommenter,~/.vim/bundle/vim-signature,~/.vim/bundle/Mark--Karkat,~/.vim/bundle/indentLine,~/.vim/bundle/vim-addon-mw-utils,~/.vim/bundle/tlib_vim,~/.vim/bundle/ag.vim,~/.vim/bundle/vim-snipmate,~/.vim/bundle/vim-snippets,~/.vim/bundle/vim-surround,~/.vim/bundle/vim-airline-themes,~/.vim/bundle/gundo.vim,~/.vim/bundle/vim-virtualenv,~/.vim/bundle/vim-notes,~/.vim/bundle/vim-misc,~/.vim/bundle/vim-jsbeautify,~/.vim/bundle/emmet-vim,~/.vim/bundle/typescript-vim,~/.vim/bundle/vim-coloresque,~/.vim/bundle/vim-sqlformat,/usr/share/vim/vimfiles,/usr/share/vim/vim81,/usr/share/vim/vimfiles/after,~/.vim/after,~/.vim/bundle/Vundle.vim,~/.vim/bundle/Vundle.vim/after,~/.vim/bundle/vim-fugitive/after,~/.vim/bundle/YouCompleteMe/after,~/.vim/bundle/vim-airline/after,~/.vim/bundle/nerdtree/after,~/.vim/bundle/python-mode/after,~/.vim/bundle/nerdcommenter/after,~/.vim/bundle/vim-signature/after,~/.vim/bundle/Mark--Karkat/after,~/.vim/bundle/indentLine/after,~/.vim/bundle/vim-addon-mw-utils/after,~/.vim/bundle/tlib_vim/after,~/.vim/bundle/ag.vim/after,~/.vim/bundle/vim-snipmate/after,~/.vim/bundle/vim-snippets/after,~/.vim/bundle/vim-surround/after,~/.vim/bundle/vim-airline-themes/after,~/.vim/bundle/gundo.vim/after,~/.vim/bundle/vim-virtualenv/after,~/.vim/bundle/vim-notes/after,~/.vim/bundle/vim-misc/after,~/.vim/bundle/vim-jsbeautify/after,~/.vim/bundle/emmet-vim/after,~/.vim/bundle/typescript-vim/after,~/.vim/bundle/vim-coloresque/after,~/.vim/bundle/vim-sqlformat/after
set scrolloff=5
set shiftround
set shiftwidth=4
set shortmess=filnxtToOc
set showmatch
set noshowmode
set showtabline=2
set splitright
set suffixes=.bak,~,.o,.info,.swp,.aux,.bbl,.blg,.brf,.cb,.dvi,.idx,.ilg,.ind,.inx,.jpg,.log,.out,.png,.toc
set noswapfile
set tabline=%!airline#extensions#tabline#get()
set tabstop=4
set undodir=~/.cache/vim/undo//
set wildignore=.DS_Store,.git/**,tmp/**,*.log,.bundle/**,node_modules/**,tags,*.rbc,.rbx,*.scssc,*.sassc,.sass-cache,*.pyc,*.gem,*.jpg,*.jpeg,*.tiff,*.gif,*.png,*.svg,*.psd,*.pdf
set wildmenu
set nowritebackup
let s:so_save = &so | let s:siso_save = &siso | set so=0 siso=0
let v:this_session=expand("<sfile>:p")
silent only
silent tabonly
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty
if expand('%') == '' && !&modified && line('$') <= 1 && getline(1) == ''
  let s:wipebuf = bufnr('%')
endif
set shortmess=aoO
badd +1 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/las_r.py
badd +6 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_wrapper.py
badd +93 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdz_ls.py
badd +143 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdz_dzkat.py
badd +75 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/baza_przetworz.py
argglobal
silent! argdel *
$argadd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/las_r.py
edit ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdz_dzkat.py
set splitbelow splitright
wincmd _ | wincmd |
vsplit
1wincmd h
wincmd w
wincmd _ | wincmd |
split
1wincmd k
wincmd w
set nosplitbelow
wincmd t
set winminheight=0
set winheight=1
set winminwidth=0
set winwidth=1
exe 'vert 1resize ' . ((&columns * 105 + 105) / 211)
exe '2resize ' . ((&lines * 40 + 25) / 50)
exe 'vert 2resize ' . ((&columns * 105 + 105) / 211)
exe '3resize ' . ((&lines * 6 + 25) / 50)
exe 'vert 3resize ' . ((&columns * 105 + 105) / 211)
argglobal
noremap <buffer> <silent> ra :PymodeRopeAutoImport
noremap <buffer> <silent> r1p :call pymode#rope#module_to_package()
noremap <buffer> <silent> rnc :call pymode#rope#generate_class()
noremap <buffer> <silent> rnp :call pymode#rope#generate_package()
noremap <buffer> <silent> rnf :call pymode#rope#generate_function()
noremap <buffer> <silent> ru :call pymode#rope#use_function()
noremap <buffer> <silent> rs :call pymode#rope#signature()
noremap <buffer> <silent> rv :call pymode#rope#move()
noremap <buffer> <silent> ri :call pymode#rope#inline()
vnoremap <buffer> <silent> rl :call pymode#rope#extract_variable()
vnoremap <buffer> <silent> rm :call pymode#rope#extract_method()
noremap <buffer> <silent> r1r :call pymode#rope#rename_module()
noremap <buffer> <silent> rr :call pymode#rope#rename()
noremap <buffer> <silent> ro :call pymode#rope#organize_imports()
noremap <buffer> <silent> f :call pymode#rope#find_it()
noremap <buffer> <silent> d :call pymode#rope#show_doc()
noremap <buffer> <silent> ,g :call pymode#rope#goto_definition()
vnoremap <buffer> <silent> ,r :PymodeRun
nnoremap <buffer> <silent> ,r :PymodeRun
onoremap <buffer> C :call pymode#motion#select('^\s*class\s', 0)
vnoremap <buffer> <silent> K :call pymode#doc#show(@*)
nnoremap <buffer> <silent> K :call pymode#doc#find()
onoremap <buffer> M :call pymode#motion#select('^\s*def\s', 0)
onoremap <buffer> [C :call pymode#motion#move('\v^(class|def)\s', 'b')
nnoremap <buffer> [C :call pymode#motion#move('\v^(class|def)\s', 'b')
vnoremap <buffer> [M :call pymode#motion#vmove('^\s*def\s', 'b')
vnoremap <buffer> [[ :call pymode#motion#vmove('\v^(class|def)\s', 'b')
onoremap <buffer> [M :call pymode#motion#move('^\s*def\s', 'b')
onoremap <buffer> [[ :call pymode#motion#move('\v^(class|def)\s', 'b')
nnoremap <buffer> [M :call pymode#motion#move('^\s*def\s', 'b')
nnoremap <buffer> [[ :call pymode#motion#move('\v^(class|def)\s', 'b')
onoremap <buffer> ]C :call pymode#motion#move('\v^(class|def)\s', '')
nnoremap <buffer> ]C :call pymode#motion#move('\v^(class|def)\s', '')
vnoremap <buffer> ]M :call pymode#motion#vmove('^\s*def\s', '')
vnoremap <buffer> ]] :call pymode#motion#vmove('\v^(class|def)\s', '')
onoremap <buffer> ]M :call pymode#motion#move('^\s*def\s', '')
onoremap <buffer> ]] :call pymode#motion#move('\v^(class|def)\s', '')
nnoremap <buffer> ]M :call pymode#motion#move('^\s*def\s', '')
nnoremap <buffer> ]] :call pymode#motion#move('\v^(class|def)\s', '')
vnoremap <buffer> aM :call pymode#motion#select('^\s*def\s', 0)
onoremap <buffer> aM :call pymode#motion#select('^\s*def\s', 0)
vnoremap <buffer> aC :call pymode#motion#select('^\s*class\s', 0)
onoremap <buffer> aC :call pymode#motion#select('^\s*class\s', 0)
vnoremap <buffer> iM :call pymode#motion#select('^\s*def\s', 1)
onoremap <buffer> iM :call pymode#motion#select('^\s*def\s', 1)
vnoremap <buffer> iC :call pymode#motion#select('^\s*class\s', 1)
onoremap <buffer> iC :call pymode#motion#select('^\s*class\s', 1)
setlocal keymap=
setlocal noarabic
setlocal autoindent
setlocal backupcopy=
setlocal balloonexpr=
setlocal nobinary
setlocal nobreakindent
setlocal breakindentopt=
setlocal bufhidden=
setlocal buflisted
setlocal buftype=
setlocal nocindent
setlocal cinkeys=0{,0},0),:,!^F,o,O,e
setlocal cinoptions=
setlocal cinwords=if,else,while,do,for,switch
set colorcolumn=80
setlocal colorcolumn=+1
setlocal comments=b:#,fb:-
setlocal commentstring=#\ %s
setlocal complete=.,w,b,u,t,i
setlocal concealcursor=inc
setlocal conceallevel=2
setlocal completefunc=youcompleteme#CompleteFunc
setlocal nocopyindent
setlocal cryptmethod=
setlocal nocursorbind
setlocal nocursorcolumn
set cursorline
setlocal cursorline
setlocal define=^s*\\(def\\|class\\)
setlocal dictionary=
setlocal nodiff
setlocal equalprg=
setlocal errorformat=
setlocal expandtab
if &filetype != 'python'
setlocal filetype=python
endif
setlocal fixendofline
setlocal foldcolumn=0
setlocal foldenable
setlocal foldexpr=0
setlocal foldignore=#
setlocal foldlevel=2
setlocal foldmarker={{{,}}}
set foldmethod=indent
setlocal foldmethod=indent
setlocal foldminlines=1
set foldnestmax=2
setlocal foldnestmax=2
setlocal foldtext=foldtext()
setlocal formatexpr=
setlocal formatoptions=cq
setlocal formatlistpat=^\\s*\\d\\+[\\]:.)}\\t\ ]\\s*
setlocal formatprg=
setlocal grepprg=
setlocal iminsert=0
setlocal imsearch=-1
setlocal include=^\\s*\\(from\\|import\\)
setlocal includeexpr=substitute(substitute(substitute(v:fname,b:grandparent_match,b:grandparent_sub,''),b:parent_match,b:parent_sub,''),b:child_match,b:child_sub,'g')
setlocal indentexpr=pymode#indent#get_indent(v:lnum)
setlocal indentkeys=!^F,o,O,<:>,0),0],0},=elif,=except
setlocal noinfercase
setlocal iskeyword=@,48-57,_,192-255
setlocal keywordprg=pydoc
setlocal nolinebreak
setlocal nolisp
setlocal lispwords=
setlocal nolist
setlocal makeencoding=
setlocal makeprg=
setlocal matchpairs=(:),{:},[:]
setlocal modeline
setlocal modifiable
setlocal nrformats=bin,octal,hex
set number
setlocal number
setlocal numberwidth=4
setlocal omnifunc=python3complete#Complete
setlocal path=
setlocal nopreserveindent
setlocal nopreviewwindow
setlocal quoteescape=\\
setlocal noreadonly
setlocal norelativenumber
setlocal norightleft
setlocal rightleftcmd=search
setlocal noscrollbind
setlocal shiftwidth=4
setlocal noshortname
setlocal signcolumn=auto
setlocal nosmartindent
setlocal softtabstop=4
setlocal nospell
setlocal spellcapcheck=[.?!]\\_[\\])'\"\	\ ]\\+
setlocal spellfile=
setlocal spelllang=en
setlocal statusline=%!airline#statusline(1)
setlocal suffixesadd=.py
setlocal noswapfile
setlocal synmaxcol=3000
if &syntax != 'python'
setlocal syntax=python
endif
setlocal tabstop=4
setlocal tagcase=
setlocal tags=
setlocal termwinkey=
setlocal termwinscroll=10000
setlocal termwinsize=
setlocal textwidth=79
setlocal thesaurus=
setlocal noundofile
setlocal undolevels=-123456
setlocal varsofttabstop=
setlocal vartabstop=
setlocal nowinfixheight
setlocal nowinfixwidth
set nowrap
setlocal nowrap
setlocal wrapmargin=0
45
normal! zo
656
normal! zo
657
normal! zc
682
normal! zc
719
normal! zc
735
normal! zc
let s:l = 212 - ((22 * winheight(0) + 23) / 47)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
212
normal! 014|
wincmd w
argglobal
if bufexists('~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdz_ls.py') | buffer ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdz_ls.py | else | edit ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/lasr/skrypty/sprawdz_ls.py | endif
noremap <buffer> <silent> ra :PymodeRopeAutoImport
noremap <buffer> <silent> r1p :call pymode#rope#module_to_package()
noremap <buffer> <silent> rnc :call pymode#rope#generate_class()
noremap <buffer> <silent> rnp :call pymode#rope#generate_package()
noremap <buffer> <silent> rnf :call pymode#rope#generate_function()
noremap <buffer> <silent> ru :call pymode#rope#use_function()
noremap <buffer> <silent> rs :call pymode#rope#signature()
noremap <buffer> <silent> rv :call pymode#rope#move()
noremap <buffer> <silent> ri :call pymode#rope#inline()
vnoremap <buffer> <silent> rl :call pymode#rope#extract_variable()
vnoremap <buffer> <silent> rm :call pymode#rope#extract_method()
noremap <buffer> <silent> r1r :call pymode#rope#rename_module()
noremap <buffer> <silent> rr :call pymode#rope#rename()
noremap <buffer> <silent> ro :call pymode#rope#organize_imports()
noremap <buffer> <silent> f :call pymode#rope#find_it()
noremap <buffer> <silent> d :call pymode#rope#show_doc()
noremap <buffer> <silent> ,g :call pymode#rope#goto_definition()
vnoremap <buffer> <silent> ,r :PymodeRun
nnoremap <buffer> <silent> ,r :PymodeRun
onoremap <buffer> C :call pymode#motion#select('^\s*class\s', 0)
vnoremap <buffer> <silent> K :call pymode#doc#show(@*)
nnoremap <buffer> <silent> K :call pymode#doc#find()
onoremap <buffer> M :call pymode#motion#select('^\s*def\s', 0)
onoremap <buffer> [C :call pymode#motion#move('\v^(class|def)\s', 'b')
nnoremap <buffer> [C :call pymode#motion#move('\v^(class|def)\s', 'b')
vnoremap <buffer> [M :call pymode#motion#vmove('^\s*def\s', 'b')
vnoremap <buffer> [[ :call pymode#motion#vmove('\v^(class|def)\s', 'b')
onoremap <buffer> [M :call pymode#motion#move('^\s*def\s', 'b')
onoremap <buffer> [[ :call pymode#motion#move('\v^(class|def)\s', 'b')
nnoremap <buffer> [M :call pymode#motion#move('^\s*def\s', 'b')
nnoremap <buffer> [[ :call pymode#motion#move('\v^(class|def)\s', 'b')
onoremap <buffer> ]C :call pymode#motion#move('\v^(class|def)\s', '')
nnoremap <buffer> ]C :call pymode#motion#move('\v^(class|def)\s', '')
vnoremap <buffer> ]M :call pymode#motion#vmove('^\s*def\s', '')
vnoremap <buffer> ]] :call pymode#motion#vmove('\v^(class|def)\s', '')
onoremap <buffer> ]M :call pymode#motion#move('^\s*def\s', '')
onoremap <buffer> ]] :call pymode#motion#move('\v^(class|def)\s', '')
nnoremap <buffer> ]M :call pymode#motion#move('^\s*def\s', '')
nnoremap <buffer> ]] :call pymode#motion#move('\v^(class|def)\s', '')
vnoremap <buffer> aM :call pymode#motion#select('^\s*def\s', 0)
onoremap <buffer> aM :call pymode#motion#select('^\s*def\s', 0)
vnoremap <buffer> aC :call pymode#motion#select('^\s*class\s', 0)
onoremap <buffer> aC :call pymode#motion#select('^\s*class\s', 0)
vnoremap <buffer> iM :call pymode#motion#select('^\s*def\s', 1)
onoremap <buffer> iM :call pymode#motion#select('^\s*def\s', 1)
vnoremap <buffer> iC :call pymode#motion#select('^\s*class\s', 1)
onoremap <buffer> iC :call pymode#motion#select('^\s*class\s', 1)
setlocal keymap=
setlocal noarabic
setlocal autoindent
setlocal backupcopy=
setlocal balloonexpr=
setlocal nobinary
setlocal nobreakindent
setlocal breakindentopt=
setlocal bufhidden=
setlocal buflisted
setlocal buftype=
setlocal nocindent
setlocal cinkeys=0{,0},0),:,!^F,o,O,e
setlocal cinoptions=
setlocal cinwords=if,else,while,do,for,switch
set colorcolumn=80
setlocal colorcolumn=+1
setlocal comments=b:#,fb:-
setlocal commentstring=#\ %s
setlocal complete=.,w,b,u,t,i
setlocal concealcursor=inc
setlocal conceallevel=2
setlocal completefunc=youcompleteme#CompleteFunc
setlocal nocopyindent
setlocal cryptmethod=
setlocal nocursorbind
setlocal nocursorcolumn
set cursorline
setlocal cursorline
setlocal define=^s*\\(def\\|class\\)
setlocal dictionary=
setlocal nodiff
setlocal equalprg=
setlocal errorformat=
setlocal expandtab
if &filetype != 'python'
setlocal filetype=python
endif
setlocal fixendofline
setlocal foldcolumn=0
setlocal foldenable
setlocal foldexpr=0
setlocal foldignore=#
setlocal foldlevel=2
setlocal foldmarker={{{,}}}
set foldmethod=indent
setlocal foldmethod=indent
setlocal foldminlines=1
set foldnestmax=2
setlocal foldnestmax=2
setlocal foldtext=foldtext()
setlocal formatexpr=
setlocal formatoptions=cq
setlocal formatlistpat=^\\s*\\d\\+[\\]:.)}\\t\ ]\\s*
setlocal formatprg=
setlocal grepprg=
setlocal iminsert=0
setlocal imsearch=-1
setlocal include=^\\s*\\(from\\|import\\)
setlocal includeexpr=substitute(substitute(substitute(v:fname,b:grandparent_match,b:grandparent_sub,''),b:parent_match,b:parent_sub,''),b:child_match,b:child_sub,'g')
setlocal indentexpr=pymode#indent#get_indent(v:lnum)
setlocal indentkeys=!^F,o,O,<:>,0),0],0},=elif,=except
setlocal noinfercase
setlocal iskeyword=@,48-57,_,192-255
setlocal keywordprg=pydoc
setlocal nolinebreak
setlocal nolisp
setlocal lispwords=
setlocal nolist
setlocal makeencoding=
setlocal makeprg=
setlocal matchpairs=(:),{:},[:]
setlocal modeline
setlocal modifiable
setlocal nrformats=bin,octal,hex
set number
setlocal number
setlocal numberwidth=4
setlocal omnifunc=python3complete#Complete
setlocal path=
setlocal nopreserveindent
setlocal nopreviewwindow
setlocal quoteescape=\\
setlocal noreadonly
setlocal norelativenumber
setlocal norightleft
setlocal rightleftcmd=search
setlocal noscrollbind
setlocal shiftwidth=4
setlocal noshortname
setlocal signcolumn=auto
setlocal nosmartindent
setlocal softtabstop=4
setlocal nospell
setlocal spellcapcheck=[.?!]\\_[\\])'\"\	\ ]\\+
setlocal spellfile=
setlocal spelllang=en
setlocal statusline=%!airline#statusline(2)
setlocal suffixesadd=.py
setlocal noswapfile
setlocal synmaxcol=3000
if &syntax != 'python'
setlocal syntax=python
endif
setlocal tabstop=4
setlocal tagcase=
setlocal tags=
setlocal termwinkey=
setlocal termwinscroll=10000
setlocal termwinsize=
setlocal textwidth=79
setlocal thesaurus=
setlocal noundofile
setlocal undolevels=-123456
setlocal varsofttabstop=
setlocal vartabstop=
setlocal nowinfixheight
setlocal nowinfixwidth
set nowrap
setlocal nowrap
setlocal wrapmargin=0
36
normal! zo
154
normal! zo
157
normal! zo
164
normal! zo
187
normal! zo
215
normal! zo
215
normal! zc
let s:l = 51 - ((33 * winheight(0) + 20) / 40)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
51
normal! 069|
wincmd w
argglobal
enew
setlocal keymap=
setlocal noarabic
setlocal noautoindent
setlocal backupcopy=
setlocal balloonexpr=
setlocal nobinary
setlocal nobreakindent
setlocal breakindentopt=
setlocal bufhidden=wipe
setlocal buflisted
setlocal buftype=quickfix
setlocal nocindent
setlocal cinkeys=0{,0},0),:,0#,!^F,o,O,e
setlocal cinoptions=
setlocal cinwords=if,else,while,do,for,switch
set colorcolumn=80
setlocal colorcolumn=80
setlocal comments=s1:/*,mb:*,ex:*/,://,b:#,:%,:XCOMM,n:>,fb:-
setlocal commentstring=/*%s*/
setlocal complete=.,w,b,u,t,i
setlocal concealcursor=
setlocal conceallevel=0
setlocal completefunc=youcompleteme#CompleteFunc
setlocal nocopyindent
setlocal cryptmethod=
setlocal nocursorbind
setlocal nocursorcolumn
set cursorline
setlocal cursorline
setlocal define=
setlocal dictionary=
setlocal nodiff
setlocal equalprg=
setlocal errorformat=
setlocal expandtab
if &filetype != 'qf'
setlocal filetype=qf
endif
setlocal fixendofline
setlocal foldcolumn=0
setlocal foldenable
setlocal foldexpr=0
setlocal foldignore=#
setlocal foldlevel=0
setlocal foldmarker={{{,}}}
set foldmethod=indent
setlocal foldmethod=manual
setlocal foldminlines=1
set foldnestmax=2
setlocal foldnestmax=2
setlocal foldtext=foldtext()
setlocal formatexpr=
setlocal formatoptions=tcq
setlocal formatlistpat=^\\s*\\d\\+[\\]:.)}\\t\ ]\\s*
setlocal formatprg=
setlocal grepprg=
setlocal iminsert=0
setlocal imsearch=-1
setlocal include=
setlocal includeexpr=
setlocal indentexpr=
setlocal indentkeys=0{,0},:,0#,!^F,o,O,e
setlocal noinfercase
setlocal iskeyword=@,48-57,_,192-255
setlocal keywordprg=
setlocal nolinebreak
setlocal nolisp
setlocal lispwords=
setlocal nolist
setlocal makeencoding=
setlocal makeprg=
setlocal matchpairs=(:),{:},[:]
setlocal modeline
setlocal nomodifiable
setlocal nrformats=bin,octal,hex
set number
setlocal number
setlocal numberwidth=4
setlocal omnifunc=
setlocal path=
setlocal nopreserveindent
setlocal nopreviewwindow
setlocal quoteescape=\\
setlocal noreadonly
setlocal norelativenumber
setlocal norightleft
setlocal rightleftcmd=search
setlocal noscrollbind
setlocal shiftwidth=4
setlocal noshortname
setlocal signcolumn=auto
setlocal nosmartindent
setlocal softtabstop=0
setlocal nospell
setlocal spellcapcheck=[.?!]\\_[\\])'\"\	\ ]\\+
setlocal spellfile=
setlocal spelllang=en
setlocal statusline=%!airline#statusline(3)
setlocal suffixesadd=
setlocal noswapfile
setlocal synmaxcol=3000
if &syntax != 'qf'
setlocal syntax=qf
endif
setlocal tabstop=4
setlocal tagcase=
setlocal tags=
setlocal termwinkey=
setlocal termwinscroll=10000
setlocal termwinsize=
setlocal textwidth=0
setlocal thesaurus=
setlocal noundofile
setlocal undolevels=-123456
setlocal varsofttabstop=
setlocal vartabstop=
setlocal winfixheight
setlocal nowinfixwidth
set nowrap
setlocal nowrap
setlocal wrapmargin=0
wincmd w
2wincmd w
exe 'vert 1resize ' . ((&columns * 105 + 105) / 211)
exe '2resize ' . ((&lines * 40 + 25) / 50)
exe 'vert 2resize ' . ((&columns * 105 + 105) / 211)
exe '3resize ' . ((&lines * 6 + 25) / 50)
exe 'vert 3resize ' . ((&columns * 105 + 105) / 211)
tabnext 1
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
doautoall SessionLoadPost
unlet SessionLoad
" vim: set ft=vim :
