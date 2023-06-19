from django.urls import path
from .views import (
    ConversationListView,
    MessageListView,
    UnreadMessagesView,
    MessageSendView
)


urlpatterns = [
    path("unread/", view=UnreadMessagesView.as_view()),
    path("conversations/", view=ConversationListView.as_view()),
    path("conversations/<int:pk>", view=MessageListView.as_view()),
    path("send/<int:pk>/", view=MessageSendView.as_view()),
]
