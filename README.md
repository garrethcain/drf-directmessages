# drf-directmessages

[![PyPI](https://img.shields.io/pypi/v/drf-directmessages.svg)](https://pypi.org/project/drf-directmessages/)
[![License](https://img.shields.io/pypi/l/drf-directmessages.svg)](https://github.com/garrethcain/drf-directmessages/blob/master/LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/drf-directmessages.svg)](https://pypi.org/project/drf-directmessages/)
[![Django](https://img.shields.io/badge/Django-4.2%20%7C%205.0%20%7C%205.1-green.svg)](https://pypi.org/project/drf-directmessages/)

A small, lightweight Django REST Framework library that adds direct messaging
between your users. Drop it into any DRF project, run migrations, and you have
a fully functional private messaging API.

## Features

- Send and receive direct messages between users
- List conversation partners with cursor-based pagination
- Retrieve all messages in a conversation (inbound messages are auto-marked as read)
- Total unread message count and per-conversation unread counts
- Soft-delete messages per user (the other participant still sees them)
- Django signals for `message_sent` and `message_read` events
- OpenAPI schema support via [drf-spectacular](https://github.com/tfranzel/drf-spectacular)
- Configurable recipient restrictions via `DIRECTMESSAGES_ALLOWED_RECIPIENTS`
- Self-messaging prevention (enforced at both model and service layer)

## Requirements

| Package | Version |
|---|---|
| Python | >= 3.10 |
| Django | >= 4.2 |
| Django REST Framework | >= 3.14 |

## Installation

Install with pip:

```bash
pip install drf-directmessages
```

Or with uv:

```bash
uv add drf-directmessages
```

Add the app to your Django project's `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "directmessages",
]
```

Run migrations:

```bash
python manage.py migrate
```

Mount the URLs in your project's `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("api/dm/", include("directmessages.urls")),
]
```

## Configuration

### `DIRECTMESSAGES_ALLOWED_RECIPIENTS`

An optional list of user IDs that act as a messaging whitelist. When set:

- Users **in** the list can message anyone.
- Users **not in** the list can only message users **in** the list.
- If the setting is `None` or an empty list (the default), there are no restrictions.

```python
# settings.py
DIRECTMESSAGES_ALLOWED_RECIPIENTS = [1, 2, 3]  # Only these users can be messaged by anyone
```

Default: `None` (no restrictions)

## API Endpoints

All endpoints require authentication. The table below assumes you mounted the
URLs at `api/dm/`.

| Method | Path | Description |
|---|---|---|
| GET | `api/dm/unread/` | Get your user ID and total unread message count |
| GET | `api/dm/conversations/` | List your conversation partners (paginated) |
| GET | `api/dm/conversations/unread/` | Get unread counts per conversation partner |
| GET | `api/dm/conversations/<id>/` | List messages with user `<id>` (paginated, auto-read) |
| POST | `api/dm/conversations/<id>/` | Send a message to user `<id>` |
| DELETE | `api/dm/messages/<id>/` | Soft-delete a message for yourself |
| POST | `api/dm/send/<id>/` | Send a message to user `<id>` |

All list endpoints use cursor-based pagination with a page size of 50.

## How-To Guides

### How to send a message

You can send a message in two ways: via the dedicated send endpoint or from
within a conversation.

**Using the send endpoint:**

```bash
curl -X POST http://localhost:8000/api/dm/send/2/ \
  -H "Authorization: Token your-token-here" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, world!"}'
```

```python
import requests

response = requests.post(
    "http://localhost:8000/api/dm/send/2/",
    headers={"Authorization": "Token your-token-here"},
    json={"content": "Hello, world!"},
)
print(response.status_code)  # 201
print(response.json())
```

Response (`201 Created`):

```json
{
  "id": 1,
  "sender": 1,
  "recipient": 2,
  "direction": "out",
  "sent_at": "2025-06-06T12:00:00Z",
  "read_at": null,
  "content": "Hello, world!"
}
```

**From within a conversation:**

```bash
curl -X POST http://localhost:8000/api/dm/conversations/2/ \
  -H "Authorization: Token your-token-here" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello again!"}'
```

This returns the full updated conversation (`201 Created`) rather than a single
message.

### How to list your conversations

```bash
curl http://localhost:8000/api/dm/conversations/ \
  -H "Authorization: Token your-token-here"
```

```python
import requests

response = requests.get(
    "http://localhost:8000/api/dm/conversations/",
    headers={"Authorization": "Token your-token-here"},
)
print(response.json())
```

Response:

```json
{
  "next": "http://localhost:8000/api/dm/conversations/?cursor=cj0xJnA9Mg%3D%3D",
  "previous": null,
  "results": [
    {
      "id": 2,
      "username": "jane",
      "first_name": "Jane",
      "last_name": "Doe"
    }
  ]
}
```

### How to get messages in a conversation

Retrieving messages automatically marks inbound messages as read.

```bash
curl http://localhost:8000/api/dm/conversations/2/ \
  -H "Authorization: Token your-token-here"
```

```python
import requests

response = requests.get(
    "http://localhost:8000/api/dm/conversations/2/",
    headers={"Authorization": "Token your-token-here"},
)
print(response.json())
```

Response:

```json
{
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "sender": 2,
      "recipient": 1,
      "direction": "in",
      "sent_at": "2025-06-06T12:00:00Z",
      "read_at": "2025-06-06T12:01:00Z",
      "content": "Hey there!"
    },
    {
      "id": 2,
      "sender": 1,
      "recipient": 2,
      "direction": "out",
      "sent_at": "2025-06-06T12:02:00Z",
      "read_at": null,
      "content": "Hello, world!"
    }
  ]
}
```

The `direction` field is relative to the authenticated user: `"in"` for messages
you received, `"out"` for messages you sent.

### How to check unread message counts

**Total unread count:**

```bash
curl http://localhost:8000/api/dm/unread/ \
  -H "Authorization: Token your-token-here"
```

```python
import requests

response = requests.get(
    "http://localhost:8000/api/dm/unread/",
    headers={"Authorization": "Token your-token-here"},
)
print(response.json())
```

Response:

```json
{
  "id": 1,
  "count": 5
}
```

**Per-conversation unread counts:**

```bash
curl http://localhost:8000/api/dm/conversations/unread/ \
  -H "Authorization: Token your-token-here"
```

```python
import requests

response = requests.get(
    "http://localhost:8000/api/dm/conversations/unread/",
    headers={"Authorization": "Token your-token-here"},
)
print(response.json())
```

Response:

```json
[
  {
    "partner_id": 2,
    "partner_username": "jane",
    "unread_count": 3
  },
  {
    "partner_id": 5,
    "partner_username": "bob",
    "unread_count": 1
  }
]
```

### How to delete a message

Deleting a message is a soft-delete that only hides it for the requesting user.
The other participant still sees the message.

```bash
curl -X DELETE http://localhost:8000/api/dm/messages/42/ \
  -H "Authorization: Token your-token-here"
```

```python
import requests

response = requests.delete(
    "http://localhost:8000/api/dm/messages/42/",
    headers={"Authorization": "Token your-token-here"},
)
print(response.status_code)  # 204
```

A successful deletion returns `204 No Content` with an empty body. If the
message doesn't exist or doesn't belong to you, you'll get a `404`.

### How to use signals

drf-directmessages fires two Django signals that you can connect to for
notifications, analytics, real-time updates, or any other side effects.

**`message_sent`** — fired when a new message is created.

**`message_read`** — fired when an unread message is marked as read.

Both signals provide `from_user` (the sender of the message) and `to` (the
recipient of the message). The signal sender is the `Message` instance.

```python
# your_app/signals.py
from django.dispatch import receiver
from directmessages.signals import message_sent, message_read


@receiver(message_sent)
def on_message_sent(sender, **kwargs):
    from_user = kwargs["from_user"]
    to = kwargs["to"]
    # sender is the Message instance
    # e.g. send a push notification, update a feed, log analytics
    print(f"Message {sender.id} sent from {from_user} to {to}")


@receiver(message_read)
def on_message_read(sender, **kwargs):
    from_user = kwargs["from_user"]
    to = kwargs["to"]
    # e.g. notify the sender that their message was read
    print(f"Message {sender.id} from {from_user} read by {to}")
```

### How to restrict who can message whom

Use `DIRECTMESSAGES_ALLOWED_RECIPIENTS` in your Django settings to control
which users can receive messages from unrestricted users.

```python
# settings.py

# Only users 1, 2, and 3 can receive messages from anyone.
# All other users can only message users in this list.
DIRECTMESSAGES_ALLOWED_RECIPIENTS = [1, 2, 3]
```

Common use cases:

- **Support staff**: list support agent IDs so customers can only message agents.
- **Admin-only**: restrict to admin users for a moderated messaging system.
- **Unset** (default): anyone can message anyone.

### How to integrate with drf-spectacular

All views include `@extend_schema` decorators. To serve interactive API docs,
add `drf-spectacular` to your project:

```bash
pip install drf-spectacular
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "drf_spectacular",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "My API",
    "VERSION": "1.0.0",
}
```

```python
# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # ...
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
```

## Signals Reference

| Signal | Sender | Keyword Arguments | Fired When |
|---|---|---|---|
| `message_sent` | `Message` instance | `from_user` (User), `to` (User) | A message is created |
| `message_read` | `Message` instance | `from_user` (User), `to` (User) | An unread message is marked as read |

## Running Tests

Clone the repository and run the test suite:

```bash
git clone https://github.com/garrethcain/drf-directmessages.git
cd drf-directmessages
uv sync --group dev
uv run pytest
```

## License

This project is licensed under the [GNU Lesser General Public License v3.0 or later](https://spdx.org/licenses/LGPL-3.0-or-later.html).
