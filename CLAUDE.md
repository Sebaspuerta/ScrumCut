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

- Prohibido: fuente Inter (y Geist, Space Grotesk), degradados violetas, glassmorphism, tarjetas dentro de tarjetas, emojis como íconos, el rojo-azul-blanco del poste de barbería.
- Base negro y hueso con un solo acento metálico; el color de la barbería solo como acento.
- Títulos en serif con carácter (Fraunces o Cormorant), texto en IBM Plex Sans, cifras tabulares.
- Superficies planas separadas por líneas finas; radio único de 4 px; tablas densas para gerencia.
- Todo estado de pantalla diseñado: vacío, cargando, error.

## Frontend

- Django genera las vistas; todo lo visual vive en frontend/. Nada de HTML, CSS o JS dentro de backend/.
- HTML: plantillas de Django con partials ({% partialdef %}), una subcarpeta por módulo en frontend/templates/.
- Interacción con el servidor: HTMX. Interacción en pantalla: Alpine.js en su versión CSP (@alpinejs/csp).
- JavaScript propio: vanilla, ES modules, sin compilación, en frontend/static/js/ con core/, components/ y modules/.
- CSS propio con variables de diseño (tokens.css, base.css, components/, modules/). Sin Bootstrap ni Tailwind.
- Gráficas: Chart.js. Íconos: Lucide. Librerías de terceros descargadas en frontend/static/vendor/ con su licencia; sin CDN.
- Nada de <script> dentro de las plantillas ni atributos onclick: todo el JS en archivos .js (compatible con CSP estricta).

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

- Nunca ejecutar `git commit`, `git push`, `git tag` ni nada que cree o suba historial. Tampoco `git add`.
- No agregar "Co-Authored-By", "Generated with Claude" ni ninguna mención a Claude o IA en archivos, comentarios, mensajes o documentación.
- Al terminar cada tarea, entregar solo la lista de archivos cambiados y un mensaje de commit sugerido en español, sin atribuciones. El commit y el push los hace una persona.
