"""Autenticación de allauth sin el atajo de las cuentas inactivas (hallazgo S4 de docs/arquitectura.md)."""

from allauth.account.auth_backends import AuthenticationBackend


class ActiveOnlyAuthenticationBackend(AuthenticationBackend):
    """Una cuenta inactiva nunca se autentica, ni para avisarle que lo está.

    allauth guarda la cuenta inactiva cuya contraseña es correcta para llevarla a /cuenta/inactive/, y esa
    pantalla revela que la cuenta existe. Aquí la contraseña se revisa igual (el tiempo de respuesta no la
    delata) y el intento falla como cualquier otro: mismo mensaje y cuenta para axes y el límite de allauth.
    """

    def _check_password(self, user, password: str):
        if user is not None and not self.user_can_authenticate(user):
            self._did_check_password = True  # allauth no repite el cálculo para "mitigar" el tiempo
            user.check_password(password)
            return None
        return super()._check_password(user, password)
