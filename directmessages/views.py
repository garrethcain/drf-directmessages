
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from rest_framework import (
    generics,
    status,
    views)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .apps import Inbox
from .models import Message
from .serializers import (
    ConversationSerializer,
    MessageSendSerializer,
    MessageSerializer,
    UnreadMessageSerializer)
from .services import MessagingService


User = get_user_model()


class MessageViewBase:
    permission_classes = [IsAuthenticated,]

    def get_user(self):
        return self.request.user

    def get_recipient(self):
        return User.objects.get(id=self.kwargs['pk'])


class UnreadMessagesView(MessageViewBase, views.APIView):
    serializer_class = UnreadMessageSerializer

    def get(self, request):
        user = self.get_user()
        serializer = UnreadMessageSerializer(user)
        return Response(data=serializer.data)


class ConversationListView(MessageViewBase, generics.ListAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Inbox.get_conversations(self.get_user())


class MessageListView(MessageViewBase, generics.ListCreateAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        user1 = self.get_user()
        user2 = self.kwargs['pk']
        return Inbox.get_conversation(
                user1=user1, user2=user2, mark_read=True).order_by('-sent_at')

    def create(self, request, *args, **kwargs):
        sender = self.get_user()
        recipient = self.get_recipient()
        content = request.data.get('content')
        _ = Message.objects.create(
                sender=sender, recipient=recipient, content=content)
        return Response(MessageSerializer(
                self.get_queryset(),
                many=True).data, status=status.HTTP_201_CREATED)


class MessageSendView(MessageViewBase, generics.CreateAPIView):
    serializer_class = MessageSendSerializer

    def create(self, request, *args, **kwargs):
        sender = self.get_user()
        recipient = self.get_recipient()
        content = request.data.get('content')

        ms = MessagingService()
        try:
            ms.send_message(
                    sender=sender, recipient=recipient, message=content)
        except ValidationError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_201_CREATED)
