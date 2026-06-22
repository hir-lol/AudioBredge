import socket
import pyaudio
import asyncio
import os
import sys 
import json 
import threading
from typing import Callable
import customtkinter as ctk
from array import array
import logging 
import ctypes 
import queue

__all__ = ("load_config","get_base_path","AudioSender")
log = logging.getLogger(__name__)

_u32 = ctypes.windll.user32
_u32.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
_u32.MessageBoxW.restype = ctypes.c_int

_MB_YESNO_Q = 0x24
_MB_OR_ERR = 0x10
_IDYES = 6

def ask_yes_or_no(text:str, title:str) -> bool:
    return True if _u32.MessageBoxW(0,text,title,_MB_YESNO_Q) == _IDYES else False

def show_error(text:str, title:str):
    _u32.MessageBoxW(0,text,title,_MB_OR_ERR)

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def load_config(CONFIG_FILE: str = str(get_base_path()+"/config.json")) -> dict :
    if not os.path.exists(CONFIG_FILE):
        log.error("Не нашёлся конфиг по пути:",CONFIG_FILE)
        #raise FileNotFoundError(f"File not found in path: {CONFIG_FILE}")
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.exception("Ошибка чтения config.json")
        return {}

class CustomError():
    """
    Класс для диалогового окна ошибки, выдаёт да или нет, если нажато да то выдаёт поле для ввода и при подтвержедении ведённого вызвает 
    переданную функцию и закрывается

    text - Текст ошибки
    func - Вызываемая функция после ввода данных, на вход должна принимать то что быо ведено в поле
    output - Вызываемая функция после отказа от ввода данных

    Retry_label_text - текст который будет дополнительно показан в окне
    entry_placeholder_text - фоновый текст у поля ввода
    """
    def __init__(self,text: str, func: Callable = None, output: Callable = None):
        self.boost = 1.0
        self.Retry_label_text = "Попробовать снова но с дефолтными настройками?"
        self.entry_placeholder_text = "192.168.0.2"

        self._app = ctk.CTk()
        self._app.geometry("350x130")
        self._app.title("Ошибка")
        self._app.protocol("WM_DELETE_WINDOW", lambda: self._exit(True))
        ctk.set_appearance_mode("dark")

        self._Error_TextWiev = ctk.CTkLabel(self._app, text = text,wraplength=330)
        self._Error_TextWiev.pack(fill="both",padx=5,pady=5)

        self._Retry_Label = ctk.CTkLabel(self._app,text=self.Retry_label_text,wraplength=330)
        self._Retry_Label.pack(fill="both",padx=5,pady=5)

        self._frame = ctk.CTkFrame(self._app)
        self._frame.pack(fill="both",padx=5,pady=5)

        self._no_button = ctk.CTkButton (self._frame,text="Нет",command=lambda: self._exit(True),corner_radius=10)
        self._no_button.grid(row=0,column=0,padx=5,pady=5)

        self._frame.grid_columnconfigure(0,weight=1)
        self._frame.grid_columnconfigure(1,weight=1)

        self._yes_button = ctk.CTkButton(self._frame,text="Да",command=lambda: self._yes(),corner_radius=10)
        self._yes_button.grid(row=0,column=1,padx=5,pady=5)

        self._entry = ctk.CTkEntry(self._app,corner_radius=10,placeholder_text=self.entry_placeholder_text)
        self._entry.bind("<Return>", lambda e:self._ready())
        self._ready_button = ctk.CTkButton(self._app,corner_radius=10,text="Подтвердить",command=lambda: self._ready())

        self.func = func if func is not None else False
        self.output_func = output if output is not None else False
        self._app.mainloop()

    def _ready(self):
        if self.func is not False:
            self.func(self._entry.get())
        self._exit()

    def _yes(self):
        self._frame.pack_forget()

        self._entry.pack(padx=5,pady=5)
        self._ready_button.pack(padx=5,pady=5,anchor="e")

    def _exit(self,output: bool = False):
        if output is True:
            if self.output_func is not False:
                self.output_func()
        self._app.destroy()

class AudioSender () :
    def __init__ (self,q:queue.Queue):
        log.debug("Иницализация класса")
        self._sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self._p = pyaudio.PyAudio()
        self._format = pyaudio.paInt16
        self.boost = 1.0
        self.q = q

    def start(self, defalt: bool = False,ip: str = None):
        log.info("Получение настроек")
        if defalt is False:
            try:
                log.debug("Пременение пользавательских настроек")
                config = load_config(str(get_base_path() + "/config.json"))
                self._chunk = config["chunk"]
                self._channels = config["channels"]
                self._rate = config["rate"]

                self._phone_ip = config["phone_ip"]
                self._port = config["port"]
            except KeyError as e:
                raise Exception(f"Ошибка при получении настроек, не найден ключ {e}")
        else:
            log.debug("Пременения стандартных настроек")
            self._chunk = 2048
            self._channels = 2
            self._rate = 44100
            self._port = 5000
            self._phone_ip = ip

        threading.Thread(target= self._async_start,daemon=True).start()

    def stop(self):
        self._send = False

    def _async_start(self):
        asyncio.run(self._sender())

    def edit_value(self,value: int):
        if value > 100 :
            self.boost = value / 100

    def _boosting(self,data):
        samples = array("h", data)

        for i, sample in enumerate(samples):
            sample = int(sample * self.boost)

            if sample > 32767:
                sample = 32767
            elif sample < -32768:
                sample = -32768

            samples[i] = sample 

        return samples.tobytes()

    async def _sender (self):
        log.debug("Поиск динамика")
        self._device_index = None
        for i in range(self._p.get_device_count()):
            dev = self._p.get_device_info_by_index(i)
            if "CABLE Output" in dev.get("name"):
                self._device_index = i 
                log.debug(f"Нашёлся динамик: {dev.get('name')}") 
                break

        if self._device_index is None:
            log.error("Не нашёлся динамик")
            self.q.put({"type":"NOTIFY","value":"Не найден виртуальный динамик"})
            show_error("Не найден виртуальный динамик","Критическая ошибка")
            raise Exception(2)

        self._stream = self._p.open(
            format= self._format,
            channels= self._channels,
            rate= self._rate,
            input= True,
            input_device_index=self._device_index,
            frames_per_buffer=self._chunk
        )

        self._send = True
        
        log.info("Отправка началась")

        while self._send:
            try:
                data = self._stream.read(self._chunk,exception_on_overflow=False)
                if self.boost >= 1.0:
                    data = self._boosting(data)
                self._sock.sendto(data,(self._phone_ip,self._port))
            except Exception:
                pass

        log.info("Окончание отправки")
