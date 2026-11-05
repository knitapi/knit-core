from .mock_utils import NOT_MOCK


def email(context, to, subject, html_content, attachment=None):
    """Send an email. Mock mode returns context["mock_io"]["knit_mail"] if set, else {"status": "mocked", ...}."""
    if context and context.get("mock_mode"):
        fixture = (context.get("mock_io") or {}).get("knit_mail")
        return fixture if fixture is not None else {"status": "mocked", "to": to, "subject": subject}
    raise RuntimeError(NOT_MOCK)
