"""holds the playerctl service"""
import os
from gi.repository import Playerctl
from fabric.core.service import Service, Signal


class SimplePlayerctlService(Service):
    """Simple, lightweight service for MPRIS players"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.manager = Playerctl.PlayerManager()
        self.players = {}  # player_name -> Playerctl.Player

        # Connect manager signals
        self.manager.connect("name-appeared", self._on_player_appeared)
        self.manager.connect("name-vanished", self._on_player_vanished)

        # Discover existing players
        self._discover_players()

    def _discover_players(self):
        """Find all available players"""
        for name in self.manager.props.player_names:

            if name.name not in self.players:
                try:
                    player = Playerctl.Player.new_from_name(name)
                    # player.connect("metadata",lambda _: self.emit_update())
                    self._connect_player_signals_with_emits(player)
                    self.players[name.name] = player
                except:
                    pass

    def _connect_player_signals_with_emits(self, player) -> Playerctl.Player:
        signals = ["metadata", "loop-status", "seeked", "shuffle"]
        for signal in signals:
            player.connect(signal, lambda _: (self.emit_update(), False))
        for signal in [
            "playback-status::playing",
            "playback-status::paused",
            "playback-status::ended",
        ]:
            player.connect(signal, lambda _: (self.emit_track_status(), False))

    def _on_player_appeared(self, manager, name):
        """Handle new player"""
        print(f"add_player {name.name}")

        if name.name not in self.players:
            try:
                player = Playerctl.Player.new_from_name(name)
                self._connect_player_signals_with_emits(player)

                self.players[name.name] = player
            except:
                pass

    @Signal
    def track_change(self) -> None: ...
    @Signal
    def track_status_change(self) -> None: ...

    def emit_track_status(self):
        self.emit("track-status-change")

    def emit_update(self):
        # print("emitting after recieving metadata signal")
        self.notify("changed")
        self.emit("track-change")
        return False

    def _on_player_vanished(self, manager, player):
        """Handle player disappearing"""
        print(f"player {player.name} vanished")

        player_name = player.name
        if player_name in self.players:
            del self.players[player_name]
        self.emit("track-change")

    def get_players(self):
        """Get list of all player names"""
        return list(self.players.keys())

    def get_metadata(self, player_name=None):
        """Get metadata for player (or first available player if None)"""
        if not self.players:
            return None

        if len(self.players.keys()) == 0:
            return None
        if player_name is None:
            # print(self.players)
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return None

        player = self.players[player_name]
        try:
            metadata = player.props.metadata
            if not metadata:
                return None

            # Extract basic info
            # print(metadata)
            title = self._get_variant_string(metadata.lookup_value("xesam:title", None))
            artist = self._get_variant_artist(
                metadata.lookup_value("xesam:artist", None)
            )
            album = self._get_variant_string(metadata.lookup_value("xesam:album", None))
            art_url = self._get_variant_string(
                metadata.lookup_value("mpris:artUrl", None)
            )
            length = self._get_variant_int(metadata.lookup_value("mpris:length", None))
            # print(length)
            return {
                "title": title,
                "artist": artist,
                "album": album,
                "art_url": art_url,
                "length": length / 1000000 if length > 0 else 0,  # Convert to seconds
                "player_name": player_name,
            }
        except Exception as e:
            print(e)
            return None

    def get_position(self, player_name=None):
        """Get current position in seconds"""
        if not self.players:
            return 0

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return 0

        try:
            position = self.players[player_name].props.position
            # print("position: ",position)
            return position / 1000000 if position > 0 else 0  # Convert to seconds
        except:
            return 0

    def set_position(self, position, player_name=None):
        if not self.players:
            return 0

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return 0

        try:
            player: Playerctl.Player = self.players[player_name]
            player.set_position(int(position * 1e6))
        except Exception as e:
            print(e)

    def get_status(self, player_name=None):
        """Get playback status"""
        if not self.players:
            return "stopped"

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return "stopped"

        try:
            status = self.players[player_name].props.playback_status
            if hasattr(status, "value_nick"):
                return status.value_nick.lower()
            else:
                return str(status).split(".")[-1].lower()
        except:
            return "stopped"

    def get_shuffle(self, player_name=None):
        """Get shuffle status"""
        if not self.players:
            return False

        if player_name is None:
            player_name = list(self.players.keys())[0]
            try:
                return bool(self.players[player_name].props.shuffle)
            except:
                return False

        if player_name not in self.players:
            return False

    def get_loop(self, player_name=None):
        """Get loop status"""
        if not self.players:
            return "none"

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return "none"

        try:
            loop_status = self.players[player_name].props.loop_status
            if hasattr(loop_status, "value_nick"):
                return loop_status.value_nick.lower()
            else:
                return str(loop_status).split(".")[-1].lower()
        except:
            return "none"

    # Control methods
    def play_pause(self, player_name=None):
        """Toggle play/pause"""
        if not self.players:
            return False

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return False

        try:
            self.players[player_name].play_pause()
            return True
        except:
            return False

    def next_track(self, player_name=None):
        """Next track"""
        if not self.players:
            return False

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return False

        try:
            self.players[player_name].next()
            return True
        except:
            return False

    def previous_track(self, player_name=None):
        """Previous track"""
        if not self.players:
            return False

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return False

        try:
            self.players[player_name].previous()
            return True
        except:
            return False

    def toggle_shuffle(self, player_name=None):
        """Toggle shuffle"""
        if not self.players:
            return False

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return False

        try:
            current = self.players[player_name].props.shuffle
            self.players[player_name].set_shuffle(not current)
            return True
        except:
            return False

    def cycle_loop(self, player_name=None):
        """Cycle loop mode"""
        if not self.players:
            return False

        if player_name is None:
            player_name = list(self.players.keys())[0]

        if player_name not in self.players:
            return False

        try:
            current = self.players[player_name].props.loop_status
            if current == Playerctl.LoopStatus.NONE:
                new_status = Playerctl.LoopStatus.PLAYLIST
            elif current == Playerctl.LoopStatus.PLAYLIST:
                new_status = Playerctl.LoopStatus.TRACK
            else:
                new_status = Playerctl.LoopStatus.NONE

            self.players[player_name].set_loop_status(new_status)
            return True
        except:
            return False

    def _cleanup_temp(self):
        """Clean up temp files"""
        if self.temp_art_path and os.path.isfile(self.temp_art_path):
            try:
                os.remove(self.temp_art_path)
            except:
                pass
            self.temp_art_path = None

    # Helper methods for variant conversion
    def _get_variant_string(self, variant):
        """Convert variant to string"""
        if variant is None:
            return ""
        try:
            return str(variant.get_string())
        except:
            try:
                return str(variant.unpack())
            except:
                return ""

    def _get_variant_artist(self, variant):
        """Convert variant to artist string (handle arrays)"""
        if variant is None:
            return ""
        try:
            artist_data = variant.unpack()
            if isinstance(artist_data, list) and len(artist_data) > 0:
                return str(artist_data[0])
            else:
                return str(artist_data)
        except:
            return self._get_variant_string(variant)

    def _get_variant_int(self, variant):
        """Convert variant to int - FIXED for uint64"""
        if variant is None:
            return 0
        try:
            # First try to unpack - this should work for any variant type
            value = variant.unpack()
            return int(value)
        except:
            try:
                # Fallback: try different getter methods
                if hasattr(variant, "get_uint64"):
                    return int(variant.get_uint64())
                elif hasattr(variant, "get_int64"):
                    return int(variant.get_int64())
                # ... other types
            except Exception as e:
                print(f"Error converting variant to int: {e}")
                return 0
