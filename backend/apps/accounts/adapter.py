"""Adaptadores de allauth: registro cerrado sin textos legales y los mensajes de la entrada, tuteando."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.mfa.adapter import DefaultMFAAdapter
from django.http import HttpRequest

from apps.legal.selectors import missing_signup_documents

# Un solo mensaje para el bloqueo por intentos (axes y allauth): no dice si la cuenta existe ni si está
# inactiva (hallazgo S4 de docs/arquitectura.md).
LOCKOUT_MESSAGE = (
    "Por seguridad pausamos el ingreso desde este equipo por unos minutos. "
    "Intenta de nuevo más tarde o recupera tu contraseña."
)
WRONG_CREDENTIALS = "El correo o la contraseña no son correctos."
INCORRECT_CODE = "El código no es correcto."


class AccountAdapter(DefaultAccountAdapter):
    error_messages = {
        **DefaultAccountAdapter.error_messages,
        # Nunca se muestra (ActiveOnlyAuthenticationBackend), pero si algo lo pidiera, diría lo mismo.
        "account_inactive": WRONG_CREDENTIALS,
        "cannot_remove_primary_email": "No puedes quitar tu correo principal.",
        "duplicate_email": "Este correo ya está asociado a tu cuenta.",
        "email_password_mismatch": WRONG_CREDENTIALS,
        "email_taken": "Ya hay una cuenta registrada con este correo.",
        "enter_current_password": "Escribe tu contraseña actual.",
        "incorrect_code": INCORRECT_CODE,
        "incorrect_password": "La contraseña no es correcta.",
        "invalid_or_expired_key": "El enlace no es válido o ya venció.",
        "invalid_login": WRONG_CREDENTIALS,
        "invalid_password_reset": "El enlace para restablecer la contraseña no es válido.",
        "max_email_addresses": "No puedes agregar más de %d correos.",
        "too_many_login_attempts": LOCKOUT_MESSAGE,
        "unknown_email": "Este correo no está asociado a ninguna cuenta.",
        "unverified_primary_email": "Tu correo principal debe estar verificado.",
    }

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """Sin términos, política de datos y aviso de privacidad publicados no se recolectan datos."""
        return not missing_signup_documents()


class MFAAdapter(DefaultMFAAdapter):
    error_messages = {
        **DefaultMFAAdapter.error_messages,
        "add_email_blocked": "No puedes agregar un correo a una cuenta protegida con verificación en dos pasos.",
        "cannot_delete_authenticator": "No puedes desactivar la verificación en dos pasos.",
        "cannot_generate_recovery_codes": (
            "Activa la verificación en dos pasos antes de generar códigos de recuperación."
        ),
        "incorrect_code": INCORRECT_CODE,
        "unverified_email": "Verifica tu correo antes de activar la verificación en dos pasos.",
    }
