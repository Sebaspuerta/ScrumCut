# ScrumCut — reglas del repositorio

ScrumCut by ScrumTech: SaaS de gestión para barberías, multi-barbería, 100 % web.
Arquitectura completa: ver `docs/arquitectura.md`.

## Principio
Todo el código es de nivel senior: limpio, sin nada de sobra, duradero en el tiempo, seguro y escalable. Ante la duda entre rápido y bien hecho, se hace bien hecho.

- Limpio: nada de código muerto, duplicado ni "por si acaso"; cada cosa tiene un solo lugar.
- Duradero: las reglas del negocio viven en services, selectors y modelos, nunca en vistas, serializers ni React; las críticas se refuerzan además con restricciones en la base de datos. Los nombres explican qué hace el código y los comentarios, solo el porqué.
- Seguro: el servidor decide permisos, sede y montos; nunca se confía en el cliente.
- Escalable: consultas constantes, paginación y nada que se rompa al crecer en barberías, sedes o datos.

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

- La identidad aprobada para la app de React y la entrada es la de la fase R1: docs/diseno/identidad-r1.md, a partir de docs/diseno/figma-make/ (se copia en fidelidad, no su estructura de código). Las pantallas que siguen en plantillas usan docs/diseno.md y sus maquetas en docs/diseno/maquetas/ hasta que pasen a React.
- Ningún diseño se inventa. Pantallas, colores, tipografía, espaciado, íconos y componentes visuales solo se implementan cuando Sebastián los aprueba. Si falta una definición, se pregunta antes de escribir HTML o CSS; no se rellena con valores supuestos.
- Prohibido: fuente Inter (y Geist, Space Grotesk), degradados violeta, glassmorphism, tarjetas dentro de tarjetas, emojis como íconos, el rojo-azul-blanco del poste de barbería y cualquier diseño genérico de IA.
- Fuentes aprobadas: Libre Baskerville y Manrope (identidad R1: app de React y entrada) y Bricolage Grotesque y Hanken Grotesk (pantallas en plantillas hasta su migración). Alojadas: @fontsource en frontend/app y frontend/static/fonts/ en Django; nunca desde Google.
- Toda pantalla contempla sus estados vacío, cargando y error; su aspecto también requiere aprobación.
- La identidad de cada barbería (nombre, logo, color) es dato de tenancy.Barbershop, nunca fija en el código.
- El asistente se muestra sin funcionalidad hasta que el backend esté completo.

## Frontend

La parte interna migra a React + TypeScript (`frontend/app/`, servida en `/app/`) módulo por módulo; login, registro, recuperación y 2FA siguen en Django. Decisión y motivos: `docs/decisiones/frontend-react.md`.

### Reglas de la app de React (no se negocian)

- Toda regla de negocio, permiso y alcance de sede vive en el backend; el frontend solo muestra lo que la API le da.
- La sesión sigue en la cookie HttpOnly del mismo dominio: nada de tokens, ni JWT, ni datos en localStorage o sessionStorage.
- CSRF en toda escritura: la API usa solo `SessionAuthentication`; el token se pide a `/api/v1/csrf/` y vive solo en memoria.
- La CSP estricta se mantiene en producción. Cualquier relajación, solo con DEBUG=True y documentada.
- Migración por módulos: las pantallas en plantillas siguen funcionando hasta que su versión en React las reemplace.
- Los tipos de TypeScript se generan del esquema OpenAPI (`npm run gen:types`), nunca se escriben a mano.
- API en `apps/api`: vistas DRF delgadas, permiso `HasRolePermission` (reutiliza `role_has_permission`), alcance de sede de `request.branch_scope`, errores genéricos. Toda vista nueva declara `required_permission` o tiene su motivo en `tests/security/url_inventory.py`.
- Un solo cliente HTTP (`src/api/client.ts`); el formato COP y de fechas solo en `src/lib/format.ts`, con los casos compartidos con el backend en `format-cases.json`.
- Dependencias con versión exacta, `package-lock.json` versionado e instalación con `npm ci`.

### Estándar del frontend en React

- Componentes funcionales de 150 líneas o menos y funciones de 30 líneas o menos.
- Un componente por archivo.
- Hooks para los datos (`useMe`, `useNavigation`…), con TanStack Query.
- Sin lógica de negocio ni permisos decididos en el cliente.
- Sin estilos en línea: CSS por módulo con los tokens. Un valor que depende de los datos (el alto de una torre 3D) va como variable de CSS por el CSSOM desde un ref, nunca en el atributo style.
- Íconos: lucide-react. Tema claro/oscuro por tokens (`data-theme` y `prefers-color-scheme`), guardado en el servidor.
- Accesible: roles y aria correctos, foco visible y objetivos de 44 px.
- TypeScript strict, sin `any` ni `ts-ignore`. ESLint y Prettier sin errores.

### Pantallas en plantillas (hasta que React las reemplace)

- Django genera las vistas; todo lo visual vive en frontend/. Nada de HTML, CSS o JS dentro de backend/.
- HTML: plantillas de Django con partials ({% partialdef %}), una subcarpeta por módulo en frontend/templates/.
- Interacción con el servidor: HTMX. Interacción en pantalla: JavaScript propio sobre elementos nativos (<details> para menús), sin frameworks.
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

## Estándar de código

- Capas: las vistas solo reciben, validan formato y responden; la lógica de negocio va en services (escriben) y selectors (leen). Los modelos no conocen la presentación.
- Una función hace una cosa. Si pasa de ~30 líneas o necesita un comentario para separar partes, se divide. Un archivo de más de ~400 líneas se divide por responsabilidad.
- Nombres que dicen qué es y para qué, en el idioma del dominio. Sin abreviaturas crípticas ni números mágicos: constantes con nombre.
- Sin código muerto, sin código comentado, sin print, sin TODO sueltos. Los comentarios explican el porqué, nunca repiten el qué.
- Firmas públicas tipadas. Los servicios con más de dos parámetros usan argumentos solo por nombre (*).
- Errores: excepciones específicas. Nunca except Exception silencioso. ValidationError con mensajes claros en español para el usuario.
- Escrituras de varias tablas dentro de transaction.atomic. select_for_update cuando hay concurrencia. Las reglas críticas también como restricción en la base de datos.
- Consultas: sin N+1 (select_related y prefetch_related) y agregaciones en la base de datos, no en Python. assertNumQueries en los selectores del tablero y de los reportes.
- Una regla, una implementación: antes de crear un ayudante, buscar si ya existe. Sin duplicar lógica.
- Sin dependencias nuevas sin aprobación de Sebastián.
- Pruebas: toda regla de negocio y todo defecto corregido tienen su prueba. El nombre de la prueba describe el comportamiento.
- Frontend: módulos ES pequeños sin variables globales, CSS solo con tokens, HTML semántico y accesible, sin estilos ni scripts en línea.
- noqa y nosec solo con su justificación en la misma línea.
- Antes de entregar cualquier tarea: autorrevisión contra esta lista, e informar cualquier excepción con su motivo.

## Antes de pedir revisión

```bash
pre-commit run --all-files
cd backend
pytest
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy --fail-level WARNING
cd ../frontend/app
npm ci
npm run lint && npm run format:check && npm run typecheck && npm run test && npm run build
```

Si cambia la API: regenerar `frontend/app/openapi.json` (`manage.py openapi_schema`) y `npm run gen:types` (ver `tests/api/test_openapi_schema.py`).

Pruebas:
- Nunca correr dos procesos de pytest a la vez contra la misma base de pruebas. Si una corrida pasa a segundo plano, esperar a que termine antes de lanzar otra.

Luego: `deslop` y `/slop-check` (anti-slop) sobre el cambio, y veredicto de Thermos antes de fusionar a `main`.
Cambios en permisos, pagos, migraciones o seguridad requieren aprobación humana.

## Git
- Los agentes de código nunca ejecutan git commit, git push, git tag ni nada que cree o suba historial, ni git add.
- Los agentes no ejecutan comandos de git que cambien el repositorio o el índice (add, rm, commit, restore --staged, push, tag, etc.). Solo lectura: status, diff, log.
- Ningún commit, archivo, comentario, mensaje o documento lleva atribución a herramientas de IA (Co-Authored-By, Session, "Generated with" ni similares).
- Al terminar cada tarea se entrega solo la lista de archivos cambiados y un mensaje de commit sugerido en español, sin atribuciones. El commit y el push los hace una persona.
