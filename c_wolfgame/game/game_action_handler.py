# game_action_handler.py
import logging
from .models import GameSession, GamePlayer

class GameActionHandler:
    def __init__(self, game_id, controller, game_store):
        self.game_id = game_id
        self.controller = controller
        self.game_store = game_store
        self.logger = logging.getLogger(__name__)

    def handle_action(self, player_id, action_type, target_id, session):
        """Process a player's action"""
        try:
            # Log action to MongoDB
            self.game_store.add_action(
                session_id=self.game_id,
                player_id=player_id,
                action_type=action_type,
                target_id=target_id,
                round_number=session.round_count,
                phase=session.current_phase
            )

            # Submit action through controller
            success, message = self.controller.login_player(player_id)
            if not success:
                return False, message

            success, message = self.controller.submit_action(action_type, target_id)
            if not success:
                return False, message

            return True, "Action processed successfully"

        except Exception as e:
            self.logger.error(f"Error handling action: {e}")
            return False, str(e)