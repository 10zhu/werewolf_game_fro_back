# game/consumer.py
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)

class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        logger.info(f"websocket connect : {self.scope}")
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'game_{self.game_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        await self.send_json({
            "message": "hello",
            "type": "welcome"
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive_json(self, content):
        logger.info(f"websocket receiving json content {content}")
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_message',
                'message': content
            }
        )

    async def game_message(self, event):
        logger.info(f"websocket receiving game message {event}")
        await self.send_json(event['message'])


