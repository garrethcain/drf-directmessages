from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Q

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, views
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .apps import Inbox
from .models import Message
from .serializers import (
    ConversationSerializer,
    ConversationUnreadSerializer,
    ErrorSerializer,
    MessageSendSerializer,
    MessageSerializer,
    UnreadMessageSerializer,
)


User = get_user_model()


class MessageCursorPagination(CursorPagination):
    ordering = "-sent_at"
    page_size = 50


class ConversationCursorPagination(CursorPagination):
    ordering = "-pk"
    page_size = 50


class MessageViewBase:
    permission_classes = [IsAuthenticated]

    def get_user(self):
        return self.request.user

    def get_recipient(self):
        return get_object_or_404(User, id=self.kwargs["pk"])


@extend_schema(
    tags=["Messages"],
    summary="Get unread message count",
    description="Returns the authenticated user's ID and count of unread messages.",
    responses={200: UnreadMessageSerializer},
)
class UnreadMessagesView(MessageViewBase, views.APIView):
    def get(self, request):
        user = self.get_user()
        serializer = UnreadMessageSerializer(user)
        return Response(data=serializer.data)


@extend_schema(
    tags=["Conversations"],
    summary="List conversation partners",
    description="Returns a paginated list of users the authenticated user has had conversations with.",
    responses={200: ConversationSerializer(many=True)},
)
class ConversationListView(MessageViewBase, generics.ListAPIView):
    serializer_class = ConversationSerializer
    pagination_class = ConversationCursorPagination

    def get_queryset(self):
        user = self.get_user()
        return User.objects.filter(
            Q(sent_dm__recipient=user, sent_dm__hidden_for_sender__isnull=True)
            | Q(
                received_dm__sender=user, received_dm__hidden_for_recipient__isnull=True
            )
        ).distinct()


@extend_schema(
    tags=["Conversations"],
    summary="Unread counts per conversation",
    description="Returns a list of conversation partners with their unread message counts.",
    responses={200: ConversationUnreadSerializer(many=True)},
)
class ConversationUnreadView(MessageViewBase, generics.ListAPIView):
    serializer_class = ConversationUnreadSerializer
    pagination_class = None

    def get_queryset(self):
        return []

    def list(self, request, *args, **kwargs):
        user = self.get_user()
        counts = Inbox.get_unread_counts_per_conversation(user)
        if not counts:
            return Response([])

        partners = User.objects.filter(id__in=counts.keys())
        data = [
            {
                "partner_id": p.id,
                "partner_username": p.username,
                "unread_count": counts[p.id],
            }
            for p in partners
        ]
        serializer = ConversationUnreadSerializer(data, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Messages"],
    summary="List messages in a conversation",
    description="Returns a paginated list of messages between the authenticated user and the specified user. Inbound messages are marked as read on access.",
    responses={200: MessageSerializer(many=True)},
)
@extend_schema(
    tags=["Messages"],
    summary="Send a message",
    description="Send a message to the specified user from within a conversation view.",
    request=MessageSendSerializer,
    responses={
        201: MessageSerializer(many=True),
        400: ErrorSerializer,
    },
    methods=["POST"],
)
class MessageListView(MessageViewBase, generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    pagination_class = MessageCursorPagination

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


@extend_schema(
    tags=["Messages"],
    summary="Delete a message",
    description="Soft-deletes a message for the authenticated user. The message remains visible to the other participant.",
    responses={
        204: None,
        404: ErrorSerializer,
    },
)
class MessageDeleteView(MessageViewBase, generics.DestroyAPIView):
    def destroy(self, request, *args, **kwargs):
        message_id = kwargs.get("pk")
        user = self.get_user()
        success = Inbox.delete_message(user, message_id)

        if not success:
            return Response(
                {"detail": "Message not found or not authorized."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Messages"],
    summary="Send a direct message",
    description="Send a direct message to the specified user.",
    request=MessageSendSerializer,
    responses={
        201: MessageSerializer,
        400: ErrorSerializer,
    },
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
