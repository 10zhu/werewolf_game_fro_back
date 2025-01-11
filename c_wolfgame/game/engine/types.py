from enum import Enum
from dataclasses import dataclass
from typing import Optional

class GamePhase(Enum):
    SETUP = 1
    NIGHT = 2
    POLICEMAN_SELECTION = 3
    DAY = 4
    VOTING = 5
    GAME_OVER = 6

class PlayerStatus(Enum):
    ALIVE = 1
    DEAD = 2

class Role(Enum):
    WEREWOLF = "WEREWOLF"
    VILLAGER = "VILLAGER"
    SEER = "SEER"
    WITCH = "WITCH"
    HUNTER = "HUNTER"
    IDIOT = "IDIOT"

@dataclass
class GameAction:
    player_id: str
    action_type: str
    target_id: Optional[str] = None
    success: bool = False
