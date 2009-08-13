" Beah - Test harness. Part of Beaker project.
"
" Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
"
" This program is free software; you can redistribute it and/or modify
" it under the terms of the GNU General Public License as published by
" the Free Software Foundation; either version 2 of the License, or
" (at your option) any later version.
"
" This program is distributed in the hope that it will be useful,
" but WITHOUT ANY WARRANTY; without even the implied warranty of
" MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
" GNU General Public License for more details.
"
" You should have received a copy of the GNU General Public License
" along with this program; if not, write to the Free Software
" Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

let s:INDENT = "  "
let s:indent = ""

function! Indent()
  let line = getline(".")
  if line =~ '^}'
    let s:indent = s:indent[:-(len(s:INDENT)+1)]
  endif
  call setline(".", s:indent . line)
  if line =~ '{$'
    let s:indent .= s:INDENT
  endif
endfunction

g/\S\+/call Indent()
