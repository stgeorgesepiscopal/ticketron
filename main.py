import re
from time import strftime

from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.image import Image
from kivy.uix.accordion import AccordionItem
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen, ScreenManager, SwapTransition

import ezsheets


LabelBase.register(name='Roboto',
                   fn_regular='Roboto-Thin.ttf',
                   fn_bold='Roboto-Medium.ttf')


class DashboardScreen(Screen):
    pass


class TicketScreen(Screen):
    pass


class TicketItem(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animate_in()

    def animate_in(self):
        a = Animation(opacity=1, duration=2)
        a.start(self)


class NewTicketItem(TicketItem):
    pass



class WindowManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg_texture = Image(source='bg.jpg')
    pass


class TicketronApp(App):
    def __init__(self):
        super().__init__()
        self.all_tickets = set()
        self.new_tickets = set()
        self.ticket_widgets = {}
        self.current_ticket = 0
        self.sheet = None


    def update_time(self, _):
        self.root.ids.time.text = strftime('%-I:%M')
        self.root.ids.seconds.text = strftime('%S ')
        self.root.ids.ampm.text = strftime('[b]%p[/b]')
        self.root.ids.calendar.text = strftime('[b]%A[/b] %B %-d')

    def add_ticket(self, n):
        if n[3] == "NEW":
            t = NewTicketItem(text=f"[b]{n[1]}[/b][size=30sp]\n{n[2]}[/size]")
        else:
            t = TicketItem(text=f"[b]{n[1]}[/b][size=30sp]\n{n[2]}[/size]")
        self.ticket_widgets[n[0]] = t
        self.all_tickets.add(n)
        self.root.ids.tickets.add_widget(t)

    def remove_ticket(self, n):
        try:
            t = self.ticket_widgets.pop(n[0])
            self.all_tickets.remove(n)
            a = Animation(opacity=0)

            def callback(*args):
                self.root.ids.tickets.remove_widget(t)

            a.bind(on_complete=callback)
            a.start(t)
        except KeyError:
            pass


    def get_tickets_from_sheet(self, *_):
        self.sheet.refresh()
        ws = self.sheet.sheets[0]
        print(ws.title, ws.columnCount, ws.rowCount)
        ws.getRows()

        new_tickets = set()

        for row in ws:
            if row[8] in [ "0 - New", "1 - Open" ]:
                status = 'NEW' if row[8] == "0 - New" else 'OPEN'
                id = row[9]
                title = re.sub(r"re: |fwd: |\[EXTERNAL\] ", "", row[3], flags=re.I)
                fr = row[2]
                new_tickets.add((id, title, fr, status))

        for t in self.all_tickets.difference(new_tickets):
            self.remove_ticket(t)

        for t in new_tickets.difference(self.all_tickets):
            self.add_ticket(t)

        num_tickets = len(self.all_tickets)
        self.root.ids.ticket_header.text = f"[b]{num_tickets}[/b] Open Ticket{'s' if num_tickets != 1 else ''}"





    def rotate_tickets(self, n):
        self.current_ticket += 1
        if self.current_ticket >= len(self.ticket_widgets):
            self.current_ticket = 0
        try:
            self.ticket_widgets[self.current_ticket].dispatch('on_touch_down', self.ticket_widgets[self.current_ticket])
        except KeyError:
            pass

    def init_sheet(self, n):
        self.sheet = ezsheets.Spreadsheet('1-XlENZVrZ9oYx6UqIUi5V3eq0l3RPDCfeXIyB6TC2NA')

    def on_start(self):
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_once(self.init_sheet, 0.1)
        Clock.schedule_once(self.get_tickets_from_sheet, 5)
        Clock.schedule_interval(self.get_tickets_from_sheet, 60*1)
        Clock.schedule_interval(self.rotate_tickets, 3)




if __name__ == "__main__":
    TicketronApp().run()
