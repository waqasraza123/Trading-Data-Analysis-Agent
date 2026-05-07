package safety

import (
	"net/url"
	"strings"
)

func RedactDatabaseURL(value string) string {
	if value == "" {
		return ""
	}
	parsed, err := url.Parse(value)
	if err != nil {
		return "<redacted>"
	}
	if parsed.User != nil {
		username := parsed.User.Username()
		if username == "" {
			parsed.User = url.UserPassword("<redacted>", "<redacted>")
		} else {
			parsed.User = url.UserPassword(username, "<redacted>")
		}
	}
	return parsed.String()
}

func MetadataContainsSecret(value any) bool {
	switch typed := value.(type) {
	case map[string]any:
		for key, nested := range typed {
			if KeyContainsSecret(key) || MetadataContainsSecret(nested) {
				return true
			}
		}
	case []any:
		for _, nested := range typed {
			if MetadataContainsSecret(nested) {
				return true
			}
		}
	}
	return false
}

func KeyContainsSecret(key string) bool {
	normalized := strings.NewReplacer("-", "_", " ", "_").Replace(strings.ToLower(key))
	secretKeys := []string{"api_key", "apikey", "authorization", "auth", "bearer", "password", "secret", "token"}
	for _, secretKey := range secretKeys {
		if strings.Contains(normalized, secretKey) {
			return true
		}
	}
	return false
}
