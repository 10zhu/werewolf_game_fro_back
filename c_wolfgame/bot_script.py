import logging
import json
import asyncio
import random
import os
import django

import websockets
import requests
import time
from typing import Dict, List
from enum import Enum

from game.mongodb_model import GameStateStore

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wolfgame.settings')
django.setup()


class Role(Enum):
    WEREWOLF = "WEREWOLF"
    VILLAGER = "VILLAGER"
    SEER = "SEER"
    WITCH = "WITCH"
    HUNTER = "HUNTER"
    IDIOT = "IDIOT"


class BotStrategy:
    def __init__(self, player_data: Dict):
        self.player_id = player_data['player_id']
        self.role = player_data['role']
        self.position = player_data['position']
        self.is_alive = player_data['status'] == 'ALIVE'
        self.logger = logging.getLogger(__name__)
        self.last_night_killed = None
        self.last_action_round = None

    async def decide_action(self, game_state: Dict, game_id: str) -> Dict:
        current_round = game_state.get('round', 1)
        current_phase = game_state.get('phase')
        # self.logger.info(f"""
        #     Bot {self.player_id} deciding action:
        #     Round: {current_round}
        #     Phase: {current_phase}
        #     Last action round: {self.last_action_round}
        #     Is alive: {self.is_alive}
        #     Role: {self.role}
        #     """)
        # Don't act if we've already acted this round
        if self.last_action_round == current_round:
            # self.logger.info(f"Bot {self.player_id} already acted in round {current_round}")
            return None
        """Decide action based on role and game state"""
        try:
            if not self.is_alive:
                # self.logger.info(f"Bot {self.player_id} is dead, no action needed")
                return None

            current_phase = game_state.get('phase')

            # Update last night's killed target and alive status
            killed_player = next((p['player_id'] for p in game_state['players'] if p['status'] == 'DEAD'), None)
            if killed_player:
                self.last_night_killed = killed_player

            # Update alive status
            self.is_alive = next(
                (p['status'] == 'ALIVE' for p in game_state['players']
                 if p['player_id'] == self.player_id), False)

            self.last_action_round = current_round

            if current_phase == 'NIGHT':
                if self.role == 'WEREWOLF':
                    # Werewolf decision logic
                    werewolves = [p for p in game_state['players'] if p['role'] == 'WEREWOLF']
                    if self.player_id == werewolves[0]['player_id']:
                        possible_targets = [p for p in game_state['players']
                                            if p['status'] == 'ALIVE']
                        if possible_targets:
                            # target = random.choice(possible_targets)
                            return {
                                'type': 'player_action',
                                'player_id': self.player_id,
                                'action': 'kill',
                                # 'target_id': target['player_id']
                                'target_id': 4
                            }
                    else:
                        # Other werewolves sleep
                        return {
                            'type': 'player_action',
                            'player_id': self.player_id,
                            'action': 'sleep',
                            'target_id': self.player_id
                        }

                elif self.role == 'WITCH':
                    # Get game state for witch powers usage
                    game_store = GameStateStore()
                    game_state = game_store.get_game_state(game_id)
                    witch_powers = game_state.get('witch_powers_used', {'heal': False, 'poison': False})
                    if self.last_night_killed and not witch_powers.get('heal'):
                        # Simple healing strategy: heal the killed player
                        game_store.update_witch_powers(game_id, 'heal', True)
                        self.logger.info(f"Witch {self.player_id} healing {self.last_night_killed}")
                        return {
                            'type': 'player_action',
                            'player_id': self.player_id,
                            'action': 'heal',
                            'target_id': self.last_night_killed
                        }

                    self.logger.info(f"Witch powers state: {witch_powers}")

                    # If no heal can be used, go to sleep
                    self.logger.info(f"Witch {self.player_id} going to sleep")
                    return {
                        'type': 'player_action',
                        'player_id': self.player_id,
                        'action': 'sleep',
                        'target_id': self.player_id
                    }

                elif self.role == 'SEER':
                    possible_targets = [p for p in game_state['players']
                                        if p['status'] == 'ALIVE']
                    if possible_targets:
                        target = random.choice(possible_targets)
                        action = {
                            'type': 'player_action',
                            'player_id': self.player_id,
                            'action': 'check',
                            'target_id': target['player_id']
                        }
                        self.logger.info(f"Seer {self.player_id} checking {target['player_id']}")
                        return action
                else:
                    action = {
                        'type': 'player_action',
                        'player_id': self.player_id,
                        'action': 'sleep',
                        'target_id': self.player_id
                    }
                    self.logger.info(f"Player {self.player_id} going to sleep")
                    return action

            elif current_phase == 'POLICEMAN_SELECTION':

                # Players p1 and p2 will run for policeman
                if self.player_id in ['p1', 'p2']:
                    return {
                        'type': 'player_action',
                        'player_id': self.player_id,
                        'action': 'run_for_policeman',
                        'target_id': self.player_id
                    }
                # Other players vote for either p1 or p2
                else:
                    target_id = random.choice(['p1', 'p2'])
                    return {
                        'type': 'player_action',
                        'player_id': self.player_id,
                        'action': 'vote_policeman',
                        'target_id': target_id
                    }

            return None

        except Exception as e:
            self.logger.error(f"Error in decide_action for {self.player_id}: {e}")
            return None


class TestBot:
    API_BASE = "http://localhost:8000/api/"
    WS_BASE = "ws://localhost:8000/ws/game/"

    def __init__(self):
        self.session = requests.session()
        self.bots: Dict[str, BotStrategy] = {}
        self.logger = logging.getLogger(__name__)

    def get_latest_game(self) -> str:
        """Get the most recently created game session"""
        try:
            # Use the list endpoint to get all games
            response = requests.get(f"{self.API_BASE}games/?recent=true")
            if response.ok:
                games = response.json()
                if games:
                    # First game should be the most recent
                    latest_game = games[-1]
                    game_id = latest_game['session_id']
                    self.logger.info(f"Found existing game: {game_id}")
                    return game_id
                else:
                    self.logger.error("No existing games found")
                    raise Exception("No games available")
        except Exception as e:
            self.logger.error(f"Error getting latest game: {e}")
            raise

    async def get_game_state(self, game_id: str) -> Dict:
        try:
            start_response = requests.post(
                f"{self.API_BASE}games/{game_id}/start_game/"
            )
            if start_response.ok:
                return start_response.json()
            else:
                self.logger.error(f"Failed to start game: {start_response.text}")
                raise Exception("Failed to start game")
        except Exception as e:
            self.logger.error(f"Error getting game state: {e}")
            raise

    async def run_bot(self, game_id: str, bot: BotStrategy):
        game_store = GameStateStore()
        while True:  # Keep trying to reconnect
            try:
                ws_url = f"{self.WS_BASE}{game_id}/"
                self.logger.info(f"Bot {bot.player_id} connecting to {ws_url}")

                async with websockets.connect(ws_url) as ws:
                    self.logger.info(f"Bot {bot.player_id} connected")
                    while True:
                        try:
                            message = await ws.recv()
                            self.logger.info(f"Bot {bot.player_id} received: {message}")
                            game_state = json.loads(message)
                            self.logger.info(f"Current bot:{bot.player_id}")
                            # TODO: new endpoint is_next_round_ready check whether all agents send the messages
                            action = await bot.decide_action(game_state, game_id)
                            self.logger.info(f"current action:{action}")
                            if action:
                                # Explicitly record the action in MongoDB
                                recorded = game_store.add_action(
                                    session_id=game_id,
                                    player_id=action['player_id'],
                                    action_type=action['action'],
                                    target_id=action.get('target_id'),
                                    round_number=game_state.get('round', 1),
                                    phase=game_state.get('phase')
                                )

                                # Log whether the action was successfully recorded
                                self.logger.info(f"Action recorded in MongoDB: {recorded}")
                                await ws.send(json.dumps(action))
                                self.logger.info(f"Bot {bot.player_id} sent action: {action}")
                                await asyncio.sleep(1)  # Add delay between actions

                        except websockets.ConnectionClosed:
                            self.logger.info(f"Bot {bot.player_id} connection closed, attempting reconnect...")
                            break

            except Exception as e:
                self.logger.error(f"Bot {bot.player_id} error: {e}")
            # TODO: 直接sleep
            await asyncio.sleep(5)  # Wait before reconnecting

    async def run_game(self, game_id: str, num_bots: int = 12):
        try:
            game_state = await self.get_game_state(game_id)
            self.logger.info(f"Initial game state: {game_state}")
            self.logger.info(f"game id: {game_id}")

            # Create tasks for all bots
            bots = []
            bot_tasks = []
            for player in game_state['players'][:num_bots]:
                bot = BotStrategy({
                    'player_id': player['player_id'],
                    'role': player['role'],
                    'position':  game_state['players'].index(player) + 1,  # Add the position if available
                    'status': player['status']  # Add the status if available
                })
                bots.append(bot)  # Store bot instance
                self.logger.info(f"Starting bot for player {player['player_id']} with role {player['role']}")
                task = asyncio.create_task(self.run_bot(game_id, bot))
                bot_tasks.append(task)

            while True:
                # Check MongoDB for current game state and pending actions
                game_store = GameStateStore()
                current_state = game_store.get_game_state(game_id)

                if not current_state:
                    self.logger.error("Could not get current game state")
                    break

                current_round = game_state.get('round', 1)
                current_phase = game_state.get('phase')
                self.logger.info(f"Current round: {current_round}, phase: {current_phase}")

                actions = current_state.get('action_history', [])
                current_actions = [
                    action for action in actions
                    if action.get('round_number') == current_round and
                       action.get('phase') == current_phase
                ]

                self.logger.info(f"Actions this round: {current_actions}")

                alive_players = [p for p in game_state['players'] if p['status'] == 'ALIVE']
                pending_actions = game_store.get_pending_actions_count(
                    game_id,
                    current_round,
                    current_phase,
                    len(alive_players)
                )

                if pending_actions == 0:
                    # All players have acted, make bot actions for next round
                    for bot in bots:
                        if bot.is_alive:
                            action = await bot.decide_action(game_state, game_id)
                            if action:
                                await self.send_action(game_id, action)
                                self.logger.info(f"Bot {bot.player_id} sent action: {action}")


                    # Wait for server to process actions
                    await asyncio.sleep(2)
                else:
                    # Still waiting for some players to act
                    self.logger.info(f"Waiting for {pending_actions} players to act...")
                    await asyncio.sleep(5)  # Wait longer before next check

                # Update game state
                game_state = await self.get_game_state(game_id)

                # Check if game is over
                if game_state.get('phase') == 'GAME_OVER':
                    self.logger.info("Game is over, stopping bots")
                    break

            # # Wait for all bot tasks to complete
            await asyncio.gather(*bot_tasks)
        except Exception as e:
            self.logger.error(f"Error running game: {e}")
            raise

    async def send_action(self, game_id: str, action: Dict):
        """Send a single action to the game server"""
        ws_url = f"{self.WS_BASE}{game_id}/"
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps(action))
            response = await ws.recv()
            return json.loads(response)
async def main():
    bot_manager = TestBot()
    game_id = bot_manager.get_latest_game()
    await bot_manager.run_game(game_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

# import logging
#
# import requests
# import time
# import websockets
#
# class TestBot:
#     API_BASE = "api/"
#     CREATE_GAME = "games/"
#     WEBSOCKET_BASE = "ws/game/"
#     def __init__(self, base_url: str):
#         self.session = requests.session()
#         self.ws_session = None
#         self.base_url = base_url
#         self.logger = logging.getLogger(__name__)
#
    # def create_game(self) -> str:
    #     resp = self.session.post(
    #         self.base_url + self.API_BASE + self.CREATE_GAME,
    #         {
    #             "session_id": time.time()
    #         }
    #     )
    #
    #     game_id = resp.json()["session_id"]
    #     self.logger.info(f"Created game {game_id}")
    #     return game_id
#
#     def connect_to_websocket(self, game_id) -> websockets.connect:
#         return websockets.connect(self.WEBSOCKET_BASE + f"{game_id}")
#
#     def join_game(self, game_id: str):
#         pass
#
#     def run_game(self, game_id):
#         with self.connect_to_websocket(game_id) as ws:
#             info = ws.recv()
#
#
# if __name__ == "__main__":
#     # # configure logger here
#     # LOGGING = {
#     #     'version': 1,
#     #     'disable_existing_loggers': False,
#     #     'handlers': {
#     #         'console': {
#     #             'class': 'logging.StreamHandler',
#     #             'level': 'INFO'
#     #         }
#     #     },
#     #     'root': {
#     #         'handlers': ['console'],
#     #         'level': 'INFO'
#     #     }
#     # }
#     # logging.basicConfig()
#     base_url = "localhost:8000"
#     bot = TestBot(base_url)
#     game_id = bot.create_game()
#     for _ in range(10):
#         bot = TestBot(base_url)
#         bot.join_game(game_id)