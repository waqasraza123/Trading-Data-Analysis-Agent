package providers

type ProviderError struct {
	Code    string
	Message string
}

func (e ProviderError) Error() string {
	return e.Message
}

func NewProviderError(code string, message string) ProviderError {
	return ProviderError{Code: code, Message: message}
}
