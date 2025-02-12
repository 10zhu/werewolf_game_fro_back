# game/consumer.py

import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from .engine.controller import GameController
from .engine.types import GameAction
from .models import GameSession, GamePlayer
from .engine.game import WerewolfGame
from .mongodb_model import GameStateStore

logger = logging.getLogger(__name__)


class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        logger.info(f"websocket connect : {self.scope}")
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'game_{self.game_id}'
        self.game = None
        self.controller = None
        self.game_store = GameStateStore()
        game_state = self.game_store.get_or_create_game_state(self.game_id)
        logger.info(f"Connecting to game {self.game_id}, room group {self.room_group_name}")

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        logger.info("Added to channel group")
        await self.accept()
        logger.info("Connection accepted")

        # Initialize game and controller
        await self.initialize_game()
        logger.info("Game initialized")
        game_state = await self.get_game_state()
        logger.info(f"Initial game state retrieved: {game_state}")
        await self.send_json(game_state)
        logger.info("Initial state sent")
    @database_sync_to_async
    def initialize_game(self):
        # Initialize game engine and controller
        self.game = WerewolfGame()
        self.controller = GameController(self.game)


    async def receive_json(self, content):
            logger.info(f"websocket receiving json content {content}")
            message_type = content.get('type')
            try:
                # Get the PostgreSQL session
                session = await database_sync_to_async(GameSession.objects.get)(session_id=self.game_id)

                # Example of logging an action
                await database_sync_to_async(self.game_store.add_action)(
                    session_id=self.game_id,
                    player_id=content.get('player_id'),
                    action_type=content.get('action'),
                    target_id=content.get('target_id'),
                    round_number=session.round_count,  # From PostgreSQL GameSession
                    phase=session.current_phase  # From PostgreSQL GameSession
                )
            except GameSession.DoesNotExist:
                # Handle error...
                pass


            if message_type == 'player_action':
                # Handle player actions and update game state
                updated_state = await self.handle_player_action(content)
                # Broadcast updated state to all players
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_message',
                        'message': updated_state
                    }
                )
            elif message_type == 'start_game':
                # Handle game start
                game_state = await self.handle_start_game()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_message',
                        'message': game_state
                    }
                )

    @database_sync_to_async
    def handle_start_game(self):
        try:
            session = GameSession.objects.get(session_id=self.game_id)
            game = WerewolfGame()
            game.setup_game()

            # Update players with roles
            players_data = []
            for player_id, game_player in game._players.items():
                db_player = GamePlayer.objects.get(
                    game_session=session,
                    player_id=player_id
                )
                db_player.role = game_player.get_role().value
                db_player.status = 'ALIVE'
                db_player.save()

                players_data.append({
                    'player_id': db_player.player_id,
                    'name': db_player.name,
                    'role': db_player.role,
                    'status': db_player.status,
                    'is_policeman': db_player.is_policeman
                })

            session.current_phase = game._current_phase.name
            session.save()

            return {
                'type': 'game_state',
                'phase': session.current_phase,
                'players': players_data
            }
        except GameSession.DoesNotExist:
            return {
                'type': 'error',
                'message': 'Game session not found'
            }

    @database_sync_to_async
    def handle_player_action(self, content):
        try:
            player_id = content.get('player_id')
            action_type = content.get('action')
            target_id = content.get('target_id')

            logger.info(f"Handling action: Player {player_id} performing {action_type} on {target_id}")
            # First, login the player through controller
            success, message = self.controller.login_player(player_id)
            if not success:
                return {
                    'type': 'error',
                    'message': message
                }

            # Submit the action through controller
            success, message = self.controller.submit_action(action_type, target_id)
            if not success:
                return {
                    'type': 'error',
                    'message': message
                }
            logger.info(f"Action queue before processing: {self.controller.action_queue}")
            # Process the action queue
            phase_changed = self.process_action_queue()
            logger.info(f"Phase changed: {phase_changed}")
            # Get current game state directly (not using await)
            game_session = GameSession.objects.get(session_id=self.game_id)

            # If phase changed, we might want to update round count or do other phase-specific logic
            if phase_changed:
                if game_session.current_phase == 'DAY':
                    game_session.round_count += 1
                game_session.save()
                logger.info(f"Phase changed to: {game_session.current_phase}, Round: {game_session.round_count}")

            session = GameSession.objects.get(session_id=self.game_id)
            players = GamePlayer.objects.filter(game_session=game_session)
            logger.info(f"Current game state - Phase: {session.current_phase}")

            for player in players:
                logger.info(f"Player {player.player_id}: Role={player.role}, Status={player.status}")

            return {
                'type': 'game_state',
                'phase': game_session.current_phase,
                'players': [
                    {
                        'player_id': player.player_id,
                        'name': f"Player {int(player.player_id.replace('p', '')) + 1}",
                        'role': player.role,
                        'status': player.status,
                        'is_policeman': player.is_policeman,
                        'position': int(player.player_id.replace('p', '')) + 1
                    } for player in players
                ],
                'round': game_session.round_count
            }

        except Exception as e:
            logger.error(f"Error handling player action: {e}")
            return {
                'type': 'error',
                'message': str(e)
            }
    async def game_message(self, event):
        logger.info(f"websocket sending game message {event}")
        await self.send_json(event['message'])

    # TODO:

    async def process_action_queue(self):
        """Process all actions in the controller's queue"""


        try:
            session = GameSession.objects.get(session_id=self.game_id)
            current_phase = session.current_phase
            night_actions = []
            phase_changed = False
            # while self.controller.action_queue:
            #     action = self.controller.action_queue.pop(0)
            #
            #     # Handle night phase actions
            #     if current_phase == 'NIGHT':
            #         if action.action_type in ['kill', 'heal', 'check', 'poison', 'sleep']:
            #             night_actions.append(action)
            #             if self.all_night_actions_received(night_actions):
            #                 self.process_night_actions(night_actions)
            #                 session.current_phase = 'POLICEMAN_SELECTION' if session.round_count == 1 else 'DAY'
            #                 session.save()
            #                 phase_changed = True

            # Process each action in the queue
            while self.controller.action_queue:
                action = self.controller.action_queue.pop(0)
                logger.info(f"Processing action: {action.action_type} from player {action.player_id}")

                # Handle NIGHT phase
                if current_phase == 'NIGHT':
                    if action.action_type in ['kill', 'heal', 'check', 'poison', 'sleep']:
                        night_actions.append(action)
                        logger.info(f"Added night action from {action.player_id}. Total actions: {len(night_actions)}")
                        logger.info(f"Current night actions: {[a.action_type for a in night_actions]}")
                        # Check if we have a kill action
                        # werewolf_actions = [a for a in night_actions if a.action_type == 'kill']
                        # if werewolf_actions:
                        logger.info("Kill action received, processing night actions...")
                        self.process_night_actions(night_actions)
                        session.current_phase = 'POLICEMAN_SELECTION' if session.round_count == 1 else 'DAY'
                        session.save()
                        phase_changed = True
                        logger.info(f"Phase changed to {session.current_phase}")


                # Handle policeman selection phase
                elif current_phase == 'POLICEMAN_SELECTION':
                    if action.action_type == 'run_for_policeman':
                        logger.info(f"Player {action.player_id} running for policeman")
                        await self.handle_policeman_candidacy(action.player_id)
                        players = GamePlayer.objects.filter(game_session=self.game_id)
                        logger.info(f"Current candidates: {[p.player_id for p in players if p.running_for_policeman]}")
                    elif action.action_type == 'vote_policeman':
                        self.handle_policeman_vote(action.player_id, action.target_id)
                        # Check if all votes are in
                        if self.all_eligible_voters_voted():
                            self.finalize_policeman_election()
                            session.current_phase = 'DAY'
                            session.save()
                            phase_changed = True

                # Handle day phase actions
                elif current_phase == 'DAY':
                    if action.action_type == 'vote':
                        self.handle_vote(action)
                        if self.check_all_day_votes_cast():
                            self.process_day_votes()
                            session.current_phase = 'NIGHT'
                            session.round_count += 1
                            session.save()
                            phase_changed = True

            return phase_changed

        except Exception as e:
            logger.error(f"Error in process_action_queue: {e}")
            return False

    def all_eligible_voters_voted(self):
        """Check if all eligible players have voted for policeman"""
        try:
            session = GameSession.objects.get(session_id = self.game_id)
            total_alive = GamePlayer.objects.filter(
                game_session=session,
                status='ALIVE',
                running_for_policeman=False
            ).count()
            total_votes = len(self.controller.policeman_votes)
            return total_votes >= total_alive
        except Exception as e:
            logger.error(f"Error checking eligible voters: {e}")
            return False

    async def handle_policeman_candidacy(self, player_id):
        """Handle a player deciding to run for policeman"""
        try:
            session = GameSession.objects.get(session_id=self.game_id)
            player = GamePlayer.objects.get(
                game_session=session,
                player_id=player_id
            )
            player.running_for_policeman = True
            player.save()

            # Broadcast updated game state to all clients
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_message',
                    'message': await self.get_game_state()
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error handling policeman candidacy: {e}")
            return False
    def handle_policeman_vote(self, voter_id, candidate_id):
        """Handle a vote for policeman"""
        try:
            session = GameSession.objects.get(session_id=self.game_id)
            voter = GamePlayer.objects.get(game_session=session, player_id=voter_id)
            candidate = GamePlayer.objects.get(game_session=session, player_id=candidate_id)

            if not candidate.running_for_policeman:
                return False

            if voter.running_for_policeman:
                return False  # Candidates can't vote

            self.controller.policeman_votes[voter_id] = candidate_id
            return True
        except Exception as e:
            logger.error(f"Error handling policeman vote: {e}")
            return False

    def finalize_policeman_election(self):
        """Count votes and assign policeman role"""
        try:
            vote_counts = {}
            for candidate_id in self.controller.policeman_votes.values():
                vote_counts[candidate_id] = vote_counts.get(candidate_id, 0) + 1

            if vote_counts:
                winner_id = max(vote_counts.items(), key=lambda x: x[1])[0]
                session = GameSession.objects.get(session_id=self.game_id)

                # Reset all players
                GamePlayer.objects.filter(game_session=session).update(
                    is_policeman=False,
                    running_for_policeman=False
                )

                # Set winner as policeman
                winner = GamePlayer.objects.get(
                    game_session=session,
                    player_id=winner_id
                )
                winner.is_policeman = True
                winner.save()

                # Move to next phase
                session.current_phase = 'DAY'
                session.save()

        except Exception as e:
            logger.error(f"Error finalizing policeman election: {e}")

    def handle_policeman_transfer(self, policeman_id, target_id):
        """Handle policeman transferring their role before death"""
        try:
            session = GameSession.objects.get(session_id=self.game_id)
            current_policeman = GamePlayer.objects.get(
                game_session=session,
                player_id=policeman_id,
                is_policeman=True
            )

            if target_id:  # Transfer to new policeman
                new_policeman = GamePlayer.objects.get(
                    game_session=session,
                    player_id=target_id
                )
                current_policeman.is_policeman = False
                new_policeman.is_policeman = True
                current_policeman.save()
                new_policeman.save()
            else:  # No transfer, role is eliminated
                current_policeman.is_policeman = False
                current_policeman.save()

        except Exception as e:
            logger.error(f"Error handling policeman transfer: {e}")
    def all_night_actions_received(self, night_actions):
        """Check if we have received all expected night actions"""
        werewolf_actions = sum(1 for action in night_actions if action.action_type == 'kill')
        seer_actions = sum(1 for action in night_actions if action.action_type == 'check')
        witch_actions = sum(1 for action in night_actions if action.action_type in ['heal', 'poison'])

        # Check living players with each role in the game engine
        werewolves_alive = any(
            player.get_role() and
            player.get_role().value == 'WEREWOLF' and
            player.is_alive()
            for player in self.game._players.values()
        )

        seer_alive = any(
            player.get_role() and
            player.get_role().value == 'SEER' and
            player.is_alive()
            for player in self.game._players.values()
        )

        witch_alive = any(
            player.get_role() and
            player.get_role().value == 'WITCH' and
            player.is_alive()
            for player in self.game._players.values()
        )
        # For villagers/other roles, their 'sleep' action doesn't affect night completion
        villager_sleep_actions = sum(1 for action in night_actions if action.action_type == 'sleep')

        # Expected actions based on living players
        expected_werewolf_actions = 1 if werewolves_alive else 0
        expected_seer_actions = 1 if seer_alive else 0
        expected_witch_actions = 1 if witch_alive else 0
        logger.info(f"Night actions received - Werewolf: {werewolf_actions}/{expected_werewolf_actions}, "
                    f"Seer: {seer_actions}/{expected_seer_actions}, "
                    f"Witch: {witch_actions}/{expected_witch_actions}, "
                    f"Villager sleep: {villager_sleep_actions}")
        return (werewolf_actions >= expected_werewolf_actions and
                seer_actions >= expected_seer_actions and
                witch_actions >= expected_witch_actions)

    def process_night_actions(self, night_actions):
        """Process all night actions in the correct order"""
        try:
            session = GameSession.objects.get(session_id=self.game_id)
            logger.info(f"Processing night actions: {night_actions}")
            # Track all night outcomes
            killed_player_id = None
            healed_player_id = None
            poisoned_player_id = None

            # 1. Process werewolf kill
            kill_actions = [a for a in night_actions if a.action_type == 'kill']
            if kill_actions:
                killed_player_id = kill_actions[0].target_id
                # Don't mark as dead yet - wait for witch's action
                logger.info(f"Werewolf chose to kill player {killed_player_id}")

            # 2. Process witch actions (heal/poison)
            heal_actions = [a for a in night_actions if a.action_type == 'heal']
            if heal_actions:
                healed_player_id = heal_actions[0].target_id
                logger.info(f"Witch chose to heal player {healed_player_id}")
            poison_actions = [a for a in night_actions if a.action_type == 'poison']
            if poison_actions:
                poisoned_player_id = poison_actions[0].target_id
                logger.info(f"Witch chose to poison player {poisoned_player_id}")

            # Final death processing
            if killed_player_id and killed_player_id != healed_player_id:
                # Mark werewolf's target as dead if not healed
                self.update_player_status(killed_player_id, 'DEAD')

            if poisoned_player_id:
                # Mark witch's poison target as dead
                self.update_player_status(poisoned_player_id, 'DEAD')

            # Update game phase after processing all actions
            session.current_phase = 'POLICEMAN_SELECTION' if session.round_count == 1 else 'DAY'
            session.save()
            logger.info(f"Changed phase to: {session.current_phase}, round: {session.round_count}")
            return True

        except Exception as e:
            logger.error(f"Error processing night actions: {e}")
            return False

    @database_sync_to_async
    def update_player_status(self, player_id, status):
        """Update player's status in database"""
        try:
            session = GameSession.objects.get(session_id=self.game_id)
            player = GamePlayer.objects.get(
                game_session=session,
                player_id=player_id
            )
            player.status = status
            player.save()
        except Exception as e:
            logger.error(f"Error updating player status: {e}")

    def all_night_actions_received(self, night_actions):
        """Check if we have received all expected night actions"""
        try:
            # Get current session and players
            session = GameSession.objects.get(session_id=self.game_id)
            players = GamePlayer.objects.filter(game_session=session)

            # Count roles that need to act
            werewolves_alive = any(p.role == 'WEREWOLF' and p.status == 'ALIVE' for p in players)
            witch_alive = any(p.role == 'WITCH' and p.status == 'ALIVE' for p in players)
            seer_alive = any(p.role == 'SEER' and p.status == 'ALIVE' for p in players)

            # Count submitted actions
            werewolf_actions = sum(1 for action in night_actions if action.action_type == 'kill')
            seer_actions = sum(1 for action in night_actions if action.action_type == 'check')
            witch_actions = sum(1 for action in night_actions if action.action_type in ['heal', 'poison'])

            # For testing with one player, temporarily set expectations to match what we have
            if len(players) < 12:  # If we're testing with fewer players
                logger.info("Testing mode: Adjusting expected actions")
                return True  # Allow phase to progress with fewer actions

            # Normal game mode
            return (
                    (not werewolves_alive or werewolf_actions > 0) and
                    (not seer_alive or seer_actions > 0) and
                    (not witch_alive or witch_actions > 0)
            )

        except Exception as e:
            logger.error(f"Error checking night actions: {e}")
            return False

    @database_sync_to_async
    def get_game_state(self):
        try:
            game_session = GameSession.objects.get(session_id=self.game_id)
            players = GamePlayer.objects.filter(game_session=game_session)

            if not players.exists():
                # Create 12 initial players
                for i in range(12):
                    GamePlayer.objects.create(
                        game_session=game_session,
                        player_id=f"p{i}", # Keep internal ID as 0-based
                        name=f"Player {i + 1}", # Display name as 1-based
                        status='ALIVE',
                        role='UNASSIGNED'  # Initial role before game starts
                    )
                # Refresh players queryset
                players = GamePlayer.objects.filter(game_session=game_session)
                logger.info(
                    f"Players running for policeman: {[p.player_id for p in players if p.running_for_policeman]}")

            return {
                'type': 'game_state',
                'phase': game_session.current_phase,
                'players': [
                    {
                        'player_id': player.player_id,
                        'name': f"Player {int(player.player_id.replace('p', '')) + 1}",  # Convert to 1-based
                        'role': player.role,
                        'status': player.status,
                        'is_policeman': player.is_policeman,
                        'running_for_policeman': player.running_for_policeman,  # Add this field
                        'position': int(player.player_id.replace('p', '')) + 1  # Add position number
                    } for player in players
                ]
            }
        except GameSession.DoesNotExist:
            return {
                'type': 'error',
                'message': 'Game session not found'
            }

