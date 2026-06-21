import asyncio
import threading
import logging 
import json
from .protocol import *
import queue
# import queue

log = logging.getLogger(__name__)

class Server():
    def __init__(self,ip: str, port: int,q: asyncio.Queue,com_q: queue.Queue):
        log.debug("Иницилизация класса")
        # self.isCLient = False
        self.port = port
        self.ip = ip
        self.q = q
        self.loop = None
        self.isPing = False
        self.Ping = False
        self.com_q = com_q

        self.protocol = {
            ping : self.on_ping,
            pong : self.on_pong,
            volume : self.on_volume,
            stop : self.on_stop,
            start: self.on_start,
            send : self.send,
            send_tray: self.on_send
        }

        self.reader = None
        self.writer = None

        self.run()

    def run(self):
        log.info("Запуск TCP клиента")
        threading.Thread(target=lambda:asyncio.run(self.main()),daemon=True).start()

    async def main(self,connect: bool = False):   
        if connect is True:
            self.isRunning = True
            try:
                log.info("Подключение к серверу")
                log.debug(f"Клиент {self.ip}:{self.port}")
                reader, writer = await asyncio.wait_for(asyncio.open_connection(self.ip,self.port),timeout=25.0)
                self.reader = reader
                self.writer = writer  
            except asyncio.TimeoutError:
                log.exception("Сервер не ответил")
                return
            except (ConnectionResetError,ConnectionRefusedError,TimeoutError,OSError):
                log.exception(f"Ошибка при подключении к серверу {self.ip}:{self.port}")
                return
            except Exception:
                log.exception("Неизвестная ошибка")
                return
            asyncio.create_task(self.handler())
        else:
            self.isRunning = False
            self.loop = asyncio.get_running_loop()
            await self._check_queue()

    async def on_stop(self,command: dict):
        log.info("Закрытие соеденения")
        self.isRunning = False
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None

    async def on_start(self,command: dict):
        await self.main(True)

    async def on_volume(self,command: dict):
        log.info(f"Клиент изменил громкость на {command.get('value')}")
        await self.put(command)
        await self.put({"type":"NOTIFY","value":f"Клиент изменил громкость на {command.get('value')}"})

    async def on_pong(self,command: dict):
        self.Ping = False
        log.info("Клиент ответил понг")
        await self.put({"type":"NOTIFY","value":"Клиент ответил понг"})
        if self.isPing is True:
            log.info("Остановка соеденения")
            await self.q.put({"type":"STOP"})

    async def on_ping(self,command: dict):
        if self.writer is None:
            log.warning("Нету конекта к серверу, подключение...")
            await self.main(True)
            self.isPing = True
        log.info("Отправка пинг запроса")
        self.Ping = True
        await self.send({
            "type": "PING"
        })
        await self._check_ping()

    async def on_send(self,command: dict):
        log.debug(f"Отправка команды трею {command}")
        await self.put(command.get("value"))

    async def _check_ping(self):
        await asyncio.sleep(30.0)
        if self.Ping is True:
            log.info("Клиент не ответил на пинг")
            await self.put({"type":"NOTIFY","value":"Клиент не ответил на пинг"})
        else:
            return

    async def _check_queue (self):
        log.debug("Начало проверки очереди команд")
        while True : 
            task = await self.q.get()
            asyncio.create_task( self.analiz(task))

    async def analiz(self,command: dict):
        try:
            log.debug(f"Анализ полученных данных: {command}")
            await self.protocol[command.get("type")](command)
        except KeyError:
            log.exception("Неизвестваня команда")

    async def handler(self):
        log.debug("Чтение команд от сервера")
        while True:
            data = await self.reader.readline()
            if not data:
                break
            log.debug(f"Необработаный пакет: {data}")
            command = data.decode().strip()
            if not command:
                break
            log.debug(f"Обработаный пакет:{command}")
            try:
                message = json.loads(command)
            except json.JSONDecodeError:
                log.warning(f"Битый пакет: {command}")
                continue 

            await self.analiz(message)
        # except (ConnectionResetError, OSError) :
            # self.isCLient = False
            # log.exception(f"Кажется клиент отключился: {addr}")

    async def send(self,command: dict):
        if self.writer is None :
            log.error("Невозможно отправить запрос к серверу")
            return
        if command.get("type") == send :
            data = json.dumps(command.get("value"))
        else:
            data = json.dumps(command)
        self.writer.write((data + "\n").encode())
        await self.writer.drain()

    async def put(self,command: dict):
        log.debug(f"Отправка команды трею: {command}")
        if self.loop is None:
            log.warning("Ошибка при отправке команды в трей, loop is None")
            return
        await self.loop.run_in_executor(None,self.com_q.put , command)