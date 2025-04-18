from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.geometry import clamp
from textual.widgets import Static, Markdown, Button

from enum import Enum, auto

import api_client


class Card(Static):
    def __init__(self, info: dict) -> None:
        super().__init__()
        self.info = info
        self.title_widget = Static(self.info["title"]["romaji"], classes="title")
        self.progress = self.info["mediaListEntry"]["progress"]
        if self.info["status"] == "FINISHED":
            self.max_progress = self.info["episodes"]
        elif self.info["nextAiringEpisode"] is None:
            self.max_progress = self.progress
        else:
            self.max_progress = self.info["nextAiringEpisode"]["episode"] - 1

        self.progress_widget = Progress(self)
        self.description_widget = Markdown(self.info["description"], id="description")

        self.container_widget = Container(
            self.title_widget, self.progress_widget, self.description_widget
        )

        self.deactivate()

    def compose(self) -> ComposeResult:
        yield self.container_widget

    def on_click(self) -> None:
        if self.has_class("active"):
            self.deactivate()
        else:
            self.activate()

    def activate(self) -> None:
        self.add_class("active")
        self.container_widget.styles.height = "auto"
        self.progress_widget.styles.display = "block"
        self.description_widget.styles.display = "block"

    def deactivate(self) -> None:
        self.remove_class("active")
        self.container_widget.styles.height = None
        self.progress_widget.styles.display = "none"
        self.description_widget.styles.display = "none"


class ProgressStates(Enum):
    next_episode_unavailable = auto()
    next_episode_available = auto()
    finding_torrent = auto()
    downloading = auto()
    downloaded = auto()


class Progress(VerticalScroll):
    def __init__(self, card: Card) -> None:
        super().__init__()

        self.progress = card.progress
        self.max_progress = card.max_progress
        self.media_id = card.info["id"]
        self.titles = card.info["title"]
        self.title = self.titles["romaji"]
        self.minus_button = Button("-", disabled=self.progress == 0, id="minus")
        self.plus_button = Button(
            "+", disabled=self.progress == self.max_progress, id="plus"
        )
        self.middle_button = Button(str(self.progress), disabled=True, id="middle")
        self.state_button = Button("Loading", id="state")
        self.parent_widget = card
        self.set_state()

    def compose(self) -> ComposeResult:
        yield Horizontal(
            self.minus_button, self.middle_button, self.plus_button, classes="buttons"
        )
        yield Horizontal(self.state_button, classes="statebutton")

    def set_state(self) -> None:
        if self.progress == self.max_progress:
            self.set_next_episode_unavailable()
            if self.parent_widget.has_class("highlight"):
                self.parent_widget.remove_class("highlight")
        else:
            self.set_next_episode_available()

            if not self.parent_widget.has_class("highlight"):
                self.parent_widget.add_class("highlight")

    def set_next_episode_unavailable(self) -> None:
        self.state = ProgressStates.next_episode_unavailable

    def set_next_episode_available(self) -> None:
        self.state = ProgressStates.next_episode_available

        self.update_buttons()
        self.state_button.disabled = False
        self.state_button.label = f"⬇️ {self.progress + 1}"

    def set_downloading(self) -> None:
        self.state = ProgressStates.downloading

        self.download_timer = self.set_interval(5, self.download)

    def set_downloaded(self, stop_timer=True) -> None:
        self.state = ProgressStates.downloaded
        if stop_timer:
            self.download_timer.stop()
        self.state_button.label = f"▶️ {self.progress + 1}"
        self.state_button.disabled = False

        self.update_buttons()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "minus":
                self.progress = max(0, self.progress - 1)
                await self.update_progress()
            case "plus":
                self.progress = min(self.max_progress, self.progress + 1)
                await self.update_progress()
            case "state":
                match self.state:
                    case ProgressStates.next_episode_available:
                        self.state = ProgressStates.finding_torrent
                        self.state_button.disabled = True
                        self.plus_button.disabled = True
                        self.minus_button.disabled = True
                        self.state_button.label = "↺ Finding torrent"
                        try:
                            self.info_hash = api_client.download(
                                self.media_id, self.progress + 1
                            )["msg"].split()[-1]
                        except Exception as e:
                            print(e)
                            self.set_next_episode_available()
                            return

                        self.set_downloading()

                    case ProgressStates.downloaded:
                        print("give the scp command")

    async def update_progress(self) -> None:
        api_client.set_progress(self.media_id, self.progress)

        self.middle_button.label = str(self.progress)
        self.update_buttons()
        self.set_state()

    def update_buttons(self) -> None:
        self.minus_button.disabled = self.progress == 0
        self.plus_button.disabled = self.progress == self.max_progress

    def download(self) -> None:
        for torrent in api_client.get_torrents():
            print(torrent["hash"], self.info_hash)
            if torrent["hash"] == self.info_hash:
                print(torrent)
                progress = clamp(torrent["progress"], 0.0, 100.0)
                self.state_button.label = f"{progress:.2f} %"
                if abs(progress - 100.0) <= 0.01:
                    self.set_downloaded()
