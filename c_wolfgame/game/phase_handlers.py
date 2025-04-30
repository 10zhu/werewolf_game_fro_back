# phase_handlers.py
import logging
from channels.db import database_sync_to_async
from .models import GamePlayer
from .engine.types import GameAction


class NightPhaseHandler:
    def __init__(self, game_id, game_store):
        self.game_id = game_id
        self.game_store = game_store
        self.logger = logging.getLogger(__name__)

    @database_sync_to_async
    def process_actions(self, content, session):
        try:
            # Get all alive players
            alive_players = GamePlayer.objects.filter(
                game_session=session,
                status='ALIVE'
            )
            total_alive_players = alive_players.count()

            # Log the incoming content
            self.logger.info(f"Processing action content: {content}")

            # Extract information from the content
            player_id = content.get('player_id')
            action_type = content.get('action')
            target_id = content.get('target_id')

            # Add the current action to MongoDB
            self.game_store.add_action(
                session_id=str(session.session_id),
                player_id=player_id,
                action_type=action_type,
                target_id=target_id,
                round_number=session.round_count,
                phase=session.current_phase
            )

            # Retrieve all actions for the current round and phase
            actions = self.game_store.get_action_history(
                str(session.session_id),
                round_number=session.round_count
            )

            # Get unique actors from the actions
            unique_actors = set(action['player_id'] for action in actions)

            # Check if all players have acted
            all_players_acted = len(unique_actors) == total_alive_players

            self.logger.info(f"""
            Action Processing Analysis:
            - Current Phase: {session.current_phase}
            - Current Round: {session.round_count}
            - Total Alive Players: {total_alive_players}
            - Unique Actors: {len(unique_actors)}
            - Unique Actor IDs: {unique_actors}
            - All Players Acted: {all_players_acted}
            """)

            # Phase change logic
            if all_players_acted:
                self.logger.info(f"""
                Phase Change Decision Details:
                - All players acted: {all_players_acted}
                - Current Phase: {session.current_phase}
                - Round Count: {session.round_count}
                - Will phase change: {all_players_acted and session.current_phase == 'NIGHT'}
                """)

                if session.current_phase == 'NIGHT':
                    if session.round_count == 1:
                        # First round night ends, move to policeman selection
                        session.current_phase = 'POLICEMAN_SELECTION'
                        session.save()
                        self.logger.info("Phase changed from NIGHT to POLICEMAN_SELECTION (First Round)")
                        return True
                    else:
                        # Not first round, move to day
                        session.current_phase = 'DAY'
                        session.round_count += 1
                        session.save()
                        self.logger.info("Phase changed from NIGHT to DAY")
                        return True

                elif session.current_phase == 'POLICEMAN_SELECTION':
                    # Check if all players have voted for policeman
                    session.current_phase = 'DAY'
                    session.save()
                    self.logger.info("Phase changed from POLICEMAN_SELECTION to DAY")
                    return True

                elif session.current_phase == 'DAY':
                    # All players have spoken, move to night
                    session.current_phase = 'NIGHT'
                    session.round_count += 1
                    session.save()
                    self.logger.info("Phase changed from DAY to NIGHT")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error processing actions: {e}")
            return False

class PolicemanPhaseHandler:
    def __init__(self, game_id, controller):
        self.game_id = game_id
        self.controller = controller
        self.logger = logging.getLogger(__name__)

    # Sync versions of the methods for use within process_actions
    def handle_candidacy_sync(self, player_id, session):
        """Handle a player running for policeman (sync version)"""
        try:
            player = GamePlayer.objects.get(
                game_session=session,
                player_id=player_id
            )
            player.running_for_policeman = True
            player.save()
            self.logger.info(f"Player {player_id} is now running for policeman")
            return True
        except Exception as e:
            self.logger.error(f"Error handling candidacy: {e}")
            return False

    # Async versions of the methods for external calls
    @database_sync_to_async
    def handle_candidacy(self, player_id, session):
        """Handle a player running for policeman (async wrapper)"""
        return self.handle_candidacy_sync(player_id, session)
    # @database_sync_to_async
    # def handle_candidacy(self, player_id, session):
    #     """Handle a player running for policeman"""
    #     try:
    #         player = GamePlayer.objects.get(
    #             game_session=session,
    #             player_id=player_id
    #         )
    #         player.running_for_policeman = True
    #         player.save()
    #         self.logger.info(f"Player {player_id} is now running for policeman")
    #         return True
    #     except Exception as e:
    #         self.logger.error(f"Error handling candidacy: {e}")
    #         return False

    def process_vote_sync(self, voter_id, candidate_id, session):
        """Process a vote for policeman (sync version)"""
        try:
            voter = GamePlayer.objects.get(game_session=session, player_id=voter_id)
            candidate = GamePlayer.objects.get(game_session=session, player_id=candidate_id)

            if not candidate.running_for_policeman or voter.running_for_policeman:
                return False

            self.controller.policeman_votes[voter_id] = candidate_id
            self.logger.info(f"Vote recorded: {voter_id} voted for {candidate_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error processing vote: {e}")
            return False
    @database_sync_to_async
    def process_vote(self, voter_id, candidate_id, session):
        """Process a vote for policeman (async wrapper)"""
        return self.process_vote_sync(voter_id, candidate_id, session)
    # @database_sync_to_async
    # def process_vote(self, voter_id, candidate_id, session):
    #     """Process a vote for policeman"""
    #     try:
    #         voter = GamePlayer.objects.get(game_session=session, player_id=voter_id)
    #         candidate = GamePlayer.objects.get(game_session=session, player_id=candidate_id)
    #
    #         if not candidate.running_for_policeman or voter.running_for_policeman:
    #             return False
    #
    #         self.controller.policeman_votes[voter_id] = candidate_id
    #         self.logger.info(f"Vote recorded: {voter_id} voted for {candidate_id}")
    #
    #         # Check if voting is complete
    #         total_voters = GamePlayer.objects.filter(
    #             game_session=session,
    #             status='ALIVE',
    #             running_for_policeman=False
    #         ).count()
    #
    #         if len(self.controller.policeman_votes) >= total_voters:
    #             self._finalize_election(session)
    #             return True
    #         return False
    #
    #     except Exception as e:
    #         self.logger.error(f"Error processing vote: {e}")
    #         return False

    def _finalize_election(self, session):
        """Count votes and declare winner"""
        try:
            vote_counts = {}
            for candidate_id in self.controller.policeman_votes.values():
                vote_counts[candidate_id] = vote_counts.get(candidate_id, 0) + 1

            if vote_counts:
                winner_id = max(vote_counts.items(), key=lambda x: x[1])[0]
                # Reset all players
                GamePlayer.objects.filter(game_session=session).update(
                    is_policeman=False,
                    running_for_policeman=False
                )
                # Set winner
                winner = GamePlayer.objects.get(
                    game_session=session,
                    player_id=winner_id
                )
                winner.is_policeman = True
                winner.save()

                session.current_phase = 'DAY'
                session.save()
                self.logger.info(f"Election complete: {winner_id} is the new policeman")
        except Exception as e:
            self.logger.error(f"Error finalizing election: {e}")

    @database_sync_to_async
    def process_actions(self, content, session):
        """Process player actions during policeman selection phase"""
        try:
            # Extract information from the content
            player_id = content.get('player_id')
            action_type = content.get('action')
            target_id = content.get('target_id')

            self.logger.info(f"Processing policeman phase action: {player_id} performing {action_type}")

            # Handle different action types
            if action_type == 'run_for_policeman':
                success = self.handle_candidacy_sync(player_id, session)
                self.logger.info(f"Player {player_id} running for policeman: {'success' if success else 'failed'}")
                # Running for policeman doesn't complete the phase
                return False

            elif action_type == 'vote_policeman':
                # Process the vote
                success = self.process_vote_sync(player_id, target_id, session)

                # Check if all votes are in and the phase should change
                alive_players = GamePlayer.objects.filter(
                    game_session=session,
                    status='ALIVE',
                    running_for_policeman=False
                )

                total_votes = len(self.controller.policeman_votes)
                all_voted = total_votes >= alive_players.count()

                self.logger.info(f"Policeman vote processed: {player_id} voted for {target_id}. All voted: {all_voted}")

                if all_voted:
                    # Finalize the election and change phase
                    self._finalize_election(session)
                    return True  # Phase should change

            return False  # No phase change by default
        except Exception as e:
            self.logger.error(f"Error processing policeman phase action: {e}")
            return False