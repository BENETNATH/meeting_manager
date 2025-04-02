pybabel extract --ignore-dirs=.venv -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
read -p "Now, translate every .po files located in translations\xx\LC_MESSAGES Then come back and press a key !"
pybabel compile -d translations
