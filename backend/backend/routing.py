"""
Routing for websocket endpoints
"""
from django.urls import path

from channels.routing import ProtocolTypeRouter, URLRouter

from .consumers import LectureConsumer

application = ProtocolTypeRouter({
    "websocket": URLRouter([
        path('ws/lectures/<int:pk>', LectureConsumer, name="lecture-ws"),
    ])
})
