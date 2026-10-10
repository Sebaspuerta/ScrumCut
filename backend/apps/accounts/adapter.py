from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpRequest

from apps.legal.selectors import missing_signup_documents


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """Sin términos, política de datos y aviso de privacidad publicados no se recolectan datos."""
        return not missing_signup_documents()
