pybabel extract --ignore-dirs=".venv build" -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
pybabel compile -d translations