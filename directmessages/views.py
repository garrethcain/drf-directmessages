from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .apps import Inbox
from .models import Message
from .serializers import (
    ConversationSerializer,
    MessageSendSerializer,
    MessageSerializer,
    UnreadMessageSerializer,
)


User = get_user_model()


class MessageViewBase:
    permission_classes = [IsAuthenticated]

    def get_user(self):
        return self.request.user

    def get_recipient(self):
        return get_object_or_404(User, id=self.kwargs["pk"])


class UnreadMessagesView(MessageViewBase, views.APIView):
    def get(self, request):
        user = self.get_user()
        serializer = UnreadMessageSerializer(user)
        return Response(data=serializer.data)


class ConversationListView(MessageViewBase, generics.ListAPIView):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        user = self.get_user()
        return User.objects.filter(
            Q(sent_dm__recipient=user) | Q(received_dm__sender=user)
        ).distinct()


class MessageListView(MessageViewBase, generics.ListCreateAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        user1 = self.get_user()
        user2 = self.get_recipient()
        return Inbox.get_conversation(
            user1=user1, user2=user2, mark_read=True
        ).order_by("-sent_at")

    def create(self, request, *args, **kwargs):
        sender = self.get_user()
        recipient = self.get_recipient()
        content = request.data.get("content", "")

        if not content:
            return Response(
                {"detail": "content is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message, _ = Inbox.send_message(
            sender=sender, recipient=recipient, message=content
        )
        return Response(
            MessageSerializer(
                self.get_queryset(), many=True, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class MessageSendView(MessageViewBase, generics.CreateAPIView):
    serializer_class = MessageSendSerializer

    def create(self, request, *args, **kwargs):
        sender = self.get_user()
        recipient = self.get_recipient()
        content = request.data.get("content", "")

        if not content:
            return Response(
                {"detail": "content is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            message, _ = Inbox.send_message(
                sender=sender, recipient=recipient, message=content
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
