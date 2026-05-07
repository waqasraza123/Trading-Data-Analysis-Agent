package safety

import "testing"

func TestRedactDatabaseURL(t *testing.T) {
	redacted := RedactDatabaseURL("postgresql://user:secret@example.com:5432/db")
	if redacted == "postgresql://user:secret@example.com:5432/db" {
		t.Fatal("expected password to be redacted")
	}
}

func TestMetadataContainsSecret(t *testing.T) {
	if !MetadataContainsSecret(map[string]any{"nested": map[string]any{"api_key": "secret"}}) {
		t.Fatal("expected secret metadata detection")
	}
}
