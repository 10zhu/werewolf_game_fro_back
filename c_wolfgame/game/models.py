import uuid

from django.db import models

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