-- skaz menu-bar launcher (compiled to SkazMenu.app at install time).
do shell script "{{INSTALL_DIR}}/.venv/bin/python {{INSTALL_DIR}}/src/skaz_menu.py > /tmp/skaz-menu.log 2>&1 &"
