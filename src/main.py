from tkinter import *

# global reference to tkinter app
root = Tk()

# global reference to app base colors
colors = {
    "primary": "#1e3743",
    "secondary": "#1e3760",
    "terciary": "#00aa00",
}

class FrameWidget():
	# __init__ function for class FrameWidget
    def __init__(self, widget: Widget, xPos, yPos):
        self.__widget = widget
        self.__xPos = xPos
        self.__yPos = yPos
        self.show()

    def show(self):
        self.__widget.place(x=self.__xPos, y=self.__yPos)

    def hide(self):
        self.__widget.place_forget()

# frame 1:n widgets
class PageFrame():
	# __init__ function for class PageFrame
    def __init__(self,
                 startx: float,
                 starty: float,
                 width: float,
                 height: float,
                 border: float,
                 backgroundcolor: StringVar,
                 highlightbackground: StringVar,
                 highlightthickness: StringVar,
                 widgets: list[FrameWidget]):
        self.__startx = startx
        self.__starty = starty
        self.__width = width
        self.__height = height
        self.__widgets = widgets
        self.frame = Frame(
                        root,
                        bd=border, 
                        bg=backgroundcolor,
                        highlightbackground=highlightbackground,
                        highlightthickness=highlightthickness
                    )
        self.hide()
    
    def show(self):
        self.frame.place(
            relx=self.__startx,
            rely=self.__starty,
            relwidth=self.__width,
            relheight=self.__height
        )

    def hide(self):
        self.frame.place_forget()

# TODO: check if necessary this implementation
# current usage is a variable pages of type list PageFrames
# app.pages: PageFrames[]
# page 1:n frames
class Page():
	# __init__ function for class Page
    def __init__(self, name: str, frames: list[PageFrame]):
        self.__name = name
        self.__frames = frames

class Application():
	# __init__ function for class Application 
    def __init__(self):
        self.root = root
        self.pages = {}
        self.appscreen()
        root.mainloop()
    
    # function to define the main screen configs
    def appscreen(self):
        self.root.title("GameFlowConnect")
        self.root.configure(background=colors["primary"])
        self.root.geometry("800x600+0+0")
        self.root.resizable(True, True)
        # self.root.minsize("400x300")
        # self.root.maxsize("1200x600")
        # widget -> Label(self.main_frame, text="First page").place(relx=0.05, rely=0.05)
        self.create_page("First page", [
            PageFrame(0.02, 0.02, 0.96, 0.3, 4, colors["secondary"], colors["terciary"], 2, [
                FrameWidget(Button(self.root), xPos=50, yPos=50)
            ]),
            PageFrame(0.02, 0.35, 0.96, 0.6, 4, colors["secondary"], colors["terciary"], 2, []),
        ])
        self.create_page("Second page", [
            PageFrame(0.1, 0.02, 0.8, 0.6, 8, colors["secondary"], colors["terciary"], 2, []),
        ])
        self.change_page("First page")

    # function to define the application pages
    def create_page(self, name, frames):
        self.pages[name] = frames

    # function to change pages
    def change_page(self, pagename):
        # print("Changed to page " + pagename)
        for frame in self.pages[pagename]:
            frame.show()

Application()
