# CHANGELOG


## v0.11.0 (2026-06-06)

### Chores

- Update the docs and changed the licence
  ([`29c6062`](https://github.com/garrethcain/drf-directmessages/commit/29c6062a58678d7bdaf008fe94d18a002c4cbe5f))

### Features

- Added a whitelist for recipients
  ([`485b26f`](https://github.com/garrethcain/drf-directmessages/commit/485b26fea79a4efd3fb1994934d4072e949d5e7f))


## v0.10.0 (2026-05-30)

### Features

- Add drf-spectacular OpenAPI schema annotations
  ([`66b9397`](https://github.com/garrethcain/drf-directmessages/commit/66b93972035b06b4192090f4a99d8781ff55e1de))

- Add drf-spectacular as optional dev dependency - Annotate all views with @extend_schema for
  summaries, descriptions, and response types - Annotate serializer method fields (count, direction)
  with @extend_schema_field for proper OpenAPI types - Add ErrorSerializer for 4xx response
  documentation - Update test settings with SpectacularAPIView and schema config - Add schema
  validation test ensuring all endpoints are documented

- Add soft delete, cursor pagination, and per-conversation unread
  ([`bbd277e`](https://github.com/garrethcain/drf-directmessages/commit/bbd277e895986dba1820058e334c4f1b252b9de5))

- Add hidden_for_sender/hidden_for_recipient fields to Message model for per-user soft delete via
  DELETE /messages/<id>/ - Add cursor-based pagination (page_size=50) to conversation and message
  list views for production-scale usage - Add GET /conversations/unread/ endpoint returning
  per-conversation unread counts with partner details - Update all service queries to exclude
  soft-deleted messages - Update existing tests for paginated response shape - Add 17 new tests
  covering all three features


## v0.9.9 (2026-05-30)

### Bug Fixes

- **ci**: Checkout release tag instead of branch head in publish job
  ([`3c61f8b`](https://github.com/garrethcain/drf-directmessages/commit/3c61f8b4a34e4fba43642725ac403de14dabc967))


## v0.9.8 (2026-05-30)

### Bug Fixes

- Resolve 5 critical bugs in models, services, and views
  ([`c073ad3`](https://github.com/garrethcain/drf-directmessages/commit/c073ad39faf70862c69c7c0816695fcb52c7dbf6))

- models: change sent_at from auto_now to auto_now_add to prevent timestamp corruption on every save
  (e.g. mark_as_read) - services: only mark messages as read for the requesting user, not all
  participants in the conversation - services: use update_fields=['read_at'] in mark_as_read to
  avoid unnecessary field updates - views: wrap ValidationError in {"detail": str(e)} before passing
  to Response (not JSON-serializable as-is) - views: pass context={'request': request} to
  MessageSerializer so direction field returns correct value - views: replace User.objects.get()
  with get_object_or_404() to return 404 instead of 500 for invalid user pk

- Resolve all remaining bugs across services, views, and serializers
  ([`a0b2714`](https://github.com/garrethcain/drf-directmessages/commit/a0b2714262499d3d367014eeee447df0666421c8))

Significant: - serializers: use isinstance() instead of type() comparison - serializers: rename
  misleading user_id variable to user - views: validate content is present before creating messages
  - views: use Inbox.send_message() instead of direct objects.create() so message_sent signal fires
  consistently Moderate: - services: replace get_conversations() memory-heavy loop with db-level
  values_list query - views: ConversationListView returns proper QuerySet for pagination - services:
  return None instead of "" for not-found to distinguish from empty content - serializers: remove
  email and is_active from ConversationSerializer - views: MessageSendView uses global Inbox,
  returns created message - views: remove unused serializer_class from UnreadMessagesView Minor: -
  services: rename reversed param to reverse_order (avoids shadowing) - services: use if limit is
  not None instead of if limit - urls: add missing trailing slash on conversations/<int:pk> - admin:
  fix import order, remove redundant model attribute - serializers: remove read_only_fields not in
  fields Config: - tests/settings: add ALLOWED_HOSTS and REST_FRAMEWORK defaults - pyproject.toml:
  fix SPDX license identifier to AGPL-3.0-only - release.yml: add test job before release to prevent
  broken releases

### Chores

- Corrected the version
  ([`3898c21`](https://github.com/garrethcain/drf-directmessages/commit/3898c215685f447ef9504971da6e5b4606ff5729))

### Testing

- Add API view tests and edge case coverage
  ([`048950f`](https://github.com/garrethcain/drf-directmessages/commit/048950fd7158b635c07f52fb660d48b36b9dad7b))

Add comprehensive tests for all four API views and edge cases: - UnreadMessagesView: count zero,
  count after message, auth required - ConversationListView: empty list, returns partners, excludes
  self, auth required - MessageListView: get messages, mark inbound read on view, don't mark
  outbound read, post message, empty/missing content returns 400, nonexistent user returns 404,
  direction field in/out - MessageSendView: send success, empty content 400, send to self 400,
  nonexistent user 404, auth required - Service layer: send to self raises, nonexistent message
  returns None - Fix variable shadowing in existing formatted message test


## v0.0.1 (2026-05-30)

### Bug Fixes

- Corrected the branch name
  ([`b90434f`](https://github.com/garrethcain/drf-directmessages/commit/b90434fc5faff0531d6c086efebb22cf62085ec4))

- Updated, fixed and modernised
  ([`65a9fc7`](https://github.com/garrethcain/drf-directmessages/commit/65a9fc751f490de817ead7a46ab8bd4f7013ba0a))

- **ci**: Separate PSR from build/publish and fix version config
  ([`d3fa6a8`](https://github.com/garrethcain/drf-directmessages/commit/d3fa6a8ccc32b1d97a2a3c848017bc5957291e63))
