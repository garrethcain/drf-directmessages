from directmessages.apps import Inbox
from directmessages.models import Message

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
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
        self.assertEqual(len(response.data["results"]), 0)

    def test_conversations_returns_partners(self):
        Inbox.send_message(self.user, self.friend, "Hi friend")
        response = self.client.get("/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.friend.id)

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
        self.assertEqual(len(response.data["results"]), 2)

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
        inbound = [m for m in response.data["results"] if m["direction"] == "in"]
        self.assertEqual(len(inbound), 1)

    def test_message_direction_outgoing(self):
        Inbox.send_message(self.user, self.friend, "To friend")

        response = self.client.get(f"/conversations/{self.friend.id}/")
        outbound = [m for m in response.data["results"] if m["direction"] == "out"]
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


class SoftDeleteTestCase(TestCase):
    def setUp(self):
        self.user = create_user("deleter", "deleter@tests.com")
        self.friend = create_user("friend", "friend@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_sender_deletes_hides_for_sender_only(self):
        msg, _ = Inbox.send_message(self.user, self.friend, "Oops")

        response = self.client.delete(f"/messages/{msg.id}/")
        self.assertEqual(response.status_code, 204)

        conversation = Inbox.get_conversation(self.user, self.friend)
        self.assertEqual(conversation.count(), 0)

        conversation_friend = Inbox.get_conversation(self.friend, self.user)
        self.assertEqual(conversation_friend.count(), 1)

    def test_recipient_deletes_hides_for_recipient_only(self):
        msg, _ = Inbox.send_message(self.friend, self.user, "Hello")

        response = self.client.delete(f"/messages/{msg.id}/")
        self.assertEqual(response.status_code, 204)

        conversation = Inbox.get_conversation(self.user, self.friend)
        self.assertEqual(conversation.count(), 0)

        conversation_friend = Inbox.get_conversation(self.friend, self.user)
        self.assertEqual(conversation_friend.count(), 1)

    def test_both_delete_fully_hides(self):
        msg, _ = Inbox.send_message(self.user, self.friend, "Bye")

        self.client.delete(f"/messages/{msg.id}/")

        friend_client = APIClient()
        friend_client.force_authenticate(user=self.friend)
        friend_client.delete(f"/messages/{msg.id}/")

        conversation_user = Inbox.get_conversation(self.user, self.friend)
        conversation_friend = Inbox.get_conversation(self.friend, self.user)
        self.assertEqual(conversation_user.count(), 0)
        self.assertEqual(conversation_friend.count(), 0)

    def test_delete_nonexistent_message_returns_404(self):
        response = self.client.delete("/messages/99999/")
        self.assertEqual(response.status_code, 404)

    def test_delete_requires_auth(self):
        msg, _ = Inbox.send_message(self.user, self.friend, "Secret")
        anon_client = APIClient()
        response = anon_client.delete(f"/messages/{msg.id}/")
        self.assertEqual(response.status_code, 403)

    def test_deleted_message_excluded_from_unread(self):
        msg, _ = Inbox.send_message(self.friend, self.user, "Unread")
        self.assertEqual(Inbox.get_unread_messages(self.user).count(), 1)

        self.client.delete(f"/messages/{msg.id}/")
        self.assertEqual(Inbox.get_unread_messages(self.user).count(), 0)

    def test_deleted_message_excluded_from_conversations(self):
        msg, _ = Inbox.send_message(self.user, self.friend, "Only message")
        self.client.delete(f"/messages/{msg.id}/")

        partners = Inbox.get_conversations(self.user)
        self.assertNotIn(self.friend, partners)

    def test_double_delete_idempotent(self):
        msg, _ = Inbox.send_message(self.user, self.friend, "Test")

        self.client.delete(f"/messages/{msg.id}/")
        response = self.client.delete(f"/messages/{msg.id}/")
        self.assertEqual(response.status_code, 204)


class PaginationTestCase(TestCase):
    def setUp(self):
        self.user = create_user("pager", "pager@tests.com")
        self.friend = create_user("pal", "pal@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_conversations_paginated_response_shape(self):
        response = self.client.get("/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_messages_paginated_response_shape(self):
        Inbox.send_message(self.user, self.friend, "Hi")
        response = self.client.get(f"/conversations/{self.friend.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_messages_pagination_cursor(self):
        for i in range(55):
            Inbox.send_message(self.user, self.friend, f"Message {i}")

        response = self.client.get(f"/conversations/{self.friend.id}/")
        self.assertEqual(len(response.data["results"]), 50)
        self.assertIsNotNone(response.data["next"])

        response2 = self.client.get(response.data["next"])
        self.assertEqual(len(response2.data["results"]), 5)
        self.assertIsNone(response2.data["next"])


class ConversationUnreadAPITestCase(TestCase):
    def setUp(self):
        self.user = create_user("reader", "reader@tests.com")
        self.friend1 = create_user("pal1", "pal1@tests.com")
        self.friend2 = create_user("pal2", "pal2@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_no_conversations_returns_empty(self):
        response = self.client.get("/conversations/unread/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_single_conversation_unread_count(self):
        Inbox.send_message(self.friend1, self.user, "Hello")
        Inbox.send_message(self.friend1, self.user, "Hello again")

        response = self.client.get("/conversations/unread/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["partner_id"], self.friend1.id)
        self.assertEqual(response.data[0]["unread_count"], 2)

    def test_multiple_conversations_unread_counts(self):
        Inbox.send_message(self.friend1, self.user, "From pal1")
        Inbox.send_message(self.friend1, self.user, "From pal1 again")
        Inbox.send_message(self.friend2, self.user, "From pal2")

        response = self.client.get("/conversations/unread/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        by_id = {r["partner_id"]: r["unread_count"] for r in response.data}
        self.assertEqual(by_id[self.friend1.id], 2)
        self.assertEqual(by_id[self.friend2.id], 1)

    def test_read_messages_excluded_from_count(self):
        msg, _ = Inbox.send_message(self.friend1, self.user, "Read me")
        Inbox.read_message(msg.id)

        Inbox.send_message(self.friend1, self.user, "Unread")

        response = self.client.get("/conversations/unread/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["unread_count"], 1)

    def test_sent_messages_not_counted(self):
        Inbox.send_message(self.user, self.friend1, "From me")

        response = self.client.get("/conversations/unread/")
        self.assertEqual(response.data, [])

    def test_unread_requires_auth(self):
        anon_client = APIClient()
        response = anon_client.get("/conversations/unread/")
        self.assertEqual(response.status_code, 403)


class RestrictRecipientTestCase(TestCase):
    def setUp(self):
        self.customer = create_user("customer", "customer@tests.com")
        self.support = create_user("support", "support@tests.com")
        self.other = create_user("other", "other@tests.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    @override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=None)
    def test_no_setting_means_no_restriction(self):
        msg, code = Inbox.send_message(self.customer, self.other, "Hi")
        self.assertEqual(code, 200)

    @override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[])
    def test_empty_list_means_no_restriction(self):
        msg, code = Inbox.send_message(self.customer, self.other, "Hi")
        self.assertEqual(code, 200)

    @override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[])
    def test_user_can_message_allowed_recipient(self):
        with override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[self.support.id]):
            msg, code = Inbox.send_message(self.customer, self.support, "Help!")
            self.assertEqual(code, 200)

    @override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[])
    def test_user_cannot_message_non_allowed(self):
        with override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[self.support.id]):
            with self.assertRaises(ValidationError):
                Inbox.send_message(self.customer, self.other, "Hi")

    @override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[])
    def test_allowed_user_can_message_anyone(self):
        with override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[self.support.id]):
            msg, code = Inbox.send_message(self.support, self.customer, "Reply")
            self.assertEqual(code, 200)

            msg2, code2 = Inbox.send_message(self.support, self.other, "Outreach")
            self.assertEqual(code2, 200)

    @override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[])
    def test_api_returns_400_for_restricted_recipient(self):
        with override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[self.support.id]):
            support_client = APIClient()
            support_client.force_authenticate(user=self.support)
            support_client.post(
                f"/send/{self.customer.id}/",
                {"content": "Hello customer"},
            )

            response = self.client.post(
                f"/send/{self.other.id}/",
                {"content": "Hi"},
            )
            self.assertEqual(response.status_code, 400)

    @override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[])
    def test_api_allows_message_to_allowed_recipient(self):
        with override_settings(DIRECTMESSAGES_ALLOWED_RECIPIENTS=[self.support.id]):
            response = self.client.post(
                f"/send/{self.support.id}/",
                {"content": "Help me!"},
            )
            self.assertEqual(response.status_code, 201)
