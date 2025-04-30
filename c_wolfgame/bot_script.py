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
        self.last_action_phase = None

    async def decide_action(self, game_state: Dict, game_id: str) -> Dict:
        current_round = game_state.get('round', 1)
        current_phase = game_state.get('phase')
        self.logger.info(f"""
            Bot {self.player_id} deciding action:
            Round: {current_round}
            Phase: {current_phase}
            Last action round: {self.last_action_round}
            Is alive: {self.is_alive}
            Role: {self.role}
            """)
        # Don't act if we've already acted this round
        if self.last_action_round == current_round and self.last_action_phase == current_phase:
            self.logger.info(f"Bot {self.player_id} already acted in round {current_round}, phase {current_phase}")
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
            self.last_action_phase = current_phase

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
                self.logger.info(f"Bot {self.player_id} is in POLICEMAN_SELECTION phase")

                # Reset the action tracking for this phase to ensure all bots act
                if self.last_action_round == current_round and self.last_action_phase == current_phase:
                    self.logger.info(f"Bot {self.player_id} already acted but will force a vote in POLICEMAN_SELECTION")
                    # Reset to allow voting again
                    self.last_action_phase = None

                # Players p1 and p2 will run for policeman
                if self.player_id in ['p1', 'p2']:
                    self.logger.info(f"Bot {self.player_id} is eligible to run for policeman and will do so")
                    return {
                        'type': 'player_action',
                        'player_id': self.player_id,
                        'action': 'run_for_policeman',
                        'target_id': self.player_id
                    }
                # Other players vote for either p1 or p2
                else:
                    self.logger.info(f"Bot {self.player_id} is not p1 or p2, will vote for policeman")
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
                    # First game should be the most recent
                    # This will work if session IDs are created with Date.now().toString()
                    # sorted_games = sorted(games, key=lambda x: int(x['session_id']), reverse=True)
                    latest_game = games[-1]  # Get the newest game
                    game_id = latest_game['session_id']
                    self.logger.info(f"Found existing game: {game_id}")
                    self.logger.info(f"Bot attempting to connect to session: {game_id}")
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

                            # Add this check for phase change to POLICEMAN_SELECTION
                            current_phase = game_state.get('phase')
                            if current_phase == 'POLICEMAN_SELECTION':
                                self.logger.info(f"Bot {bot.player_id} detected POLICEMAN_SELECTION phase")
                                # Force a reset of action state for this phase
                                bot.last_action_phase = None

                                # Immediately check pending actions for this phase
                                actions_history = game_store.get_action_history(game_id)
                                current_round = game_state.get('round', 1)
                                current_actions = [a for a in actions_history if
                                                   a.get('phase') == 'POLICEMAN_SELECTION' and
                                                   a.get('round_number') == current_round]
                                unique_actors = set(a.get('player_id') for a in current_actions)
                                alive_players = [p for p in game_state['players'] if p['status'] == 'ALIVE']

                                self.logger.info(
                                    f"POLICEMAN_SELECTION check: {len(unique_actors)} actors out of {len(alive_players)} alive")

                            self.logger.info(f"Current bot:{bot.player_id}    game_state: {game_state}")
                            # TODO: new endpoint is_next_round_ready check whether all agents send the messages
                            action = await bot.decide_action(game_state, game_id)
                            self.logger.info(f"Bot {bot.player_id} decided action: {action}")
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
            last_phase = None
            last_round = None

            while True:
                # Check MongoDB for current game state and pending actions
                game_store = GameStateStore()
                current_state = game_store.get_game_state(game_id)

                actions = game_store.get_action_history(game_id)
                self.logger.info(f"Current actions in MongoDB: {actions}")

                if not current_state:
                    self.logger.error("Could not get current game state")
                    break

                # Get the latest game state from the API
                game_state = await self.get_game_state(game_id)
                current_round = game_state.get('round', 1)
                current_phase = game_state.get('phase')

                # In run_game method, after getting the latest game state
                if last_phase != current_phase:
                    self.logger.info(f"Phase transition detected: {last_phase} -> {current_phase}")

                    # If transitioning to POLICEMAN_SELECTION, force a full check immediately
                    if current_phase == 'POLICEMAN_SELECTION':
                        self.logger.info("Transitioning to POLICEMAN_SELECTION phase, forcing immediate check")

                        # Reset action state for all bots
                        for bot in bots:
                            bot.last_action_phase = None
                            self.logger.info(f"Reset action state for bot {bot.player_id} for new phase")

                        # Force immediate actions for this phase
                        continue  # Skip to next loop iteration to immediately recheck conditions

                # Log phase transition
                if last_phase != current_phase or last_round != current_round:
                    self.logger.info(
                        f"Phase transition detected: {last_phase} -> {current_phase} (Round: {current_round})")
                    last_phase = current_phase
                    last_round = current_round

                    # When phase changes, reset the last_action_round for all bots
                    for bot in bots:
                        if bot.last_action_round == current_round and current_phase != game_state.get('phase'):
                            bot.last_action_round = None
                            self.logger.info(f"Reset action status for bot {bot.player_id} due to phase change")

                # Log current state
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

                self.logger.info(
                    f"PENDING ACTIONS CHECK: {pending_actions} pending out of {len(alive_players)} alive players")
                current_phase_actions = [a for a in actions if
                                         a.get('phase') == current_phase and a.get('round_number') == current_round]
                unique_actors = set(a.get('player_id') for a in current_phase_actions)
                self.logger.info(f"Unique actors this round/phase: {len(unique_actors)} out of {len(alive_players)}")
                self.logger.info(f"Players who have acted: {sorted(list(unique_actors))}")

                if pending_actions == 0 and current_phase == 'POLICEMAN_SELECTION':
                    self.logger.info(
                        "All players have voted in POLICEMAN_SELECTION phase. Attempting to force phase change.")

                    try:
                        # Try to use WebSocket to send a special command
                        async with websockets.connect(f"{self.WS_BASE}{game_id}/") as ws:
                            command = {
                                'type': 'admin_command',
                                'command': 'change_phase',
                                'current_phase': 'POLICEMAN_SELECTION',
                                'next_phase': 'DAY'
                            }
                            await ws.send(json.dumps(command))
                            response = await ws.recv()
                            self.logger.info(f"Phase change command response: {response}")
                    except Exception as e:
                        self.logger.error(f"Error sending phase change command: {e}")

                elif pending_actions == 0 and current_phase != 'POLICEMAN_SELECTION':
                    # All players have acted, make bot actions for next round
                    self.logger.info(f"All players have acted in {current_phase}. Waiting for phase change...")
                    # Wait for the server to process actions and update the phase

                    # Send a special message to trigger phase completion check
                    try:
                        check_message = {
                            'type': 'check_phase_completion',
                            'round': current_round,
                            'phase': current_phase
                        }

                        # Send this via WebSocket
                        async with websockets.connect(f"{self.WS_BASE}{game_id}/") as ws:
                            await ws.send(json.dumps(check_message))
                            response = await ws.recv()
                            self.logger.info(f"Phase completion check response: {response}")
                    except Exception as e:
                        self.logger.error(f"Error sending phase completion check: {e}")

                    # Then wait and check
                    await asyncio.sleep(5)

                    # Get the updated game state after waiting
                    updated_game_state = await self.get_game_state(game_id)
                    new_phase = updated_game_state.get('phase')
                    self.logger.info(f"After waiting: current_phase={current_phase}, new_phase={new_phase}")

                    # If phase has changed, have bots act according to the new phase
                    if new_phase != current_phase:
                        self.logger.info(
                            f"Phase has changed from {current_phase} to {new_phase}. Bots will act for new phase.")

                        # Let each bot act according to the new phase
                        for bot in bots:
                            if bot.is_alive:
                                self.logger.info(f"Bot {bot.player_id} is alive and will decide action for {new_phase}")
                                action = await bot.decide_action(updated_game_state, game_id)
                                self.logger.info(f"Bot {bot.player_id} decided action: {action}")
                                if action:
                                    await self.send_action(game_id, action)
                                    self.logger.info(
                                        f"Bot {bot.player_id} sent action for new phase {new_phase}: {action}")
                                else:
                                    self.logger.info(f"Bot {bot.player_id} decided not to act for {new_phase}")
                        # Short delay between bot actions
                        await asyncio.sleep(1)
                    else:
                        self.logger.info(f"No phase change detected after waiting. Still in {current_phase}")
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
        try:
            ws_url = f"{self.WS_BASE}{game_id}/"
            self.logger.info(f"Opening new WebSocket connection to {ws_url} to send action")
            async with websockets.connect(ws_url) as ws:
                self.logger.info(f"Connected, sending action: {action}")
                await ws.send(json.dumps(action))
                self.logger.info(f"Action sent, waiting for response")
                response = await ws.recv()
                response_data = json.loads(response)
                self.logger.info(f"Received response: {response_data}")
                return response_data
        except Exception as e:
            self.logger.error(f"Error in send_action: {e}")
            return None
async def main():
    bot_manager = TestBot()
    # game_id = bot_manager.get_latest_game()
    game_id = "aa6b440f-a8d8-4e19-a521-0f76be250574"
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