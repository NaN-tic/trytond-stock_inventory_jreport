#!/bin/sh -e
￼pybabel extract -F babel.cfg -k lazy_gettext -k __ -k _ -o messages.pot .
￼pybabel update -i messages.pot -d translations/ -l es
￼pybabel update -i messages.pot -d translations/ -l ca
￼pybabel compile -d translations
