import asyncio

from types import SimpleNamespace
from time import strftime

from kivy.app import App

from kivy.animation import Animation
from kivy.core.text import LabelBase
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.core.audio import SoundLoader
from kivy.logger import Logger

from views.sheets import get_tickets, get_stats, close_ticket, pin_ticket

LabelBase.register(
    name="Roboto",
    fn_regular="assets/fonts/Roboto-Thin.ttf",
    fn_bold="assets/fonts/Roboto-Medium.ttf",
)

LabelBase.register(
    name="FontAwesome",
    fn_regular="assets/fonts/Font-Awesome-5-Pro-Regular-400.ttf",
)


TicketStatus = SimpleNamespace(
    NEW="0 - New", OPEN="1 - Open", PINNED="8 - Pinned", CLOSED="9 - Closed"
)


class DashboardScreen(Screen):
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


class InfoScroll(ScrollView):
    pass


class InfoLabel(Label):
    pass


class WindowManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg_texture = Image(source="assets/images/bg.jpg")


class TicketronApp(App):
    """
    Main app class - Receives styling / layout from ticketron.kv (Kivy syntax)
    """
    update_time_task = None
    sheet_refresh_task = None

    def app_func(self):
        self.update_time_task = asyncio.ensure_future(self.update_time())
        self.sheet_refresh_task = asyncio.ensure_future(self.sheet_refresh())

        async def run_wrapper():
            # we don't actually need to set asyncio as the lib because it is
            # the default, but it doesn't hurt to be explicit
            await self.async_run(async_lib='asyncio')
            print('App done')
            self.update_time_task.cancel()
            self.sheet_refresh_task.cancel()

        return asyncio.gather(run_wrapper(), self.update_time_task, self.sheet_refresh_task)

    def __init__(self):
        super().__init__()
        self.all_tickets = set()
        self.all_pins = set()

        self.ticket_widgets = (
            {}
        )  # Hold reference to individual widgets, referenced by ticket ID
        self.all_ticket_messages = (
            {}
        )
        self.current_ticket = 0  # For rotation - not currently used
        self.active_ticket = None  # For rotation - not currently used
        self.sheet = None  # To hold Google Sheet - initialized with a Clock.schedule_once to avoid startup lag
        self.new_ticket_sound = SoundLoader.load(
            "assets/audio/chime.wav"
        )  # New ticket sound

    def build_config(self, config):
        """
        Set the default values for the configs sections.
        """
        config.setdefaults(
            "Audio", {"audio_alerts": True, "font-size": 20, "value": ["True", "False"]}
        )

    def build_settings(self, settings):
        """
        Add our custom section to the default configuration object.
        """
        settings.add_json_panel("Audio", self.config, "config/ticketron.json")

    def on_config_change(self, config, section, key, value):
        """
        Respond to changes in the configuration.
        """
        Logger.info(
            f"main.py: App.on_config_change: {config}, {section}, {key}, {value}"
        )

    def close_settings(self, settings=None):
        """
        The settings panel has been closed.
        """
        Logger.info(f"main.py: App.close_settings: {settings}")
        super().close_settings(settings)

    async def update_time(self):
        while True:
            try:
                self.root.ids.time.text = strftime("%-I:%M")
                self.root.ids.seconds.text = strftime("%S ")
                self.root.ids.ampm.text = strftime("[b]%p[/b]")
                self.root.ids.calendar.text = strftime("[b]%A[/b] %B %-d")
            except Exception as e:
                print(e)
            await asyncio.sleep(1)

    def add_pin(self, pin_data):
        t = PinnedTicketItem(
            text=f"[size=30sp][b]{pin_data[1]}[/b][/size][size=15sp]\n{pin_data[2]}[/size]"
        )
        self.all_pins.add(pin_data)
        self.root.ids.pins.add_widget(t)

    def add_ticket(self, ticket_data):
        # ticket_id, ticket_title, ticket_author, ticket_status = ticket_data
        ticket = dict(ticket_data)
        show_ticket_callback = lambda t:self.show_ticket_info(ticket_data)
        if ticket["Status"] == TicketStatus.NEW:
            ticket_widget = NewTicketItem(
                text=f"[b]{ticket['Title']}[/b][size=30sp]\n{ticket['Requested By']}[/size]",
                on_press=show_ticket_callback
            )
            try:
                print("audio_alerts !!!!!")
                print(self.config.get("Audio", "audio_alerts"))
                if (
                    self.config.getboolean("Audio", "audio_alerts")
                    and self.new_ticket_sound
                ):
                    self.new_ticket_sound.play()
            except KeyError:
                for k, v in self.config:
                    print(f"{k}: {v}")
                self.stop()
        elif ticket["Status"] == TicketStatus.OPEN:
            ticket_widget = TicketItem(
                text=f"[b]{ticket['Title']}[/b][size=30sp]\n{ticket['Requested By']}[/size]",
                on_press=show_ticket_callback
            )
        elif ticket["Status"] == TicketStatus.PINNED:
            ticket_widget = PinnedTicketItem(
                text=f"[size=30sp][b]{ticket['Title']}[/b][/size][size=20sp]\n{ticket['Requested By']}[/size]",
                on_press=show_ticket_callback
            )
        else:
            ticket_widget = None

        self.ticket_widgets[ticket["ID"]] = ticket_widget
        self.all_tickets.add(ticket_data)
        if ticket["Status"] in [TicketStatus.NEW, TicketStatus.OPEN]:
            self.root.ids.tickets.add_widget(ticket_widget)
        else:
            self.root.ids.pins.add_widget(ticket_widget)

    def remove_ticket(self, ticket_data):
        ticket = dict(ticket_data)

        try:
            ticket_widget = self.ticket_widgets.pop(ticket["ID"])
            self.all_tickets.remove(ticket_data)

            def callback_open(*_):
                self.root.ids.tickets.remove_widget(ticket_widget)

            def callback_pinned(*_):
                self.root.ids.pins.remove_widget(ticket_widget)

            animation = Animation(opacity=0, duration=5)

            if ticket["Status"] in [TicketStatus.NEW, TicketStatus.OPEN]:
                animation.bind(on_complete=callback_open)
            else:
                animation.bind(on_complete=callback_pinned)

            animation.start(ticket_widget)

        except KeyError:
            pass

    def show_ticket_info(self, ticket_data):
        ticket = dict(ticket_data)
        view = Popup(size_hint=(0.8, 0.8), title=ticket['Title'])
        layout = BoxLayout(orientation='vertical')
        scrollview = InfoScroll(size_hint=(1, 0.8))
        scrollview.add_widget(InfoLabel(text=f"{ticket['Messages']}"))
        layout.add_widget(scrollview)

        def button_callback_close(t):
            close_ticket(ticket['ID'])
            self.remove_ticket(ticket_data)
            view.dismiss()

        def button_callback_pin(t):
            pin_ticket(ticket['ID'])
            self.remove_ticket(ticket_data)
            view.dismiss()

        layout.add_widget(Button(text='Close Ticket', size_hint=(1, 0.2), on_press=button_callback_close))
        layout.add_widget(Button(text='Pin Ticket', size_hint=(1, 0.2), on_press=button_callback_pin))
        view.add_widget(layout)
        view.open()


    async def sheet_refresh(self):

        while True:
            current_tickets = await get_tickets()

            for ticket in self.all_tickets.difference(current_tickets):
                self.remove_ticket(ticket)

            for ticket in current_tickets.difference(self.all_tickets):
                self.add_ticket(ticket)

            num_open_tickets = len(
                [t for t in self.all_tickets if dict(t)["Status"] != TicketStatus.PINNED]
            )
            num_pins = len([t for t in self.all_tickets if dict(t)["Status"] == TicketStatus.PINNED])

            stats = await get_stats()
            closed_total = stats["closed_total"]

            self.root.ids.ticket_header.text = f"[b]{num_open_tickets}[/b] Open Ticket{'s' if num_open_tickets != 1 else ''} [sup][font=FontAwesome][/font] [b]{closed_total}[/b][/sup]"
            self.root.ids.pins_header.text = (
                f"[b]{num_pins}[/b] Pinned Item{'s' if num_pins != 1 else ''}"
            )
            await asyncio.sleep(15)



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
                [widget] = [
                    w
                    for e, w in list(enumerate(self.ticket_widgets))
                    if e == self.current_ticket
                ]
                self.active_ticket = self.ticket_widgets[widget]
                self.active_ticket.size_hint = (0.8, None)

            except KeyError as e:
                print(e)


    def on_start(self):
        pass
        # Clock.schedule_interval(self.update_time, 1)
        # Clock.schedule_once(self.init_sheet, 0.1)
        # Clock.schedule_once(self.get_tickets_from_sheet, 5)
        # Clock.schedule_interval(self.get_tickets_from_sheet, 15)
        # Clock.schedule_interval(self.rotate_tickets, 3)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(TicketronApp().app_func())
    loop.close()

