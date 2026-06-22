import customtkinter as ctk
import logging 
import queue
import json

from tools import load_config, get_base_path, ask_yes_or_no
log = logging.getLogger(__name__)

class SetingWindow():
    def __init__(self,q: queue.Queue, state_isRunning: bool = False):
        self.q = q
        self.state_isRunning = state_isRunning

    def _run(self):
        log.debug("Иницилизация класса")
        self.config = load_config()

        self.app = ctk.CTk()
        self.app.after(100,lambda: self.app.iconbitmap(str(get_base_path() + "/icon.ico")))
        self.app.title("Настройки")
        self.app.geometry("500x420")
        self.app.protocol("WM_DELETE_WINDOW", lambda: self.tab(True))
        ctk.set_appearance_mode("dark")
        self.app_tab = False
        self.app.withdraw()

        self.root = ctk.CTkScrollableFrame(self.app)
        self.root.pack(fill="both",expand=True)

        self.ip_text = ctk.CTkLabel(self.root,text="Айпи приёмника")
        self.ip_text.pack(padx=5,pady=(15,5),anchor="w")
        
        self.ip_entry = ctk.CTkEntry(self.root,corner_radius=10,placeholder_text="192.168.0.2")
        self.ip_entry.pack(padx=5,pady=(5,15),fill="x")

        if self.config.get("phone_ip") != "" or not None:
            self.ip_entry.insert(0,self.config.get("phone_ip"))

        self.port_text = ctk.CTkLabel(self.root,text="Порт приёмника",corner_radius=10)
        self.port_text.pack(padx=5,pady=(15,5),anchor="w")

        self.port_entry = ctk.CTkEntry(self.root,corner_radius=10,placeholder_text="5000")
        self.port_entry.pack(padx=5,pady=(5,15),fill="x")

        if self.config.get("port") != 0 or not None:
            self.port_entry.insert(0,self.config.get("port"))

        self.saving_button = ctk.CTkButton(self.root,corner_radius=10,command=lambda:self.saving(),text="Сохранить")
        self.saving_button.pack(padx=5,pady=5)
        
        self.app.mainloop()

    def saving(self):
        log.info("Сохранение настроек")
        self.config["port"] = int(self.port_entry.get())
        self.config["phone_ip"] = self.ip_entry.get()

        try:
            with open(str(get_base_path() + "/config.json"), "w", encoding = "utf-8") as f:
                json.dump(self.config, f, indent=4,ensure_ascii=False)
        except (OSError, TypeError):
            log.exception("Не удалось сохранить конфиг")
            otv = ask_yes_or_no("Попробовать снова?","Ошибка сохрения настроек")
            if otv is True:
                self.saving()
            else:
                return

        log.debug(f"state_isRunning = {self.state_isRunning}")
        if self.state_isRunning is True:
            otv = ask_yes_or_no("Перезапустить передачу для применения настроек?","Передача запущена")
            if otv is True:
                self.q.put({"type":"RESTART"})

        self.tab()

    def tab (self, saveing: bool = False):
        if not self.app_tab:
            self.app_tab = True
            if saveing is True:
                pass
            self.app.after(100, self.app.deiconify)
        else :
            self.app_tab = False 
            self.app.after(100, self.app.withdraw)