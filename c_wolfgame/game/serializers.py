from rest_framework import serializers
from .models import GameSession, GamePlayer


class GamePlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GamePlayer
        fields = ['player_id', 'name', 'role', 'status', 'is_policeman']


class GameSessionSerializer(serializers.ModelSerializer):
    players = GamePlayerSerializer(many=True, read_only=True)

    class Meta:
        model = GameSession
        fields = ['session_id', 'current_phase', 'round_count', 'players']