import logging
from pystray import Menu, MenuItem
import pystray
from PIL import Image
import threading
import queue
import asyncio 
import sys

from tools import get_base_path, AudioSender, CustomError, load_config
from seting import SetingWindow
from Server import Server
from Server.command import *

log = logging.getLogger(__name__)

class Tray:
    def __init__ (self):
        log.debug("Иницилизация класса")
        image = Image.open(str(get_base_path() + "/icon.png"))

        self.isRun = False
        self.value = 100 
        self.isRunning = False
        #self.isPing = False
        self.command = {
            notify : self.push_notifi,
            valume : self._edit_value
        }
        self.AudioSender = AudioSender()
        
        self.SetingWindow = SetingWindow()
        threading.Thread(target=lambda:self.SetingWindow._run(),daemon=True).start()

        try:
            self.queue = asyncio.Queue()
            self.q = queue.Queue()
            config = load_config(str(get_base_path() + "/config.json"))
            self.Server = Server(ip=config.get("phone_ip"),port=int(config.get("port") + 1),q=self.queue,com_q=self.q)
        except Exception:
            log.exception("Ошибка при старте сервера")
            raise Exception

        self.icon = pystray.Icon(
            "Audio in Wifi",
            image,
            "Audio in Wifi",
            menu = Menu(
                MenuItem( lambda _: "Остановить" if self.isRunning else "Запустить",self._tab_AudioSender),
                MenuItem ("Перезапустить",self._restart_Sender,enabled= lambda _: self.isRunning),
                Menu.SEPARATOR,
                MenuItem("Громкость",Menu(
                    MenuItem("25%",lambda _: self._edit_value(25),checked=lambda _: self.value == 25,radio=True),
                    MenuItem("50%",lambda _: self._edit_value(50),checked=lambda _: self.value == 50,radio=True),
                    MenuItem("100%",lambda _: self._edit_value(100),checked=lambda _: self.value == 100,radio=True),
                    MenuItem("150%",lambda _: self._edit_value(150),checked=lambda _: self.value == 150,radio=True),
                    MenuItem("200%",lambda _: self._edit_value(200),checked=lambda _: self.value == 200,radio=True),
                    MenuItem(lambda _: f"Громкость = {self.value}",lambda _: self._edit_value(self.value),enabled=False)
                ),enabled=lambda _: self.isRunning),
                MenuItem("Пинг клиента",self._ping),
                #MenuItem(lambda _:"Активен" if self.isPing is True else "Офлайн",self._ping,enabled=False),
                Menu.SEPARATOR,
                MenuItem("Настройки",self._tab_seting,default=True),
                Menu.SEPARATOR,
                MenuItem (lambda _: "Выход" if self.isRunning is not True else "Выход и остановка передачи",self._exit)
            )
        )

    def _edit_value(self,value: int| dict):
        match value:
            case int():
                log.info(f"Изменения громкости на {value}")
                self.value = value
                self.AudioSender.edit_value(value)
                self.put({"type":"SEND","value":{"type":"VOLUME","value":value}})
            case dict():
                valume = value.get("value")
                log.info(f"Изменения громкости на {valume}")
                self.value = valume
                self.AudioSender.edit_value(valume)
                
        self.icon.update_menu()

    def _ping(self,icon,item):
        log.info("Пинг клиента")
        # if self.isPing is True:
        #     self.isPing = False
        # else:
        #     self.isPing = True
        # self.icon.update_menu() #TODO: Потом сделать средство связи между сервером и клиентом
        self.put({"type":"PING","command":lambda e: self.push_notifi(e)})

    def _exit(self,icon,item):
        log.info("Закрытия трея")
        if self.isRunning is True:
            self.AudioSender.stop()
        self.stop()

    def _restart_Sender(self,icon,item):
        log.info("Перезапуск передачи")
        self._tab_AudioSender()
        self._tab_AudioSender()

    def _tab_seting(self,icon,item):
        self.SetingWindow.tab()

    def _tab_AudioSender(self,icon=None,item=None):
        if self.isRunning is False:
            log.info("Запуск передачи")
            self.icon.title = "Запускается передача"
            try:
                self.AudioSender.start()
                self.put({"type":"START"})
            except Exception as e:
                log.exception("Ошибка при старте передачи")
                if e != 2:
                    CustomError(e,func=lambda e: self._except_tab_audiosender(e))#,output=lambda: self._tab_AudioSender())
                else:
                    self.icon.title = "Ошибка запуска передачи"
                return
            self.isRunning = True
            self.icon.title = "Передача запущена"
            self.icon.update_menu()
        else: 
            log.info("Остановка передачи")
            self.put({"type":"STOP"})
            self.isRunning = False
            self.AudioSender.stop()
            self.icon.title = "Audio in Wifi"
            self.icon.update_menu()

    def _except_tab_audiosender(self,text:str): 
        self.AudioSender.start(True,text)
        self.icon.title = "Передача запущена"
        self.icon.update_menu()

    def push_notifi(self,text:dict):
        if self.icon.HAS_NOTIFICATION:
            log.info("Вывод уведомления")
            log.debug(f"Текст уведомления {text.get('value')}")
            self.icon.notify(text.get("value"),"Audio in Wifi")
        else:
            log.info("Неудачная попытка вывод уведомления")

    def start(self):
        self.isRun = True
        log.info("Запуск трея")
        self.icon.run_detached()
        self._check_queue()

    def stop(self):
        self.isRun = False
        self.icon.stop()

    def put(self,command: dict):
        if self.Server.loop is None:
            log.warning("Попытка отправка команды когда eventloop is None")
            return
        log.debug(f"Отправка команды в очередь: {command}")
        self.Server.loop.call_soon_threadsafe(self.queue.put_nowait,command)

    def _check_queue(self):
        log.debug("Начало проверки очереди команд")
        while self.isRun:
            try:
                task = self.q.get(timeout=1)
                self._analiz(task)
            except queue.Empty:
                continue

    def _analiz(self,command:dict):
        try:
            self.command[command.get("type")](command)
        except KeyError:
            log.warning(f"Неизвестная команда в очереди {command}")