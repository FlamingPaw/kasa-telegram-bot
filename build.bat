@ECHO OFF
pip.exe install -r requirements.txt
pyinstaller.exe ./kasa-telegram-bot.spec
echo File created in build folder.