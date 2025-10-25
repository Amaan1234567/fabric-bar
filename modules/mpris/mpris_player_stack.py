"""mpris players stack"""

from loguru import logger
from gi.repository import Playerctl  # type: ignore
from fabric.widgets.stack import Stack
from fabric.utils.helpers import cooldown
from modules.mpris.mpris_player import MprisPlayer
from services.playerctlservice import SimplePlayerctlService, Player


class MprisPlayerStack(Stack):
    """mpris popup widget which shows more song details,progressbar and controls"""

    def __init__(self, **kwargs):
        super().__init__(
            name="mpris-stack",
            transition_type="slide-left-right",
            transition_duration=200,
            **kwargs,
        )
        self.add_events("scroll")
        self._service = SimplePlayerctlService()
        self.players = {}
        self._visible_child_index = 0
        self._create_players()

        self.connect("scroll-event", self._on_scroll_handler)

    def _create_players(self):
        self._service.manager.connect("name-appeared", self._add_player)
        self._service.manager.connect("name-vanished", self._remove_player)
        players: dict[str, Player] = self._service.players
        for _, player in players.items():
            mpris_player = MprisPlayer(player)
            self.add(mpris_player)
            self.players[player.name] = mpris_player
            player.connect(
                "changed",
                lambda player: self.set_visible_child(self.players[player.name]),
            )

    def _add_player(self, _, player_name: Playerctl.PlayerName):
        name = player_name.name
        new_player = MprisPlayer(self._service.players[name])
        self.players[name] = new_player
        self.set_visible_child(new_player)
        self.add(new_player)

    def _remove_player(self, _, player_name: Playerctl.PlayerName):
        logger.info(f"deleted {player_name.name} player")
        if len(self.players) == 0:
            return
        widget = self.players.pop(player_name.name)
        print(self.players)
        self.remove(widget)

    @cooldown(0.2)
    def _on_scroll_handler(self, _, event):

        if len(self.players) == 0:
            return
        self._visible_child_index = (
            self._visible_child_index + (-1 if event.direction == 0 else 1)
        ) % len(self.children)

        return self.set_visible_child(self.children[self._visible_child_index])
