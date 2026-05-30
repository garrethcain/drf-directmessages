from django.contrib.auth import get_user_model

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Message


User = get_user_model()


class UnreadMessageSerializer(serializers.ModelSerializer):
    count = serializers.SerializerMethodField()

    @extend_schema_field(serializers.IntegerField())
    def get_count(self, obj):
        return Message.objects.filter(
            read_at=None, recipient=obj, hidden_for_recipient__isnull=True
        ).count()

    class Meta:
        model = User
        fields = (
            "id",
            "count",
        )


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
        )


class ConversationUnreadSerializer(serializers.Serializer):
    partner_id = serializers.IntegerField(help_text="ID of the conversation partner")
    partner_username = serializers.CharField(
        help_text="Username of the conversation partner"
    )
    unread_count = serializers.IntegerField(
        help_text="Number of unread messages from this partner"
    )


class MessageSerializer(serializers.ModelSerializer):
    direction = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ChoiceField(choices=["in", "out"]))
    def get_direction(self, obj):
        if not isinstance(obj, Message):
            return ""
        request = self.context.get("request")
        user = request.user if request else None
        return "in" if user == obj.recipient else "out"

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "recipient",
            "direction",
            "sent_at",
            "read_at",
            "content",
        )
        read_only_fields = (
            "sender",
            "recipient",
            "sent_at",
            "read_at",
        )


class MessageSendSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = (
            "id",
            "content",
        )


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
