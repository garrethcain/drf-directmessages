from django.test import TestCase


class SchemaValidationTestCase(TestCase):
    def test_schema_generates_without_errors(self):
        from drf_spectacular.generators import SchemaGenerator
        from drf_spectacular.validation import validate_schema

        gen = SchemaGenerator()
        schema = gen.get_schema(request=None, public=True)
        validate_schema(schema)

    def test_schema_contains_all_endpoints(self):
        from drf_spectacular.generators import SchemaGenerator

        gen = SchemaGenerator()
        schema = gen.get_schema(request=None, public=True)
        paths = schema["paths"]

        expected = [
            "/unread/",
            "/conversations/",
            "/conversations/unread/",
            "/conversations/{id}/",
            "/messages/{id}/",
            "/send/{id}/",
        ]
        for path in expected:
            self.assertIn(path, paths, f"Schema missing path: {path}")
