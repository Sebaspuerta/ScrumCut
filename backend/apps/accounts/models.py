from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.crypto import salted_hmac


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email: str, password: str | None, **extra) -> "User":
        if not email:
            raise ValueError("El correo es obligatorio.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra) -> "User":
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email: str, password: str, **extra) -> "User":
        extra.update(is_staff=True, is_superuser=True, is_platform_staff=True)
        return self._create(email, password, **extra)


class Theme(models.TextChoices):
    """Tema de la interfaz. "system" sigue la preferencia del sistema operativo (prefers-color-scheme)."""

    SYSTEM = "system", "Sistema"
    LIGHT = "light", "Claro"
    DARK = "dark", "Oscuro"


class User(AbstractBaseUser, PermissionsMixin):
    """Una persona. Su rol no vive aquí sino en cada membresía con una barbería."""

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text="Acceso al admin de Django.")
    is_platform_staff = models.BooleanField(default=False, help_text="Equipo ScrumTech (superadmin).")
    date_joined = models.DateTimeField(default=timezone.now)
    session_version = models.PositiveIntegerField(default=0, editable=False)
    # Se guarda en el servidor y no en el navegador: la página llega ya con el tema, sin parpadeo.
    theme = models.CharField("tema", max_length=6, choices=Theme.choices, default=Theme.SYSTEM)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(theme__in=Theme.values), name="ck_user_theme_valid")]

    def __str__(self) -> str:
        return self.email

    def _get_session_auth_hash(self, secret=None) -> str:
        # Django guarda este hash en cada sesión y lo compara en cada petición: con la
        # versión dentro, subirla invalida a la vez todas las sesiones abiertas del usuario.
        key_salt = "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash"
        payload = f"{self.password}:{self.session_version}"
        return salted_hmac(key_salt, payload, secret=secret, algorithm="sha256").hexdigest()
