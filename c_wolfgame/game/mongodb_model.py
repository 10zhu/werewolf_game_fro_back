from asyncio.log import logger
from typing import Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient
from django.conf import settings


class GameStateStore:
    def __init__(self):
        # Initialize MongoDB connection
        self.client = MongoClient(settings.MONGODB_URI)
        self.db = self.client.wolf_game_mongo_db
        self.game_states = self.db.game_states

    def create_game_state(self, session_id: str) -> Dict:
        """Create a new game state document"""
        game_state = {
            'session_id': str(session_id),
            'is_game_ready': False,
            'min_players': 12,
            'max_players': 12,
            'player_ready_status': [],
            'action_history': [],
            'current_round_states': {},
            'witch_powers_used': {'heal': False, 'poison': False},
            'hunter_shot_used': False,
            'vote_history': {},
            'role_history': {},
            'chat_history': [],
            'event_log': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = self.game_states.insert_one(game_state)
        return self.get_game_state(session_id)

    def get_game_state(self, session_id: str) -> Optional[Dict]:
        """Retrieve game state by session ID"""
        return self.game_states.find_one({'session_id': str(session_id)})

    def get_or_create_game_state(self, session_id: str) -> Dict:
        """Get existing game state or create new one"""
        game_state = self.get_game_state(session_id)
        if not game_state:
            game_state = self.create_game_state(session_id)
        return game_state

    def add_action(self, session_id: str, player_id: str, action_type: str,
                   target_id: str = None, round_number: int = None,
                   phase: str = None) -> bool:
        """Add a new action to the action history"""
        action = {
            'player_id': player_id,
            'action_type': action_type,
            'target_id': target_id,
            'round_number': round_number,
            'phase': phase,
            'timestamp': datetime.utcnow()
        }

        result = self.game_states.update_one(
            {'session_id': str(session_id)},
            {
                '$push': {'action_history': action},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    def update_player_ready(self, session_id: str, player_id: str,
                            is_ready: bool) -> bool:
        """Update player ready status"""
        # Remove existing status if present
        self.game_states.update_one(
            {'session_id': str(session_id)},
            {'$pull': {'player_ready_status': {'player_id': player_id}}}
        )

        # Add new status
        status = {
            'player_id': player_id,
            'is_ready': is_ready,
            'timestamp': datetime.utcnow()
        }

        result = self.game_states.update_one(
            {'session_id': str(session_id)},
            {
                '$push': {'player_ready_status': status},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )

        # Update game ready status
        if result.modified_count > 0:
            return self.check_game_ready(session_id)
        return False

    def add_chat_message(self, session_id: str, player_id: str,
                         message: str, is_public: bool = True) -> bool:
        """Add a chat message to history"""
        chat_message = {
            'player_id': player_id,
            'message': message,
            'is_public': is_public,
            'timestamp': datetime.utcnow()
        }

        result = self.game_states.update_one(
            {'session_id': str(session_id)},
            {
                '$push': {'chat_history': chat_message},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    def log_event(self, session_id: str, event_type: str,
                  event_data: Dict) -> bool:
        """Log a game event"""
        event = {
            'event_type': event_type,
            'event_data': event_data,
            'timestamp': datetime.utcnow()
        }

        result = self.game_states.update_one(
            {'session_id': str(session_id)},
            {
                '$push': {'event_log': event},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    def check_game_ready(self, session_id: str) -> bool:
        """Check if game is ready to start"""
        game_state = self.get_game_state(session_id)
        if not game_state:
            return False

        ready_count = sum(
            1 for status in game_state.get('player_ready_status', [])
            if status['is_ready']
        )

        is_ready = (
                ready_count >= game_state['min_players'] and
                ready_count <= game_state['max_players']
        )

        self.game_states.update_one(
            {'session_id': str(session_id)},
            {
                '$set': {
                    'is_game_ready': is_ready,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return is_ready

    def update_witch_powers(self, session_id: str, power_type: str,
                            used: bool) -> bool:
        """Update witch power usage status"""
        if power_type not in ['heal', 'poison']:
            return False

        result = self.game_states.update_one(
            {'session_id': str(session_id)},
            {
                '$set': {
                    f'witch_powers_used.{power_type}': used,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    def update_hunter_shot(self, session_id: str, used: bool) -> bool:
        """Update hunter shot usage status"""
        result = self.game_states.update_one(
            {'session_id': str(session_id)},
            {
                '$set': {
                    'hunter_shot_used': used,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    def get_action_history(self, session_id: str,
                           round_number: Optional[int] = None) -> List[Dict]:
        """Get action history, optionally filtered by round"""
        game_state = self.get_game_state(session_id)
        if not game_state:
            return []

        actions = game_state.get('action_history', [])
        if round_number is not None:
            actions = [
                action for action in actions
                if action['round_number'] == round_number
            ]
        return actions

    def get_chat_history(self, session_id: str,
                         is_public: Optional[bool] = None) -> List[Dict]:
        """Get chat history, optionally filtered by visibility"""
        game_state = self.get_game_state(session_id)
        if not game_state:
            return []

        messages = game_state.get('chat_history', [])
        if is_public is not None:
            messages = [
                msg for msg in messages
                if msg['is_public'] == is_public
            ]
        return messages

    def get_pending_actions_count(self, session_id: str, round_number: int, phase: str,
                                  alive_players_count: int) -> int:
        """Get count of players who haven't made actions in current round and phase"""
        try:
            game_state = self.game_states.find_one({'session_id': session_id})
            if not game_state:
                return alive_players_count  # If no game state found, all players are pending

            # Get actions for current round and phase
            actions = []
            if 'action_history' in game_state:
                actions = [
                    action for action in game_state['action_history']
                    if action.get('round_number') == round_number
                       and action.get('phase') == phase
                ]

            # Count unique players who have acted
            unique_actors = len(set(action['player_id'] for action in actions))
            return alive_players_count - unique_actors

        except Exception as e:
            logger.error(f"Error getting pending actions count: {e}")
            return 0