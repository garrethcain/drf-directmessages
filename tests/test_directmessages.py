from directmessages.apps import Inbox
from directmessages.models import Message

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


def create_user(username, email=None):
    return User.objects.create(
        username=username,
        email=email or f"{username}@tests.com",
    )


class MessageSendTestCase(TestCase):
    def setUp(self):
        self.u1 = create_user("user1", "someuser@tests.com")
        self.u2 = create_user("user2", "someotheruser@tests.com")

    def test_send_message(self):
        init_value = Message.objects.all().count()

        message, code = Inbox.send_message(self.u1, self.u2, "This is a message")

        after_value = Message.objects.all().count()

        self.assertEqual(init_value + 1, after_value)
        self.assertEqual(code, 200)
        self.assertEqual(message.content, "This is a message")

    def test_send_message_to_self_raises(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            Inbox.send_message(self.u1, self.u1, "Talking to myself")

    def test_read_nonexistent_message_returns_none(self):
        result = Inbox.read_message(99999)
        self.assertIsNone(result)

    def test_read_formatted_nonexistent_message_returns_none(self):
        result = Inbox.read_message_formatted(99999)
        self.assertIsNone(result)


class MessageReadingTestCase(TestCase):
    def setUp(self):
        self.u1 = create_user("user1", "someuser@tests.com")
        self.u2 = create_user("user2", "someotheruser@tests.com")

    def test_unread_messages(self):
        Inbox.send_message(self.u1, self.u2, "This is a message")

        unread_messages = Inbox.get_unread_messages(self.u1)
        unread_messages2 = Inbox.get_unread_messages(self.u2)

        self.assertEqual(unread_messages.count(), 0)
        self.assertEqual(unread_messages2.count(), 1)

    def test_reading_messages(self):
        Inbox.send_message(self.u2, self.u1, "This is another message")

        unread_messages = Inbox.get_unread_messages(self.u1)
        self.assertEqual(unread_messages.count(), 1)

        content = Inbox.read_message(unread_messages[0].id)
        unread_messages_after = Inbox.get_unread_messages(self.u1)

        self.assertEqual(content, "This is another message")
        self.assertEqual(unread_messages_after.count(), 0)

    def test_reading_formatted(self):
        msg, _ = Inbox.send_message(self.u2, self.u1, "This is just another message")

        unread_messages = Inbox.get_unread_messages(self.u1)
        self.assertEqual(unread_messages.count(), 1)

        formatted = Inbox.read_message_formatted(msg.id)
        unread_messages_after = Inbox.get_unread_messages(self.u1)

        self.assertEqual(formatted, f"{self.u2.email}: This is just another message")
        self.assertEqual(unread_messages_after.count(), 0)


class ConversationTestCase(TestCase):
    def setUp(self):
        self.u1 = create_user("user1", "user@tests.com")
        self.u2 = create_user("admin", "admin@tests.com")
        self.u3 = create_user("postman", "postman@tests.com")
        self.u4 = create_user("chef", "chef@tests.com")

        Inbox.send_message(self.u1, self.u2, "This is a message to User 2")
        Inbox.send_message(self.u1, self.u3, "This is a message to User 3")
        Inbox.send_message(self.u1, self.u4, "This is a message to User 4")

        Inbox.send_message(self.u2, self.u1, "This is a message to User 1")
        Inbox.send_message(self.u2, self.u3, "This is a message to User 3")
        Inbox.send_message(self.u2, self.u4, "This is a message to User 4")

        Inbox.send_message(
            self.u1, self.u2, "Hey, thanks for sending this message back"
        )
        Inbox.send_message(self.u2, self.u1, "No problem")

    def test_all_conversations(self):
        conversation_partners = Inbox.get_conversations(self.u1)

        self.assertEqual(len(conversation_partners), 3)
        self.assertIn(self.u2, conversation_partners)
        self.assertIn(self.u3, conversation_partners)
        self.assertIn(self.u4, conversation_partners)

        self.assertNotIn(self.u1, conversation_partners)

    def test_single_conversation(self):
        unread_messages = Inbox.get_unread_messages(self.u1)

        self.assertEqual(unread_messages.count(), 2)

        conversation = Inbox.get_conversation(self.u1, self.u2)
        unread_messages_after = Inbox.get_unread_messages(self.u1)

        self.assertEqual(conversation.count(), 4)
        self.assertEqual(unread_messages_after.count(), 2)

        conversation_limited = Inbox.get_conversation(
            self.u1, self.u2, limit=2, reverse_order=True
        )
        self.assertEqual(conversation_limited.count(), 2)

        self.assertEqual(conversation[0].content, "This is a message to User 2")
        self.assertEqual(conversation[len(conversation) - 1].content, "No problem")
        self.assertEqual(conversation_limited[0].content, "No problem")
        self.assertEqual(
            conversation_limited[len(conversation_limited) - 1].content,
            "Hey, thanks for sending this message back",
        )


class UnreadMessagesAPIViewTestCase(TestCase):
    def setUp(self):
        self.user = create_user("auth_user", "auth@tests.com")
        self.other = create_user("other_user", "other@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_unread_count_zero(self):
        response = self.client.get("/unread/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_unread_count_after_message(self):
        Inbox.send_message(self.other, self.user, "Hello")
        response = self.client.get("/unread/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_unread_requires_auth(self):
        anon_client = APIClient()
        response = anon_client.get("/unread/")
        self.assertEqual(response.status_code, 403)


class ConversationListAPIViewTestCase(TestCase):
    def setUp(self):
        self.user = create_user("auth_user", "auth@tests.com")
        self.friend = create_user("friend", "friend@tests.com")
        self.stranger = create_user("stranger", "stranger@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_empty_conversations(self):
        response = self.client.get("/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_conversations_returns_partners(self):
        Inbox.send_message(self.user, self.friend, "Hi friend")
        response = self.client.get("/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.friend.id)

    def test_conversations_excludes_self(self):
        self.assertNotIn(self.user, Inbox.get_conversations(self.user))

    def test_conversations_requires_auth(self):
        anon_client = APIClient()
        response = anon_client.get("/conversations/")
        self.assertEqual(response.status_code, 403)


class MessageListAPIViewTestCase(TestCase):
    def setUp(self):
        self.user = create_user("auth_user", "auth@tests.com")
        self.friend = create_user("friend", "friend@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_conversation_messages(self):
        Inbox.send_message(self.user, self.friend, "Hi")
        Inbox.send_message(self.friend, self.user, "Hello")

        response = self.client.get(f"/conversations/{self.friend.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_get_conversation_marks_inbound_as_read(self):
        Inbox.send_message(self.friend, self.user, "Unread msg")

        self.assertEqual(Inbox.get_unread_messages(self.user).count(), 1)

        self.client.get(f"/conversations/{self.friend.id}/")

        self.assertEqual(Inbox.get_unread_messages(self.user).count(), 0)

    def test_get_conversation_does_not_mark_outbound_as_read(self):
        Inbox.send_message(self.user, self.friend, "My msg")

        self.assertEqual(Inbox.get_unread_messages(self.friend).count(), 1)

        self.client.get(f"/conversations/{self.friend.id}/")

        self.assertEqual(Inbox.get_unread_messages(self.friend).count(), 1)

    def test_post_message_via_conversation(self):
        response = self.client.post(
            f"/conversations/{self.friend.id}/",
            {"content": "New message"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.count(), 1)

    def test_post_message_empty_content_returns_400(self):
        response = self.client.post(
            f"/conversations/{self.friend.id}/",
            {"content": ""},
        )
        self.assertEqual(response.status_code, 400)

    def test_post_message_missing_content_returns_400(self):
        response = self.client.post(f"/conversations/{self.friend.id}/", {})
        self.assertEqual(response.status_code, 400)

    def test_conversation_with_nonexistent_user_returns_404(self):
        response = self.client.get("/conversations/99999/")
        self.assertEqual(response.status_code, 404)

    def test_message_direction_incoming(self):
        Inbox.send_message(self.friend, self.user, "From friend")

        response = self.client.get(f"/conversations/{self.friend.id}/")
        inbound = [m for m in response.data if m["direction"] == "in"]
        self.assertEqual(len(inbound), 1)

    def test_message_direction_outgoing(self):
        Inbox.send_message(self.user, self.friend, "To friend")

        response = self.client.get(f"/conversations/{self.friend.id}/")
        outbound = [m for m in response.data if m["direction"] == "out"]
        self.assertEqual(len(outbound), 1)


class MessageSendAPIViewTestCase(TestCase):
    def setUp(self):
        self.user = create_user("auth_user", "auth@tests.com")
        self.friend = create_user("friend", "friend@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_send_message_success(self):
        response = self.client.post(
            f"/send/{self.friend.id}/",
            {"content": "Hello friend"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(response.data["content"], "Hello friend")

    def test_send_message_empty_content_returns_400(self):
        response = self.client.post(
            f"/send/{self.friend.id}/",
            {"content": ""},
        )
        self.assertEqual(response.status_code, 400)

    def test_send_message_to_self_returns_400(self):
        response = self.client.post(
            f"/send/{self.user.id}/",
            {"content": "Talking to myself"},
        )
        self.assertEqual(response.status_code, 400)

    def test_send_message_to_nonexistent_user_returns_404(self):
        response = self.client.post(
            "/send/99999/",
            {"content": "Hello nobody"},
        )
        self.assertEqual(response.status_code, 404)

    def test_send_requires_auth(self):
        anon_client = APIClient()
        response = anon_client.post(
            f"/send/{self.friend.id}/",
            {"content": "Hello"},
        )
        self.assertEqual(response.status_code, 403)
