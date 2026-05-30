from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from .models import Message
from .signals import message_read, message_sent


User = get_user_model()


class MessagingService:
    def send_message(self, sender, recipient, message):
        if sender == recipient:
            raise ValidationError("You can't send messages to yourself.")

        message = Message(
            sender=sender,
            recipient=recipient,
            content=str(message),
        )
        message.save()

        message_sent.send(
            sender=message, from_user=message.sender, to=message.recipient
        )

        return message, 200

    def get_unread_messages(self, user):
        return Message.objects.filter(recipient=user, read_at=None)

    def get_unread_message_count(self, user):
        return Message.objects.filter(recipient=user, read_at=None).count()

    def read_message(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            self.mark_as_read(message)
            return message.content
        except Message.DoesNotExist:
            return None

    def read_message_formatted(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            self.mark_as_read(message)
            return f"{message.sender.email}: {message.content}"
        except Message.DoesNotExist:
            return None

    def get_conversations(self, user):
        sender_ids = Message.objects.filter(sender=user).values_list(
            "recipient_id", flat=True
        )
        recipient_ids = Message.objects.filter(recipient=user).values_list(
            "sender_id", flat=True
        )
        contact_ids = set(sender_ids) | set(recipient_ids)
        return list(User.objects.filter(id__in=contact_ids)) if contact_ids else []

    def get_conversation(
        self, user1, user2, limit=None, reverse_order=False, mark_read=False
    ):
        users = [user1, user2]
        order = "-pk" if reverse_order else "pk"
        conversation = Message.objects.filter(
            sender__in=users, recipient__in=users
        ).order_by(order)

        if limit is not None:
            conversation = conversation[:limit]

        if mark_read:
            unread = [
                m for m in conversation if m.recipient == user1 and m.read_at is None
            ]
            for message in unread:
                self.mark_as_read(message)

        return conversation

    def mark_as_read(self, message):
        if message.read_at is None:
            message.read_at = timezone.now()
            message_read.send(
                sender=message, from_user=message.sender, to=message.recipient
            )
            message.save(update_fields=["read_at"])
