from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


# from django.contrib.auth.models import User

User = get_user_model()


class Message(models.Model):
    """
    A private directmessage
    """
    content = models.TextField('Content')
    sender = models.ForeignKey(User,
                               related_name='sent_dm',
                               verbose_name="Sender",
                               on_delete=models.CASCADE)
    recipient = models.ForeignKey(User,
                                  related_name='received_dm',
                                  verbose_name="Recipient",
                                  on_delete=models.CASCADE)
    sent_at = models.DateTimeField("sent at", auto_now=True)
    read_at = models.DateTimeField("read at", null=True, blank=True)

    @property
    def unread(self):
        """
        returns whether the message was read or not
        """
        return self.read_at is None

    def __str__(self):
        return f"{self.id}/{self.sender}/{self.recipient}/{self.content}"

    def save(self, **kwargs):
        if self.sender == self.recipient:
            raise ValidationError("You can't send messages to yourself")

        if not self.id:
            self.sent_at = timezone.now()
        super(Message, self).save(**kwargs)
