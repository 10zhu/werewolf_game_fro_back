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
    # @action(detail=False, methods=['POST'])
    # def create_game(self, request):
    #     session = GameSession.objects.create(
    #         session_id=request.data.get('session_id'),
    #         current_phase='SETUP'
    #     )
    #     return Response({
    #         'session_id': session.session_id,
    #         'status': 'created'
    #     })

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

    @action(detail=True, methods=['POST'])
    def start_game(self, request, pk=None):
        session = GameSession.objects.get(pk=pk)
        logger.info(f"session is {session}")
        # Update the game phase
        game = WerewolfGame()
        game.setup_game()

        session.current_phase = game._current_phase  # Example phase change
        session.save()

        # Notify clients via WebSocket
        channel_layer = get_channel_layer()
        logger.info(f"channel layer is {channel_layer}")
        #
        # async_to_sync(channel_layer.group_send)(
        #     f"game_{session.session_id}",
        #     {
        #         "type": "phase_update",
        #         "phase": session.current_phase,
        #     }
        # )
        return Response(
            StartGameResponseDto(type="phase_update", phase="Night").to_json()
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