from django.dispatch import Signal

message_sent = Signal()  # Signal(providing_args=['from_user', 'to'])
message_read = Signal()  # Signal(providing_args=['from_user', 'to'])
