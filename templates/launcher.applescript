-- skaz menu-bar launcher.
-- {{INSTALL_DIR}} is replaced at install time with the absolute install path.
do shell script "{{INSTALL_DIR}}/.venv/bin/python {{INSTALL_DIR}}/src/skaz_menu.py > /tmp/skaz-menu.log 2>&1 &"
