import re
from types import SimpleNamespace
from time import strftime

from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.image import Image
from kivy.uix.accordion import AccordionItem
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen, ScreenManager, SwapTransition
from kivy.uix.settings import SettingsWithTabbedPanel
from kivy.core.audio import SoundLoader
from kivy.config import ConfigParser
from kivy.config import Config
from kivy.lang import Builder
from kivy.logger import Logger

import ezsheets

LabelBase.register(name='Roboto',
                   fn_regular='Roboto-Thin.ttf',
                   fn_bold='Roboto-Medium.ttf')


TicketStatus = SimpleNamespace(
    NEW="0 - New",
    OPEN="1 - Open",
    PINNED="8 - Pinned",
    CLOSED="9 - Closed")


class DashboardScreen(Screen):
    pass


class OptionsScreen(Screen):
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


class PinnedTicketItem(TicketItem):
    pass


class WindowManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg_texture = Image(source='bg.jpg')

# point to settings JSON
# link to file next
json = '''
[
    {
        "type": "title",
        "title": "Options"
    },
    {
        "type": "bool",
        "title": "Audio",
        "desc": "Toggle audio ON | OFF",
        "section": "Audio",
        "key": "audio_bool"
    }
]
'''

class TicketronApp(App):
    
    #######################
    # start OPTIONS panel #
    #######################

    def build_config(self, config):
        """
        Set the default values for the configs sections.
        """
        config.setdefaults('My Label', {'text': 'Hello', 'font_size': 20})
        config.setdefaults('Audio', {'audio_bool': True, 'font-size': 20, 'value':['True', 'False']})

    def build_settings(self, settings):
        """
        Add our custom section to the default configuration object.
        """
        # We use the string defined above for our JSON, but it could also be
        # loaded from a file as follows:
        #     settings.add_json_panel('My Label', self.config, 'settings.json')
        settings.add_json_panel('Audio', self.config, data=json)

    def on_config_change(self, config, section, key, value):
        """
        Respond to changes in the configuration.
        """
        Logger.info("main.py: App.on_config_change: {0}, {1}, {2}, {3}".format(
            config, section, key, value))

        if section == "My Label":
            if key == "text":
                self.root.ids.label.text = value
            elif key == 'font_size':
                self.root.ids.label.font_size = float(value)

        if section == "Audio":
            if key == 'audio_bool':
                #self.root.ids.audio_bool = value
                self.play_audio = value

    def close_settings(self, settings=None):
        """
        The settings panel has been closed.
        """
        Logger.info("main.py: App.close_settings: {0}".format(settings))
        super().close_settings(settings)
    
    ### END OPTIONS Panel ###
    
    """
    Main app class - Receives styling / layout from ticketron.kv (Kivy syntax)
    """
    def __init__(self):
        super().__init__()
        self.all_tickets = set()
        self.all_pins = set()
        
        self.ticket_widgets = {}  # Hold reference to individual widgets, referenced by ticket ID
        self.current_ticket = 0  # For rotation - not currently used
        self.active_ticket = None  # For rotation - not currently used
        self.sheet = None  # To hold Google Sheet - initialized with a Clock.schedule_once to avoid startup lag
        self.play_audio = True  # change to false to disable sound
        self.new_ticket_sound = SoundLoader.load('audio/chime.wav') # New ticket sound
        
    
    def update_time(self, _):
        self.root.ids.time.text = strftime('%-I:%M')
        self.root.ids.seconds.text = strftime('%S ')
        self.root.ids.ampm.text = strftime('[b]%p[/b]')
        self.root.ids.calendar.text = strftime('[b]%A[/b] %B %-d')

    def add_pin(self, pin_data):
        t = PinnedTicketItem(text=f"[size=30sp][b]{pin_data[1]}[/b][/size][size=15sp]\n{pin_data[2]}[/size]")
        self.all_pins.add(pin_data)
        self.root.ids.pins.add_widget(t)

    def add_ticket(self, ticket_data):
        ticket_id, ticket_title, ticket_author, ticket_status = ticket_data
        if ticket_status == TicketStatus.NEW:
            ticket_widget = NewTicketItem(text=f"[b]{ticket_title}[/b][size=30sp]\n{ticket_author}[/size]")
            try:
                print("AUDIO_BOOL !!!!!")
                print(self.config.get('Audio', 'audio_bool'))
                if self.config.getboolean('Audio', 'audio_bool') and self.new_ticket_sound:
                    self.new_ticket_sound.play()
            except KeyError:
                for k, v in self.config:
                    print(f"{k}: {v}")
                self.stop()
        elif ticket_status == TicketStatus.OPEN:
            ticket_widget = TicketItem(text=f"[b]{ticket_title}[/b][size=30sp]\n{ticket_author}[/size]")
        elif ticket_status == TicketStatus.PINNED:
            ticket_widget = PinnedTicketItem(text=f"[size=30sp][b]{ticket_title}[/b][/size][size=20sp]\n{ticket_author}[/size]")
        else:
            ticket_widget = None

        self.ticket_widgets[ticket_id] = ticket_widget
        self.all_tickets.add(ticket_data)
        if ticket_status in [TicketStatus.NEW, TicketStatus.OPEN]:
            self.root.ids.tickets.add_widget(ticket_widget)

        else:
            self.root.ids.pins.add_widget(ticket_widget)

    def remove_ticket(self, ticket_data):
        ticket_id, ticket_title, ticket_author, ticket_status = ticket_data
        try:
            ticket = self.ticket_widgets.pop(ticket_id)
            self.all_tickets.remove(ticket_data)

            def callback_open(*_):
                self.root.ids.tickets.remove_widget(ticket)

            def callback_pinned(*_):
                self.root.ids.pins.remove_widget(ticket)

            animation = Animation(opacity=0, duration=5)

            if ticket_status in [TicketStatus.NEW, TicketStatus.OPEN]:
                animation.bind(on_complete=callback_open)
            else:
                animation.bind(on_complete=callback_pinned)

            animation.start(ticket)

        except KeyError:
            pass

    def get_tickets_from_sheet(self, *_):
        try:
            self.sheet.refresh()
            ws = self.sheet.sheets[0]
            # print(ws.title, ws.columnCount, ws.rowCount)
            ws.getRows()

            current_tickets = set()

            for row in ws:
                ticket_status = row[8]

                if ticket_status in [TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.PINNED]:
                    ticket_id = row[9]
                    ticket_title = re.sub(r"re: |fwd: |\[EXTERNAL\] ", "", row[3], flags=re.I)
                    ticket_author = row[2]
                    current_tickets.add((ticket_id, ticket_title, ticket_author, ticket_status))

            for ticket in self.all_tickets.difference(current_tickets):
                self.remove_ticket(ticket)

            for ticket in current_tickets.difference(self.all_tickets):
                self.add_ticket(ticket)

            num_open_tickets = len([t for t in self.all_tickets if t[3] != TicketStatus.PINNED])
            num_pins = len([t for t in self.all_tickets if t[3] == TicketStatus.PINNED])

            self.root.ids.ticket_header.text = f"[b]{num_open_tickets}[/b] Open Ticket{'s' if num_open_tickets != 1 else ''}"
            self.root.ids.pins_header.text = f"[b]{num_pins}[/b] Pinned Item{'s' if num_pins != 1 else ''}"

        except ConnectionResetError:
            t = ('ConnectionResetError', 'Connection Error', 'EZSheets', 'NEW')
            self.add_ticket(t)

    def rotate_tickets(self, n):
        if len(self.ticket_widgets) > 0:
            self.current_ticket += 1
            if self.current_ticket >= len(self.ticket_widgets):
                self.current_ticket = 0
            try:
                self.active_ticket.size_hint = (0.2, None)
            except Exception:
                pass

            try:
                [widget] = [w for e, w in list(enumerate(self.ticket_widgets)) if e == self.current_ticket]
                self.active_ticket = self.ticket_widgets[widget]
                self.active_ticket.size_hint = (.8, None)

            except KeyError as e:
                print(e)

    def init_sheet(self, n):
        self.sheet = ezsheets.Spreadsheet('1-XlENZVrZ9oYx6UqIUi5V3eq0l3RPDCfeXIyB6TC2NA')

    def on_start(self):
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_once(self.init_sheet, 0.1)
        Clock.schedule_once(self.get_tickets_from_sheet, 5)
        Clock.schedule_interval(self.get_tickets_from_sheet, 60*1)
        # Clock.schedule_interval(self.rotate_tickets, 3)


if __name__ == "__main__":
    TicketronApp().run()
