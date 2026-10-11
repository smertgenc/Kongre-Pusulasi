#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  print 'Önce README içindeki kurulum adımlarını tamamlayın (.venv eksik).'
  read 'reply?Çıkmak için Enter tuşuna basın.'
  exit 1
fi
exec .venv/bin/python server.py --open
