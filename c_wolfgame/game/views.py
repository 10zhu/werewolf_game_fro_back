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
from .mongodb_model import GameStateStore
from .serializers import GameSessionSerializer
from .start_game_dto_response import StartGameResponseDto

logger = logging.getLogger(__name__)

class GameViewSet(viewsets.ViewSet):
    def get(self, request):
        # Order games by creation time in descending order
        games = GameSession.objects.order_by('-created_at')
        serializer = GameSessionSerializer(games, many=True)
        return Response(serializer.data)

    def create(self, request):  # Add this method to handle POST
        print("Incoming data:", request.data)
        session_id = request.data.get('session_id')
        try:
            session_id = uuid.UUID(session_id)
        except (ValueError, TypeError):
            session_id = uuid.uuid4()

        try:
            # Create PostgreSQL session
            session = GameSession.objects.create(
                session_id=session_id,
                current_phase='SETUP'
            )

            # Initialize MongoDB game state
            game_store = GameStateStore()
            game_state = game_store.get_or_create_game_state(str(session.session_id))
            logger.info(f"MongoDB game state initialized: {game_state}")

            serializer = GameSessionSerializer(session)
            return Response(
                {
                    'session_id': str(session.session_id),
                    'status': 'created'
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error creating game: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=True, methods=['POST'])
    def start_game(self, request, pk=None):
        try:
            session = GameSession.objects.get(pk=pk)
            logger.info(f"session is {session}")

            # Initialize MongoDB game state
            game_store = GameStateStore()
            game_state = game_store.get_or_create_game_state(str(session.session_id))
            logger.info(f"MongoDB game state initialized: {game_state}")

            # Create test players if none exist
            if not GamePlayer.objects.filter(game_session=session).exists():
                # Create 12 players as defined in your WerewolfGame class
                for i in range(12):
                    GamePlayer.objects.create(
                        game_session=session,
                        player_id=f"p{i}",
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
                    'status': db_player.status
                })

            session.current_phase = game._current_phase.name
            session.save()

            # Create response
            response = StartGameResponseDto(
                type="game_state",
                phase=session.current_phase,
                players=players_data
            )

            channel_layer = get_channel_layer()
            logger.info(f"channel layer is {channel_layer}")

            return Response(response.to_json())

        except GameSession.DoesNotExist:
            return Response(
                {'error': 'Game session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

    def destroy(self, request, pk=None):
        """
        Delete a game session and its associated data
        """
        try:
            session = GameSession.objects.get(pk=pk)

            # Delete from MongoDB
            game_store = GameStateStore()
            game_store.delete_game_state(str(session.session_id))

            # Delete associated players
            GamePlayer.objects.filter(game_session=session).delete()

            # Delete the session itself
            session.delete()

            return Response(
                {'message': 'Game session deleted successfully'},
                status=status.HTTP_200_OK
            )
        except GameSession.DoesNotExist:
            return Response(
                {'error': 'Game session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting game session: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    # TODO: fetch all available rooms, player
    @action(detail=False, methods=['GET'])
    def available_rooms(self, request):
        """
        Fetch all game sessions where all alive players have made their actions
        Returns rooms with their current state and waiting status
        """
        try:
            # Initialize MongoDB store
            game_store = GameStateStore()

            # Get all active sessions
            sessions = GameSession.objects.exclude(current_phase__in=['SETUP', 'GAME_OVER'])

            available_rooms = []
            for session in sessions:
                # Get alive players count
                alive_players = GamePlayer.objects.filter(
                    game_session=session,
                    status='ALIVE'
                ).count()

                # Get pending actions count from MongoDB
                pending_actions = game_store.get_pending_actions_count(
                    str(session.session_id),
                    session.round_count,
                    session.current_phase,
                    alive_players
                )

                # Get players data
                players = GamePlayer.objects.filter(game_session=session)
                players_data = [{
                    'player_id': player.player_id,
                    'name': f"Player {int(player.player_id.replace('p', '')) + 1}",
                    'role': player.role if session.current_phase != 'SETUP' else 'UNASSIGNED',
                    'status': player.status,
                    'is_policeman': player.is_policeman,
                    'position': int(player.player_id.replace('p', '')) + 1
                } for player in players]

                # Add room info
                room_info = {
                    'session_id': str(session.session_id),
                    'phase': session.current_phase,
                    'round': session.round_count,
                    'players': players_data,
                    'waiting_for_actions': pending_actions > 0,
                    'pending_actions_count': pending_actions,
                    'total_players': len(players_data),
                    'alive_players': alive_players
                }

                available_rooms.append(room_info)

            return Response({
                'rooms': available_rooms
            })

        except Exception as e:
            logger.error(f"Error fetching available rooms: {e}")
            return Response(
                {'error': 'Failed to fetch available rooms'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )