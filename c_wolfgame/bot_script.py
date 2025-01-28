import logging
import json
import asyncio
import random

import websockets
import requests
import time
from typing import Dict, List
from enum import Enum


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

    async def decide_action(self, game_state: Dict) -> Dict:
        """Decide action based on role and game state"""
        try:
            if not self.is_alive:
                return None

            current_phase = game_state.get('phase')

            # Update last night's killed target and alive status
            killed_player = next((p['player_id'] for p in game_state['players'] if p['status'] == 'DEAD'), None)
            if killed_player:
                self.last_night_killed = killed_player

            self.is_alive = next(
                p['status'] for p in game_state['players'] if p['player_id'] == self.player_id) == 'ALIVE'

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
                    if self.last_night_killed:
                        # Simple healing strategy: heal the killed player
                        return {
                            'type': 'player_action',
                            'player_id': self.player_id,
                            'action': 'heal',
                            'target_id': self.last_night_killed
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
            response = requests.get(f"{self.API_BASE}games/")
            if response.ok:
                games = response.json()
                if games:
                    # Get the latest game (assuming games are ordered by creation time)
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
                            # TODO: new endpoint is_next_round_ready check whether all agents send the messages
                            action = await bot.decide_action(game_state)
                            if action:
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

    async def run_game(self, game_id: str, num_bots: int = 11):
        try:
            game_state = await self.get_game_state(game_id)
            self.logger.info(f"Initial game state: {game_state}")

            # Create tasks for all bots
            bot_tasks = []
            for player in game_state['players'][:num_bots]:
                bot = BotStrategy({
                    'player_id': player['player_id'],
                    'role': player['role'],
                    'position':  game_state['players'].index(player) + 1,  # Add the position if available
                    'status': player['status']  # Add the status if available
                })
                self.logger.info(f"Starting bot for player {player['player_id']} with role {player['role']}")
                task = asyncio.create_task(self.run_bot(game_id, bot))
                bot_tasks.append(task)

            # Wait for all bot tasks to complete
            await asyncio.gather(*bot_tasks)
        except Exception as e:
            self.logger.error(f"Error running game: {e}")
            raise

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