import uuid

from django.db import models
from django.contrib.postgres.fields import JSONField
from typing import List, Dict

class GameSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_phase = models.CharField(max_length=20)
    round_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class GamePlayer(models.Model):
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE)
    player_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    is_policeman = models.BooleanField(default=False)
    running_for_policeman = models.BooleanField(default=False)

    # TODO: mongodb store game states [eg. players' history action, game_ready,
# class PlayerAction(models.Model):
#     player_id = models.CharField(max_length=50)
#     action_type = models.CharField(max_length=50)  # e.g., 'kill', 'heal', 'vote', etc.
#     target_id = models.CharField(max_length=50, null=True)
#     round_number = models.IntegerField()
#     phase = models.CharField(max_length=20)  # e.g., 'NIGHT', 'DAY', etc.
#     timestamp = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         abstract = True
#
# class PlayerReadyStatus(models.Model):
#     player_id = models.CharField(max_length=50)
#     is_ready = models.BooleanField(default=False)
#     timestamp = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         abstract = True
#
# class GameState(models.Model):
#     # Link to the main game session
#     game_session = models.ForeignKey('GameSession', on_delete=models.CASCADE)
#
#     # Game status
#     is_game_ready = models.BooleanField(default=False)
#     min_players = models.IntegerField(default=12)
#     max_players = models.IntegerField(default=12)
#
#     # Player readiness tracking
#     player_ready_status = models.ArrayField(
#         model_container=PlayerReadyStatus,
#         default=list
#     )
#
#     # Action history
#     action_history = models.ArrayField(
#         model_container=PlayerAction,
#         default=list
#     )
#
#     # Round-specific states
#     current_round_states = models.JSONField(default=dict)  # Stores current round's temporary states
#
#     # Special power usage tracking
#     witch_powers_used = models.JSONField(default=dict)  # e.g., {'heal': False, 'poison': False}
#     hunter_shot_used = models.BooleanField(default=False)
#
#     # Voting history
#     vote_history = models.JSONField(default=dict)  # Stores voting results for each round
#
#     # Player role history (in case of role swaps or special events)
#     role_history = models.JSONField(default=dict)
#
#     # Chat/communication history
#     chat_history = models.ArrayField(
#         models.JSONField(),
#         default=list
#     )
#
#     # Game events log
#     event_log = models.ArrayField(
#         models.JSONField(),
#         default=list
#     )
#
#     # Timestamp fields
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         db_table = 'game_states'
#
#     def add_action(self, player_id: str, action_type: str, target_id: str = None):
#         """Add a new action to the action history"""
#         new_action = PlayerAction(
#             player_id=player_id,
#             action_type=action_type,
#             target_id=target_id,
#             round_number=self.game_session.round_count,
#             phase=self.game_session.current_phase
#         )
#         self.action_history.append(new_action)
#         self.save()
#
#     def update_player_ready(self, player_id: str, is_ready: bool):
#         """Update player ready status"""
#         for status in self.player_ready_status:
#             if status.player_id == player_id:
#                 status.is_ready = is_ready
#                 status.save()
#                 break
#         else:
#             new_status = PlayerReadyStatus(
#                 player_id=player_id,
#                 is_ready=is_ready
#             )
#             self.player_ready_status.append(new_status)
#         self.save()
#
#     def add_chat_message(self, player_id: str, message: str, is_public: bool = True):
#         """Add a chat message to history"""
#         self.chat_history.append({
#             'player_id': player_id,
#             'message': message,
#             'is_public': is_public,
#             'timestamp': models.DateTimeField.auto_now_add
#         })
#         self.save()
#
#     def log_event(self, event_type: str, event_data: Dict):
#         """Log a game event"""
#         self.event_log.append({
#             'event_type': event_type,
#             'event_data': event_data,
#             'timestamp': models.DateTimeField.auto_now_add
#         })
#         self.save()
#
#     def check_game_ready(self) -> bool:
#         """Check if game is ready to start"""
#         ready_count = sum(1 for status in self.player_ready_status if status.is_ready)
#         is_ready = (
#                 ready_count >= self.min_players and
#                 ready_count <= self.max_players
#         )
#         self.is_game_ready = is_ready
#         self.save()
#         return is_ready