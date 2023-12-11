from tkinter import *

root = Tk()

colors = {
    "primary": "#1e3743",
    "secondary": "#1e3760",
    "terciary": "#00aa00",
}

class Application():
    def __init__(self):
        self.root = root
        self.tela()
        self.frames()
        root.mainloop()
    
    def tela(self):
        self.root.title("Teste")
        self.root.configure(background=colors["primary"])
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        # self.root.minsize("400x300")
        # self.root.maxsize("1200x600")
    
    def frames(self):
        self.main_frame = Frame(self.root, bd=4, bg=colors["secondary"], 
                                highlightbackground=colors["terciary"],
                                highlightthickness=2)
        self.main_frame.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.46)




Application()
