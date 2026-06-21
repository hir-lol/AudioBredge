import customtkinter as ctk
from tools import load_config, get_base_path

class SetingWindow():
    def __init__(self, state_isRunning: bool = None):
        self.state_isRunning = state_isRunning

    def _run(self):
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

        self.port_text = ctk.CTkLabel(self.root,text="Порт приёмника",corner_radius=10)
        self.port_text.pack(padx=5,pady=5,anchor="w")

        self.port_entry = ctk.CTkEntry(self.root,corner_radius=10,placeholder_text="5000")
        self.port_entry.pack(padx=5,pady=5,fill="x")
        
        self.app.mainloop()

    def tab (self, saveing: bool = False):
        if not self.app_tab:
            self.app_tab = True
            if saveing is True:
                pass
            self.app.after(100, self.app.deiconify)
        else :
            self.app_tab = False 
            self.app.after(100, self.app.withdraw)