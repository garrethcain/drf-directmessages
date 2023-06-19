from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import Message


User = get_user_model()


class UnreadMessageSerializer(serializers.ModelSerializer):
    count = serializers.SerializerMethodField()

    def get_count(self, obj):
        breakpoint()
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
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
        )


class MessageSerializer(serializers.ModelSerializer):
    direction = serializers.SerializerMethodField()

    def get_direction(self, obj):
        request = self.context.get("request")
        user_id = request.user if request else None
        if type(obj) != Message:
            return ""
        return (
            "in" if user_id == obj.recipient
            else
            "out"
        )

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
        read_only_fields = (
            " sender",
            "sent_at",
            "read_at",
        )
