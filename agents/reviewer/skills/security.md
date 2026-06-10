# Security review skill

Check for these issues — report as CRITICAL if found:

- Hardcoded secrets, API keys, or passwords in source code
- SQL injection: string concatenation in queries instead of parameterized queries
- XSS: unescaped user input rendered as HTML
- Missing authentication/authorization on protected endpoints
- Sensitive data logged or returned in error messages
- Path traversal: unsanitized file paths from user input
