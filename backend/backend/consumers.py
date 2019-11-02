"""
Consumers for routing object
"""
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer



class LectureConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()
        lecture_id = self.scope["url_route"]["kwargs"]["pk"]
        async_to_sync(self.channel_layer.group_add)(f'lectures_update_group_{lecture_id}', self.channel_name)

    def disconnect(self, close_code):
        pass

    def trigger(self, event):
        message = event['message']
        self.send(text_data=json.dumps(message))