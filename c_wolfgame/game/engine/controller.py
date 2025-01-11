from typing import Tuple, Dict, List, Optional
from .types import GameAction


class GameController:
    def __init__(self, game):
        self.game = game
        self.action_queue: List[GameAction] = []
        self.current_player_id: Optional[str] = None
        self.policeman_candidates: List[str] = []
        self.policeman_votes: Dict[str, List[str]] = {}

    def login_player(self, player_id: str) -> Tuple[bool, str]:
        player = self.game.get_player(player_id)
        if not player:
            return False, "Invalid player ID"
        self.current_player_id = player_id
        return True, f"Logged in as {player.name}"

    def submit_action(self, action_type: str, target_id: Optional[str] = None) -> Tuple[bool, str]:
        if not self.current_player_id:
            return False, "Not logged in"

        player = self.game.get_player(self.current_player_id)
        if not player.is_alive():
            return False, "Dead players cannot perform actions"

        action = GameAction(self.current_player_id, action_type, target_id)
        self.action_queue.append(action)
        return True, "Action submitted successfully"
