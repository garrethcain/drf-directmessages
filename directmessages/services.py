from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count, Q

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
        return Message.objects.filter(
            recipient=user, read_at=None, hidden_for_recipient__isnull=True
        )

    def get_unread_message_count(self, user):
        return self.get_unread_messages(user).count()

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
        visible = Message.objects.filter(
            Q(sender=user, hidden_for_sender__isnull=True)
            | Q(recipient=user, hidden_for_recipient__isnull=True)
        )
        sender_ids = visible.filter(sender=user).values_list("recipient_id", flat=True)
        recipient_ids = visible.filter(recipient=user).values_list(
            "sender_id", flat=True
        )
        contact_ids = set(sender_ids) | set(recipient_ids)
        return list(User.objects.filter(id__in=contact_ids)) if contact_ids else []

    def get_conversation(
        self, user1, user2, limit=None, reverse_order=False, mark_read=False
    ):
        users = [user1, user2]
        order = "-pk" if reverse_order else "pk"
        conversation = (
            Message.objects.filter(sender__in=users, recipient__in=users)
            .exclude(
                Q(sender=user1, hidden_for_sender__isnull=False)
                | Q(recipient=user1, hidden_for_recipient__isnull=False)
            )
            .order_by(order)
        )

        if limit is not None:
            conversation = conversation[:limit]

        if mark_read:
            unread = [
                m for m in conversation if m.recipient == user1 and m.read_at is None
            ]
            for message in unread:
                self.mark_as_read(message)

        return conversation

    def get_unread_counts_per_conversation(self, user):
        unread = (
            Message.objects.filter(
                recipient=user, read_at=None, hidden_for_recipient__isnull=True
            )
            .values("sender_id")
            .annotate(unread_count=Count("id"))
        )
        return {row["sender_id"]: row["unread_count"] for row in unread}

    def delete_message(self, user, message_id):
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return False

        now = timezone.now()
        if message.sender == user:
            message.hidden_for_sender = now
            message.save(update_fields=["hidden_for_sender"])
            return True
        elif message.recipient == user:
            message.hidden_for_recipient = now
            message.save(update_fields=["hidden_for_recipient"])
            return True
        return False

    def mark_as_read(self, message):
        if message.read_at is None:
            message.read_at = timezone.now()
            message_read.send(
                sender=message, from_user=message.sender, to=message.recipient
            )
            message.save(update_fields=["read_at"])
