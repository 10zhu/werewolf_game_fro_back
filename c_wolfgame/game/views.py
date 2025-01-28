import logging
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .engine.game import WerewolfGame
from .models import GameSession, GamePlayer
from .serializers import GameSessionSerializer
from .start_game_dto_response import StartGameResponseDto

logger = logging.getLogger(__name__)

class GameViewSet(viewsets.ViewSet):
    def create(self, request):  # Add this method to handle POST
        print("Incoming data:", request.data)
        session_id = request.data.get('session_id')
        try:
            session_id = uuid.UUID(session_id)
        except (ValueError, TypeError):
            # raise ValidationError({'session_id': 'Invalid UUID format.'})
            session_id = uuid.uuid4()
        session = GameSession.objects.create(
            session_id = session_id,
            current_phase = 'SETUP'
        )
        serializer = GameSessionSerializer(session)
        return Response(
            {
                'session_id': str(session.session_id),
                'status': 'created'
            },
            status=status.HTTP_201_CREATED
        )
    # TODO: fetch all available rooms, 
    @action(detail=True, methods=['POST'])
    def start_game(self, request, pk=None):
        session = GameSession.objects.get(pk=pk)
        logger.info(f"session is {session}")

        # Create test players if none exist (for testing purposes)
        if not GamePlayer.objects.filter(game_session=session).exists():
            # Create 12 players as defined in your WerewolfGame class
            for i in range(12):
                GamePlayer.objects.create(
                    game_session=session,
                    player_id=f"p{i}",  # Match the IDs from your game engine
                    name=f"Player {i}",
                    status='ALIVE',
                )

        # Update the game phase
        game = WerewolfGame()
        game.setup_game()

        # Update the database with the roles assigned by the game engine
        players_data = []
        for player_id, game_player in game._players.items():
            db_player = GamePlayer.objects.get(
                game_session = session,
                player_id = player_id
            )
            db_player.role = game_player.get_role().value  # Get the role value from enum
            db_player.status = 'ALIVE'
            db_player.save()
            players_data.append({
                'player_id': db_player.player_id,
                'name': db_player.name,
                'role': db_player.role,
                'status': db_player.status
            })
        session.current_phase = game._current_phase.name  # Example phase change
        session.save()

        # Create and return response using StartGameResponseDto
        response = StartGameResponseDto(
            type="game_state",
            phase=session.current_phase,
            players=players_data
        )

        # Notify clients via WebSocket
        channel_layer = get_channel_layer()
        logger.info(f"channel layer is {channel_layer}")

        return Response(
            response.to_json()
        )

    @action(detail=True, methods=['POST'])
    def submit_action(self, request, pk=None):
        session = GameSession.objects.get(pk=pk)
        success, msg = True, "Action submitted"  # Replace with actual game logic
        return Response({
            'success': success,
            'message': msg
        })

    def list(self, request):
        sessions = GameSession.objects.all()
        serializer = GameSessionSerializer(sessions, many=True)
        return Response(serializer.data)