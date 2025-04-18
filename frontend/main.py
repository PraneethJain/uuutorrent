from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import (
    Static,
    Header,
    Footer,
    Markdown,
    ContentSwitcher,
    Button,
    Input,
)
from textual.validation import Function

from os import path

from card import Card

import api_client


class Cards(VerticalScroll):
    def __init__(self, card_data, id: str) -> None:
        super().__init__(id=id)
        self.card_data = card_data

    async def on_mount(self) -> None:
        cards = set(map(Card, self.card_data))
        highlighted_cards = {card for card in cards if card.has_class("highlight")}
        other_cards = cards - highlighted_cards
        for card in highlighted_cards:
            await self.mount(card)
        for card in other_cards:
            await self.mount(card)


class Settings(VerticalScroll):
    def __init__(self, download_path: str, id: str) -> None:
        super().__init__(id=id)
        self.download_path = download_path
        self.download_path_input = Input(
            placeholder=download_path,
            validators=[Function(path.exists, "Path does not exist!")],
            id="download-path-input",
        )

        if path.exists(self.download_path):
            self.download_path_status = Markdown(f"Download Path: {self.download_path}")
        else:
            self.download_path_status = Markdown("Invalid download path")

    # @on(Input.Submitted, "#download-path-input")
    # def update_download_path(self, event: Input.Submitted):
    #     if event.validation_result.is_valid:
    #         self.download_path = event.value
    #         with open(data_path, "r") as f:
    #             data = load(f)
    #         data["download_path"] = self.download_path
    #         self.download_path_input.placeholder = self.download_path
    #         with open(data_path, "w") as f:
    #             dump(data, f)
    #         self.download_path_status.update(f"Download Path: {self.download_path}")

    def compose(self) -> ComposeResult:
        yield self.download_path_status
        yield self.download_path_input


class Switcher(Static):

    async def on_mount(self) -> None:
        user_list_data = api_client.get_watchlist()
        card_data = [list["media"] for list in user_list_data]

        await self.mount(
            Horizontal(
                Button("Anime", id="anime"),
                # Button("Profile", id="profile"),
                # Button("Settings", id="settings"),
                id="context-buttons",
            )
        )
        await self.mount(
            ContentSwitcher(
                Cards(card_data, id="anime"),
                # Markdown("Profile Info", id="profile"),
                # Settings(download_path="", id="settings"),
                initial="anime",
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["anime", "profile", "settings"]:
            self.query_one(ContentSwitcher).current = event.button.id

    async def on_quit(self) -> None:
        pass
        # await gather(ani.close(), scraper.close())


class UUUTorrent(App):
    CSS_PATH = "style.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        yield Switcher()


if __name__ == "__main__":
    app = UUUTorrent()
    app.run()
