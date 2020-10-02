import asyncio
import re
from types import SimpleNamespace
import gspread_asyncio
from google.oauth2 import service_account


def get_credentials():
    scopes = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://spreadsheets.google.com/feeds'
    ]
    return service_account.Credentials.from_service_account_file('ticketron.json', scopes=scopes)


gspread_manager = gspread_asyncio.AsyncioGspreadClientManager(get_credentials)

TicketStatus = SimpleNamespace(
    NEW="0 - New", OPEN="1 - Open", PINNED="8 - Pinned", CLOSED="9 - Closed"
)


async def get_tickets():
    tickets = set()
    gspread = await gspread_manager.authorize()

    ss = await gspread.open_by_key("1-XlENZVrZ9oYx6UqIUi5V3eq0l3RPDCfeXIyB6TC2NA")

    tickets_sheet = await ss.get_worksheet(0)

    for row in await tickets_sheet.get_all_records():
        if row["Status"] in [
            TicketStatus.NEW,
            TicketStatus.OPEN,
            TicketStatus.PINNED,
        ]:
            # ticket_messages = row[5].replace("\r", " ")
            row["Title"] = re.sub(
                r"re: |fwd: |\[EXTERNAL\] ", "", row["Title"], flags=re.I
            )
            row["Messages"] = re.sub(
                r"\r", "\n", row["Messages"], flags=re.I
            )
            tickets.add(frozenset(row.items()))
    return tickets


async def get_stats():
    tickets = set()
    gspread = await gspread_manager.authorize()

    ss = await gspread.open_by_key("1-XlENZVrZ9oYx6UqIUi5V3eq0l3RPDCfeXIyB6TC2NA")

    summary_sheet = await ss.get_worksheet(1)

    closed_total_cell = await summary_sheet.acell("B7")

    return {
        'closed_total': closed_total_cell.value,
    }

'''
    while True:
        try:
            await self.sheet_refresh()
            ws = self.sheet.sheets[0]
            # print(ws.title, ws.columnCount, ws.rowCount)
            # print(ws)
            ws.getRows()
            # print(ws.getRows())

            current_tickets = set()
            print("Start")
            print(datetime.today())

            for row in ws:
                ticket_status = row[8]

                if ticket_status in [
                    TicketStatus.NEW,
                    TicketStatus.OPEN,
                    TicketStatus.PINNED,
                ]:
                    ticket_id = row[9]
                    ticket_title = re.sub(
                        r"re: |fwd: |\[EXTERNAL\] ", "", row[3], flags=re.I
                    )
                    ticket_author = row[2]
                    
                    current_tickets.add(
                        (ticket_id, ticket_title, ticket_author, ticket_status)
                    )
                    self.all_ticket_messages[ticket_id] = ticket_messages

            for ticket in self.all_tickets.difference(current_tickets):
                self.remove_ticket(ticket)

            for ticket in current_tickets.difference(self.all_tickets):
                self.add_ticket(ticket)

            num_open_tickets = len(
                [t for t in self.all_tickets if t[3] != TicketStatus.PINNED]
            )
            num_pins = len([t for t in self.all_tickets if t[3] == TicketStatus.PINNED])

            closed_total = self.sheet.sheets[1].get('B7')

            self.root.ids.ticket_header.text = f"[b]{num_open_tickets}[/b] Open Ticket{'s' if num_open_tickets != 1 else ''} [sup][font=FontAwesome][/font] [b]{closed_total}[/b][/sup]"
            self.root.ids.pins_header.text = (
                f"[b]{num_pins}[/b] Pinned Item{'s' if num_pins != 1 else ''}"
            )

            print("End")
            print(datetime.today())

        except ConnectionResetError as e:
            t = ("ConnectionResetError", e.strerror, "EZSheets", "NEW")
            self.add_ticket(t)

        except socket.timeout as e:
            t = ("SocketTimeout", e.strerror, "EZSheets", "NEW")
            self.add_ticket(t)

        except AttributeError as e:
            print(e)

        await trio.sleep(15)
'''