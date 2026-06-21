import logging
from tools import * 
from tray import Tray 
 # Просмотр логов на телефоне adb logcat -s ControlTCPServer
class MyFilter(logging.Filter):
    def filter(self,record):
        # print(record.name, record.module)
        return record.name.startswith(("main","tray","tools","seting","Server"))
    
def configure_logging (level = logging.INFO):
    root = logging.getLogger()
    format = logging.Formatter(
        datefmt="%Y-%m-%d %H:%M:%S",
        #fmt="[%(asctime)s] %(name)5s/%(funcName)s:%(lineno)-3d %(levelname)-5s - %(message)s",
        fmt="[%(asctime)s] %(name)5s: %(lineno)-3d %(levelname)-5s - %(message)s",
    ) 

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(format)
    console.addFilter(MyFilter())

    file = logging.FileHandler("log.log",mode="w",encoding="utf-8")
    file.setLevel(level)
    file.setFormatter(format)
    file.addFilter(MyFilter())

    root.addHandler(console)
    root.addHandler(file)

    root.setLevel(level)

def main():
    configure_logging(logging.DEBUG)
    log = logging.getLogger(__name__)
    log.info("Запуск приложения")
    tray = Tray()
    tray.start()

if __name__ == "__main__":
    main()