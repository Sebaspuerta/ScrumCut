# ScrumCut — reglas del repositorio

ScrumCut by ScrumTech: SaaS de gestión para barberías, multi-barbería, 100 % web.
Arquitectura completa: ver `docs/arquitectura.md`.

## Reglas no negociables

1. MAGNUS v1 (../MAGNUS-PROJECTO) es la base funcional de ScrumCut. Su lógica de negocio se porta a Django módulo por módulo, adaptada a multi-barbería (TenantScopedModel) y a la estructura services/selectors. Nunca se copian: la marca Magnus (nombre, logos, colores, eslogan, créditos AvanzaTech), el código maestro de recuperación, tokens en localStorage, usuarios fijos por nombre (mateo/admin), el frontend HTML/JS de MAGNUS, ni ningún patrón de los hallazgos de seguridad listados en docs/arquitectura.md.
2. **Marca neutra.** Ningún nombre, logo o color de una barbería en el código. La identidad de cada barbería es dato en `tenancy.Barbershop`.
3. **Toda tabla de negocio hereda de `TenantScopedModel`** y su migración termina con `EnableTenantRLS("<tabla>")`. Nunca se filtra por barbería a mano en una vista.
4. **`Model.unscoped`** solo en tareas de plataforma, con comentario que explique por qué.
5. **Autorización en el servidor:** `require_permission("modulo.accion")` en cada vista + filtro por dueño del objeto en los selectores (el barbero ve solo lo suyo). La matriz vive en `backend/apps/tenancy/roles.py`.
6. **Capas:** vistas delgadas → `services.py` (escrituras, `transaction.atomic`, `select_for_update` cuando se toca stock o caja) → `selectors.py` (lecturas).
7. **Dinero:** `DecimalField(max_digits=14, decimal_places=2)`. Nunca `float`.
8. **Fechas:** siempre con zona horaria (`timezone.now()`); nunca `datetime.utcnow()`.
9. **Movimientos de caja, inventario, auditoría y aceptaciones legales son solo-agregar.** Catálogo, personal y clientes usan `SoftDeleteModel`.
10. **Al cerrar una comanda se copian** precio, costo y comisión al ítem.
11. **Secretos:** solo por variables de entorno vía `config.env.require`. Prohibido poner valores por defecto a un secreto.
12. **Errores:** mensaje genérico al usuario; nunca `str(e)` en una respuesta.
13. **Cookies:** solo esenciales en la app (sesión, CSRF, idioma). Sin rastreadores de terceros.

## Diseño de interfaz

- Ningún diseño se inventa. Pantallas, colores, tipografía, espaciado, íconos y componentes visuales solo se implementan cuando Sebastián los aprueba. Si falta una definición, se pregunta antes de escribir HTML o CSS; no se rellena con valores supuestos.
- Prohibido: fuente Inter (y Geist, Space Grotesk), degradados violeta, glassmorphism, tarjetas dentro de tarjetas, emojis como íconos, el rojo-azul-blanco del poste de barbería y cualquier diseño genérico de IA.
- Las fuentes tipográficas y los recursos de diseño los entrega Sebastián. Los archivos que hoy están en frontend/static/fonts/ no son una elección aprobada: no se usan hasta que él lo indique.
- Toda pantalla contempla sus estados vacío, cargando y error; su aspecto también requiere aprobación.
- La identidad de cada barbería (nombre, logo, color) es dato de tenancy.Barbershop, nunca fija en el código.

## Frontend

- Django genera las vistas; todo lo visual vive en frontend/. Nada de HTML, CSS o JS dentro de backend/.
- HTML: plantillas de Django con partials ({% partialdef %}), una subcarpeta por módulo en frontend/templates/.
- Interacción con el servidor: HTMX. Interacción en pantalla: Alpine.js en su versión CSP (@alpinejs/csp).
- JavaScript propio: vanilla, ES modules, sin compilación, en frontend/static/js/ con core/, components/ y modules/.
- CSS propio con variables de diseño (tokens.css, base.css, components/, modules/). Sin Bootstrap ni Tailwind.
- Gráficas: Chart.js. Íconos: Lucide. Librerías de terceros descargadas en frontend/static/vendor/ con su licencia; sin CDN.
- Nada de <script> dentro de las plantillas ni atributos onclick: todo el JS en archivos .js (compatible con CSP estricta).

## Seguridad y legal

Aplican a toda vista, formulario, plantilla y endpoint. Complementan las reglas 5, 11, 12 y 13.

Sesión y autenticación
- La sesión vive solo en la cookie HttpOnly/Secure del servidor. Prohibido guardar tokens, ids de sesión o datos de usuario en localStorage, sessionStorage o cookies legibles por JS.
- Cerrar sesión siempre es por POST y borra la sesión en el servidor. Debe existir "cerrar sesión en todos los dispositivos".
- Correo verificado obligatorio; 2FA obligatorio para Dueño, Administrador y equipo de plataforma. No se desactivan ni se saltan en ningún flujo.
- Login, registro, recuperación y confirmación de correo siempre con límite de intentos (allauth + axes). Ningún endpoint de autenticación nuevo sin límite.

Autorización y confianza
- El servidor nunca confía en el navegador: todo permiso se valida con require_permission y todo objeto se filtra por barbería y por dueño. Ocultar un botón no es seguridad.
- Precios, totales, comisiones, roles y barbería activa los calcula el servidor; nunca se toman del formulario.
- Ningún secreto llega al navegador: ni en plantillas, ni en JS, ni en atributos data-. Solo variables de entorno del servidor.

Formularios y entradas
- Todo formulario usa un Form de Django validado en el servidor; la validación del navegador es solo ayuda visual.
- Los formularios públicos (registro, recuperación, contacto, reservas) llevan honeypot y límite por IP contra spam.
- Mensajes de error genéricos (regla 12): nunca revelan si un correo o usuario existe.

Navegador
- Siempre HTTPS en producción, con HSTS. CSP estricta: sin <script> en línea, sin onclick, sin eval, sin CDN.
- Las páginas privadas llevan noindex y no aparecen en el sitemap.

Legal (Colombia, Ley 1581 de 2012)
- Los textos legales viven en apps/legal como documentos versionados: política de tratamiento de datos, aviso de privacidad, términos y condiciones y política de cookies. Toda aceptación queda registrada con su versión.
- Ningún dato personal se recolecta sin la autorización previa del titular, registrada en legal.
- Solo cookies esenciales (regla 13), por eso no hay banner de consentimiento. Cualquier cookie no esencial (analítica, publicidad) exige primero aprobación de Sebastián y un banner que pida consentimiento antes de cargarla.
- Ningún texto legal se redacta como definitivo sin aprobación de Sebastián.

## Antes de pedir revisión

```bash
pre-commit run --all-files
cd backend
pytest
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy --fail-level WARNING
```

Luego: `deslop` y `/slop-check` (anti-slop) sobre el cambio, y veredicto de Thermos antes de fusionar a `main`.
Cambios en permisos, pagos, migraciones o seguridad requieren aprobación humana.

## Git
- Los agentes de código nunca ejecutan git commit, git push, git tag ni nada que cree o suba historial, ni git add.
- Ningún commit, archivo, comentario, mensaje o documento lleva atribución a herramientas de IA (Co-Authored-By, Session, "Generated with" ni similares).
- Al terminar cada tarea se entrega solo la lista de archivos cambiados y un mensaje de commit sugerido en español, sin atribuciones. El commit y el push los hace una persona.
