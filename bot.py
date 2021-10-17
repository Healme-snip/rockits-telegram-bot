"""Google Sheets client."""
import json
import logging
import datetime
from typing import List
from pathlib import Path

from telegram import (
    Update,
    Bot,
)
from telegram.ext import (
    MessageHandler,
    Filters,
    Updater,
    CommandHandler,
    CallbackContext,
)
import telegram.error

import gspread
from gspread.models import Worksheet
from gspread.exceptions import WorksheetNotFound, SpreadsheetNotFound

from google.oauth2.service_account import Credentials


class GSheetConfig():
    """GSheet config."""

    service_account_file: str
    spreadsheet_title: str
    worksheet_title: str

    writer_emails: List[str]

    scopes: List[str] = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(
            self,
            secret_file: str,
            spreadsheet_title: str,
            worksheet_title: str,
            writer_emails: List[str]
    ):
        if not Path(secret_file).is_file():
            msg = f"Cannot find file google service account file {secret_file}"
            raise Exception(msg)
        self.service_account_file = secret_file
        self.spreadsheet_title = spreadsheet_title
        self.writer_emails = writer_emails
        self.worksheet_title = worksheet_title

    @property
    def creds(self) -> Credentials:
        """Creds."""
        return Credentials.from_service_account_file(
            self.service_account_file,
            scopes=self.scopes
        )


class GSheetClient():
    """Google Sheets client."""

    def __init__(
            self,
            config: GSheetConfig
    ):
        """Google Sheets client."""
        self._config: GSheetConfig = config
        self._creds = config.creds
        self._conn = None
        self.spreadsheet: gspread.Spreadsheet = None
        self.worksheet: gspread.Worksheet = None

    def _connect(self):
        if self._conn is None:
            self._conn = gspread.authorize(self._creds)
        if self.spreadsheet is None:
            try:
                self.spreadsheet = self._conn.open(
                    self._config.spreadsheet_title
                )
            except SpreadsheetNotFound:
                self.spreadsheet = self.__create_spreadsheet(
                    self._config.writer_emails
                )
        if self.worksheet is None:
            try:
                self.worksheet = self.spreadsheet.worksheet(
                    self._config.worksheet_title
                )
            except WorksheetNotFound:
                self.worksheet = self.__create_worksheet()

    def __create_spreadsheet(
            self,
            share_with: List[str]
    ) -> str:
        """Create spreadsheet."""
        self.spreadsheet = self._conn.create(self._config.spreadsheet_title)

        for email in share_with:
            self.spreadsheet.share(email, perm_type='user', role='writer')
        return self.spreadsheet

    def __create_worksheet(
            self,
            rows: int = 100,
            cols: int = 100
    ) -> Worksheet:
        """Get sheet."""
        # self._connect()
        sheet = self.spreadsheet.add_worksheet(
            title=self._config.worksheet_title,
            rows=rows,
            cols=cols
        )
        return sheet

    def share_spreadsheet(
            self,
            share_with: List[str]
    ):
        """Share spreadsheet."""
        self._connect()
        for email in share_with:
            self.spreadsheet.share(email, perm_type='user', role='writer')

    def list_sheets(
            self
    ) -> List[Worksheet]:
        """List sheets."""
        self._connect()
        return self.spreadsheet.worksheets()

    def delete_sheets(
            self,
            sheets: List[str]
    ):
        """Delete sheets."""
        self._connect()
        sheets_raw = self.list_sheets()
        available_sheets = {sheet.title: sheet for sheet in sheets_raw}
        for sheet in sheets:
            if available_sheets.get(sheet):
                self.spreadsheet.del_worksheet(available_sheets[sheet])

    def _next_available_row(self) -> int:
        str_list = list(filter(None, self.worksheet.col_values(1)))
        return len(str_list) + 1

    def append_row(self, row: List[str]):
        self._connect()
        next_row = self._next_available_row()
        if next_row >= 1000:
            self.worksheet.resize(next_row + 1)

        self.worksheet.append_row(row, value_input_option='USER_ENTERED')


class XLBot:
    """Image Bot."""

    name: str = "tg-bot"

    def __init__(
            self,
            token: str,
            gsheet_config: GSheetConfig
    ):
        """Create image bot."""
        self.updater = Updater(
            token=token,
            use_context=True
        )
        self.bot = Bot(
            token=token
        )
        self.gsheet = GSheetClient(config=gsheet_config)

    # Telegram callbacks

    def _tg_callback_start(self, update: Update, context: CallbackContext):
        if not update.effective_chat:
            return
        chat_id = update.effective_chat.id

        msg = f"/start by {chat_id}"
        logging.info(msg)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                r"Тестовое задание Снесарева М\. С\."
            ),
            parse_mode="MarkdownV2"
        )

    def _tg_callback_text(self, update: Update, context: CallbackContext):
        if not update.effective_chat:
            return

        chat_id = update.effective_chat.id

        message = update.message

        if message is None:
            return

        line = message.text

        if line is None:
            return

        raw_row = line.split(",")
        if len(raw_row) != 3 or not raw_row[2].strip().isnumeric():
            msg = ("Неверный формат строки")

        else:
            row = []
            row.append(datetime.datetime.utcnow().isoformat())
            row.append(raw_row[0].strip())
            row.append(raw_row[1].strip())
            row.append(str(int(raw_row[2])))

            self.gsheet.append_row(row)
            msg = ("Строка добавлена успешно")

        text = (
            msg
            .replace("-", r"\-")
            .replace(".", r"\.")
            .replace("(", r"\(")
            .replace(")", r"\)")
            .replace("[", r"\[")
            .replace("]", r"\]")
        )

        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="MarkdownV2"
            )
        except telegram.error.BadRequest as err:
            logging.warning(err)

    def start(self):
        """Start the bot."""
        dispatcher = self.updater.dispatcher

        # Commands
        start_handler = CommandHandler(
            'start',
            self._tg_callback_start
        )

        # Messages
        text_handler = MessageHandler(
            Filters.text,
            self._tg_callback_text
        )

        dispatcher.add_handler(start_handler)
        dispatcher.add_handler(text_handler)

        self.updater.start_polling()
        self.updater.idle()


def _main():

    with open("settings.json") as settings:
        config = json.load(settings)

    token = config["tg"]["token"]

    bot = XLBot(
        token=token,
        gsheet_config=GSheetConfig(**config["gsheet"])
    )
    bot.start()


if __name__ == "__main__":
    _main()
