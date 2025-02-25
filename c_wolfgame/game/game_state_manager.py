# game_state_manager.py
import logging
from channels.db import database_sync_to_async
from .models import GameSession, GamePlayer

class GameStateManager:
    def __init__(self, game_id):
        self.game_id = game_id
        self.logger = logging.getLogger(__name__)

    async def get_current_state(self):
        """Get current game state"""
        try:
            session = await database_sync_to_async(GameSession.objects.get)(session_id=self.game_id)
            players = await database_sync_to_async(list)(GamePlayer.objects.filter(game_session=session))

            return {
                'type': 'game_state',
                'phase': session.current_phase,
                'players': [await self._format_player(player) for player in players],
                'round': session.round_count
            }
        except Exception as e:
            self.logger.error(f"Error getting game state: {e}")
            raise

    @database_sync_to_async
    def _format_player(self, player):
        """Format player data for state updates"""
        position = int(player.player_id.replace('p', '')) + 1
        return {
            'player_id': player.player_id,
            'name': f"Player {position}",
            'role': player.role,
            'status': player.status,
            'is_policeman': player.is_policeman,
            'running_for_policeman': player.running_for_policeman,
            'position': position
        }

    @database_sync_to_async
    def update_phase(self, new_phase, session):
        """Update game phase"""
        try:
            session.current_phase = new_phase
            if new_phase == 'DAY':
                session.round_count += 1
            session.save()
            self.logger.info(f"Updated phase to {new_phase}, round {session.round_count}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating phase: {e}")
            return False