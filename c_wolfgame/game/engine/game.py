from typing import Dict, Optional
import random
from .types import GamePhase, Role, PlayerStatus
from .controller import GameController

class Player:
    def __init__(self, player_id: str, name: str):
        self.player_id = player_id
        self.name = name
        self._role: Optional[Role] = None
        self._status = PlayerStatus.ALIVE
        self.is_policeman = False
        self.running_for_policeman = False

    def get_role(self) -> Role:
        return self._role

    def assign_role(self, role: Role):
        self._role = role

    def is_alive(self) -> bool:
        return self._status == PlayerStatus.ALIVE


class WerewolfGame:
    def __init__(self):
        self._players: Dict[str, Player] = {}
        self._current_phase = GamePhase.SETUP
        self._round_count = 1
        self._controller = GameController(self)
        self._witch_powers = {'heal': True, 'poison': True}

        for i in range(12):
            player_id = f"p{i}"
            self._players[player_id] = Player(player_id, f"Player {i}")

    def get_player(self, player_id: str) -> Optional[Player]:
        return self._players.get(player_id)

    def setup_game(self):
        roles = (
                [Role.WEREWOLF] * 4 +
                [Role.VILLAGER] * 4 +
                [Role.SEER] +
                [Role.WITCH] +
                [Role.HUNTER] +
                [Role.IDIOT]
        )

        random.shuffle(roles)
        for player, role in zip(self._players.values(), roles):
            player.assign_role(role)

        self._current_phase = GamePhase.NIGHT