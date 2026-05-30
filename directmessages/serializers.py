from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import Message


User = get_user_model()


class UnreadMessageSerializer(serializers.ModelSerializer):
    count = serializers.SerializerMethodField()

    def get_count(self, obj):
        return Message.objects.filter(read_at=None, recipient=obj).count()

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


class MessageSerializer(serializers.ModelSerializer):
    direction = serializers.SerializerMethodField()

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
