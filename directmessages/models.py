from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()


class Message(models.Model):
    content = models.TextField("Content")
    sender = models.ForeignKey(
        User,
        related_name="sent_dm",
        verbose_name="Sender",
        on_delete=models.CASCADE,
    )
    recipient = models.ForeignKey(
        User,
        related_name="received_dm",
        verbose_name="Recipient",
        on_delete=models.CASCADE,
    )
    sent_at = models.DateTimeField("sent at", auto_now_add=True)
    read_at = models.DateTimeField("read at", null=True, blank=True)
    hidden_for_sender = models.DateTimeField(null=True, blank=True)
    hidden_for_recipient = models.DateTimeField(null=True, blank=True)

    @property
    def unread(self):
        return self.read_at is None

    def __str__(self):
        return f"{self.id}/{self.sender}/{self.recipient}/{self.content}"

    def save(self, **kwargs):
        if self.sender == self.recipient:
            raise ValidationError("You can't send messages to yourself")
        super(Message, self).save(**kwargs)
