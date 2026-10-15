# Sedes

Especificación del soporte multi-sede de ScrumCut. Cada elemento lleva su estado frente al código actual:

- **YA EXISTE**: está en el código y no cambia.
- **CAMBIA**: existe, pero hay que modificarlo.
- **NUEVO**: no existe.

El módulo de reseñas (enlace de Google y QR) no está aquí: se especifica en `docs/resenas.md`.

## Principio

La barbería (`tenancy.Barbershop`) es la frontera de seguridad, protegida por RLS sobre `barbershop_id` (`EnableTenantRLS`, `apps/core/rls.py`).

La sede (`tenancy.Branch`) es una división operativa dentro de la barbería. La controlan los servicios, los selectores y los permisos. **No se hace RLS por sede.**

## Decisiones de partida

| Decisión | Estado |
|---|---|
| Inventario con existencias por sede y traslados entre sedes | NUEVO (S4b). Hoy el stock es por barbería: `inventory.Product.current_stock`. |
| Precio de servicio opcional por sede; si no hay, rige `catalog.Service.price` | NUEVO (S4a) |
| La comisión es del barbero (`staff.CommissionRule`) y no cambia según la sede | YA EXISTE. `CommissionRule` no tiene sede. |
| Al iniciar sesión, el usuario entra a la última sede que usó, si sigue siendo válida | NUEVO (S2) |
| Límite de sedes según el plan: `Barbershop.max_branches`, por defecto 1 | NUEVO (S1). No existe ninguna noción de plan. |
| Clientes (`clients.Client`), servicios (`catalog.Service`) y productos (`inventory.Product`) son compartidos en la barbería | YA EXISTE. Ninguno tiene sede. |
| Los fiados son del cliente, pero guardan la sede donde se originaron | CAMBIA (S1). Ver la decisión 3. |

## Datos

### Sede: `tenancy.Branch` (CAMBIA)

| Campo | Estado | Detalle |
|---|---|---|
| `barbershop` | YA EXISTE | Heredado de `TenantScopedModel`. |
| `name` | YA EXISTE | Único por barbería: `uq_branch_name_per_barbershop (barbershop_id, name)`. |
| `address`, `phone` | YA EXISTE | Opcionales (`blank=True`). |
| `city` | NUEVO | Opcional. |
| `is_active` | YA EXISTE | |
| `created_at`, `updated_at`, `public_id` | YA EXISTE | Heredados de `TimeStampedModel`. |
| Único `(barbershop_id, id)` | NUEVO | Destino de las llaves compuestas. |

- La sede **no** lleva zona horaria: se aplazó (decisión 7 y "Trabajo futuro").
- El enlace de reseñas y el código del QR **no** van en la sede: viven en `apps/reviews` (`docs/resenas.md`).

**Sede principal.** Al crear una barbería, `Barbershop.save` crea su "Sede principal" en la misma transacción que `BarbershopSettings` (decisión 12; CAMBIA). En las migraciones de datos, "la Sede principal" de una barbería es:
- la que la migración crea, si la barbería no tenía ninguna;
- si ya tenía, la sede más antigua (menor `id`). Confirmado.

### Tablas nuevas

Todas heredan de `TenantScopedModel`, terminan con `EnableTenantRLS` y llevan la llave compuesta hacia la sede.

| Modelo | App | Campos | Restricciones | Fase |
|---|---|---|---|---|
| `BranchHours` (horario) | tenancy | sede, día de la semana (0–6), abre, cierra, cerrado | Único `(branch, weekday)`. CHECK `closed OR opens_at < closes_at`. | S1 |
| `MembershipBranch` (acceso del Cajero a sedes) | tenancy | membresía, sede | Único `(membership, branch)`. Solo para el rol Cajero (decisión 1). | S1 |
| `BarberBranch` (barbero ↔ sede) | staff | barbero, sede | Único `(barber, branch)`. Reemplaza a `Barber.branch` (decisión 2). | S1 |
| `ServiceBranchPrice` (precio por sede) | catalog | servicio, sede, precio (`DecimalField(14, 2)`) | Único `(service, branch)`. CHECK `price >= 0`. | S4a |
| `StockLevel` (existencias por sede) | inventory | producto, sede, cantidad | Único `(product, branch)`. CHECK `quantity >= 0`. | S4b |
| `StockTransfer` (traslado) | inventory | producto, sede origen, sede destino, cantidad, motivo, quién | CHECK `quantity > 0` y `origin <> destination`. Solo-agregar (regla 9); sus dos `StockMovement` lo respaldan. | S4b |

### Campos nuevos o que cambian en tablas existentes

| Elemento | Estado | Detalle | Fase |
|---|---|---|---|
| `Membership.last_branch` (última sede usada) | NUEVO | Nullable. `Membership` no tiene RLS a propósito (`WITHOUT_RLS` en `tests/security/test_rls_coverage.py`). | S1 |
| `Barbershop.max_branches` (límite del plan) | NUEVO | Por defecto 1. La migración pone a las existentes `max(1, número de sedes)`. `Barbershop` no tiene RLS. | S1 |
| `staff.Barber.branch` | CAMBIA | Se elimina y pasa a `BarberBranch` (decisión 2). | S1 |
| `receivables.Receivable.origin_branch` | NUEVO | Obligatoria (decisión 3). | S1 |
| `inventory.StockMovement.branch` | NUEVO | Obligatoria. `stock_before` y `stock_after` pasan a ser los de la sede. | S4b |
| `inventory.Product.current_stock` | CAMBIA | Se elimina. El total se calcula sumando `StockLevel`. `minimum_stock` sigue por producto (decisión 6). | S4b |
| `alerts.Alert.branch` | NUEVO | Opcional (decisión 6). | S4b |
| `audit.AuditLog.branch` | NUEVO | Opcional. | S1 |

### Sede de cada modelo

| Modelo | Sede hoy | Especificación |
|---|---|---|
| `sales.Order` (comandas y ventas) | `branch` NOT NULL | YA EXISTE. Faltan la llave compuesta y el índice. |
| `sales.OrderItem`, `sales.Payment` | Por la comanda | YA EXISTE (por `order.branch`). |
| `cash.CashSession` | `branch` NOT NULL | YA EXISTE. Faltan la llave compuesta y el índice. |
| `cash.CashMovement` (incluye gastos: `kind="gasto"`) | Por `session.branch` | YA EXISTE. No lleva sede propia: la hereda de su sesión (decisiones 4 y 5). |
| `receivables.Receivable` | No tiene | NUEVO `origin_branch`, obligatoria. |
| `receivables.ReceivablePayment` | Por `cash_movement.session.branch` | YA EXISTE. No lleva sede propia: la hereda de la sesión de caja de su movimiento, que es obligatorio (decisión 3). |
| `staff.Barber` | `branch` FK opcional, una sola | CAMBIA a `BarberBranch`. |
| `inventory.StockLevel`, `inventory.StockTransfer` (origen y destino) | No existen | NUEVO, obligatoria. |
| `inventory.StockMovement` | No tiene | NUEVO `branch`, obligatoria. |
| Citas | La app no existe (fase 3) | NUEVO cuando llegue la agenda, obligatoria. |
| `audit.AuditLog`, `alerts.Alert` | No tiene | NUEVO `branch`, opcional. |

## Integridad en la base de datos

| Regla | Estado | Detalle |
|---|---|---|
| RLS con FORCE (`EnableTenantRLS`) en toda tabla nueva | NUEVO | Cada tabla nueva aparece sola en `TENANT_TABLES` de `tests/security/test_rls_coverage.py`. |
| Llave compuesta | NUEVO | Ver el detalle debajo de esta tabla. |
| Una sola caja abierta por sede | YA EXISTE | `uq_cashsession_one_open_per_branch`: único `(barbershop_id, branch_id) WHERE closed_at IS NULL` (`apps/cash/models.py`). |
| Índice (barbería, sede, fecha) en ventas | NUEVO (S1) | `sales_order (barbershop_id, branch_id, closed_at)`. Hoy existen `(barbershop_id, status, closed_at)` y `(branch_id)` sueltos. |
| Índice (barbería, sede, fecha) en caja | NUEVO (S1) | En `cash_cashsession (barbershop_id, branch_id, opened_at)`, no en los movimientos: estos se filtran por su sesión (decisión 4). Hoy los movimientos tienen `(session_id, payment_method)`. |
| Índice (barbería, sede, fecha) en movimientos de inventario | NUEVO (S4b) | `inventory_stockmovement (barbershop_id, branch_id, created_at)`. Hoy existe `(product_id, created_at)`. |
| Migración de datos sin sede | NUEVO | Ver el detalle debajo de esta tabla. |

**Llave compuesta**
- Único `(barbershop_id, id)` en `tenancy_branch`.
- En cada columna de sede, `FOREIGN KEY (barbershop_id, <columna>_id) REFERENCES tenancy_branch (barbershop_id, id)`, con `RunSQL` reversible y `DEFERRABLE INITIALLY DEFERRED`, como las FK de Django.
- Motivo: PostgreSQL no aplica RLS a las llaves foráneas. Sin esta llave, una fila podría apuntar a la sede de otra barbería; hoy solo la frena el manager (`TenantManager`).
- En las columnas opcionales (`Alert.branch`, `AuditLog.branch`), una sede nula pasa (MATCH SIMPLE).
- La misma llave protege `MembershipBranch.membership` → `tenancy_membership` y `BarberBranch.barber` → `staff_barber`, con su único `(barbershop_id, id)`. La operación es `TenantKey` (`apps/core/tenant_keys.py`).

**Migración de datos sin sede.** Tres pasos, reversibles:
1. Crear la "Sede principal" en cada barbería que no tenga ninguna.
2. Asignar los registros:
   - S1: `Receivable.origin_branch` sale de `order.branch`, o de la Sede principal si el fiado es manual.
   - S1: `BarberBranch` (decisión 2).
   - S4b: `StockMovement.branch` y `StockLevel` en la Sede principal, con el `current_stock` de hoy.
3. Volver las columnas obligatorias NOT NULL.

## Alcance por petición (S2, solo backend)

| Elemento | Estado | Detalle |
|---|---|---|
| `request.branch_scope` | NUEVO | Objeto inmutable (`dataclass(frozen=True)`). Lleva el modo (`"una"` o `"todas"`), la sede activa y los ids de las sedes permitidas. |
| Sedes permitidas por rol | NUEVO | Ver "Sedes permitidas por rol", debajo de esta tabla. |
| Middleware de sede | NUEVO | Va después de `ActiveBarbershopMiddleware` (`apps/tenancy/middleware.py`), así que ya corre dentro de `tenant_context`. En cada petición lee la sede de la sesión y la valida contra las permitidas. Si no es válida: (1) con una sola sede permitida, esa; (2) si no, `Membership.last_branch` si es válida; (3) si no, "todas" para quien tiene `sedes.ver`; (4) si no, la primera sede permitida. |
| Sedes inactivas | CAMBIA | No aparecen en el alcance, pero su historial sigue en los reportes. |
| Cambiar de sede | NUEVO | POST con CSRF. Valida la sede, la guarda en la sesión y en `Membership.last_branch`, y vuelve a la página anterior validando la URL con `url_has_allowed_host_and_scheme`. En S2 es solo el endpoint; el selector visual llega en S3 (decisión 9). |
| Selectores y servicios reciben el alcance | CAMBIA | Hoy reciben un `Branch` o el `public_id` de una sede. Nunca leen `request`. |
| Un único ayudante de filtro | NUEVO | `apps/tenancy/branch_scope.py`, con `BranchScope` y `BranchScope.apply(queryset, lookup="branch")`. Reemplaza `_in_branch` (`apps/reports/selectors/cash.py`) y el filtro de `closed_orders` (`apps/reports/scope.py`). `reports.scope.Period.branch` pasa a llevar el `BranchScope`. Va en tenancy y no en reports porque caja, comandas e inventario también lo usan (decisión 10). |
| Tablero y Excel | CAMBIA | Ver "Tablero y Excel", debajo de esta tabla. |
| Escribir exige modo "una" | NUEVO | El servicio rechaza escrituras en modo "todas". |
| Pestañas cruzadas | NUEVO | Todo formulario que escribe lleva oculta la sede con la que se abrió. Si no coincide con la sede activa, el servidor rechaza el envío con el mensaje "Cambiaste de sede en otra pestaña; revisa antes de guardar". |
| "Hoy" y los períodos | YA EXISTE | Siguen con `Barbershop.timezone` (decisión 7). |
| Claves de caché con la sede | YA EXISTE (no aplica) | Hoy no hay caché de datos; si se agrega, la clave lleva la sede. |

**Sedes permitidas por rol** (decisión 1)

| Rol | Sedes permitidas |
|---|---|
| Dueño, Administrador, Consultor | Todas las activas |
| Cajero | Las de su `MembershipBranch` |
| Barbero | Las de su `Barber` en `BarberBranch`, vía `Barber.membership` |

**Tablero y Excel** (decisión 10)
- `?sede=` desaparece de `apps/reports/forms.py`, `apps/reports/views.py` y `frontend/templates/dashboard/sections.html`. El tablero y el Excel usan `request.branch_scope`.
- En modo "todas", los indicadores suman las sedes permitidas. El comparativo por sede llega en S5.

## Permisos (S1)

En el formato de `MODULE_ACTIONS` (`apps/tenancy/roles.py`):

```python
"sedes": ("ver", "gestionar"),
```

| Permiso | Roles | Estado |
|---|---|---|
| `sedes.ver` (ver todas las sedes y el consolidado) | Dueño, Administrador, Consultor | NUEVO |
| `sedes.gestionar` (crear, editar, desactivar, reactivar y asignar personal) | Dueño, Administrador | NUEVO |
| Cajero y Barbero: solo sus sedes permitidas | Cajero, Barbero | NUEVO. Hoy ningún permiso ni selector mira la sede. |

`sedes.ver` cumple `tests/test_roles.py::test_el_consultor_solo_lee`, que exige que todo permiso del Consultor termine en `.ver`.

## Reglas de negocio

| Regla | Estado | Fase |
|---|---|---|
| No se crean ni reactivan sedes por encima de `Barbershop.max_branches`. Lo aplica solo el servicio de crear o reactivar sedes y cuenta solo las sedes activas: desactivar una libera cupo. | NUEVO | S1 |
| Al crear una barbería se crea su "Sede principal" en la misma transacción | CAMBIA (`Barbershop.save`) | S1 |
| Las sedes se desactivan (`is_active=False`), no se borran | CAMBIA. El campo existe; falta el servicio. | S1 |
| No se desactiva una sede con caja abierta ni si es la única activa | NUEVO | S1 |
| No se desactiva una sede con citas futuras | PENDIENTE: se activa cuando exista la agenda (fase 3 de `docs/arquitectura.md`) | Fase 3 |
| `receivables.add_payment` y `cash.selectors.current_session` exigen una sede activa | CAMBIA (defecto: hoy no filtran `is_active`) | S1 |
| Un barbero sin sedes no se puede elegir en comandas | NUEVO (`sales.services._active_barber`) | S1 |
| Barbero nuevo: con una sola sede activa queda en ella; con varias, `create_barber` exige sus sedes (`ValidationError` si no vienen) | NUEVO | S1 |
| El fiado manual toma como `origin_branch` la sede activa al crearlo; el de una comanda, `order.branch` | NUEVO | S1 |
| La sede del abono es la de la caja donde entra (`cash_movement.session.branch`), que puede ser distinta de `origin_branch`. Los selectores de abonos por sede filtran por esa sesión. | NUEVO | S1 |
| El consumo de inventario al cerrar una comanda descuenta de `StockLevel` de `order.branch` | CAMBIA (`sales.services.close_order`) | S4b |
| Traslado de inventario | NUEVO. Atómico, con `select_for_update` sobre los dos `StockLevel` (en orden fijo por id, para evitar bloqueos cruzados). Exige cantidad > 0 y origen ≠ destino, y no deja el origen en negativo. | S4b |
| Alertas de producto (agotado, stock bajo y por vencer) por (tipo, producto, sede) | CAMBIA. Hoy `uq_alert_open_per_product` es por (tipo, producto). Agotado y stock bajo comparan el `StockLevel` de la sede con `Product.minimum_stock`. Por vencer solo se genera en las sedes donde la existencia es > 0. | S4b |
| Auditoría | NUEVO. Se auditan: creación, edición, desactivación y reactivación de sedes; cambios de acceso de cajeros y barberos; traslados; cambios de precio por sede. Hoy `staff.update_barber` ya audita el cambio de `Barber.branch`. | S1, S4a, S4b |

## Frontend

| Elemento | Estado | Fase |
|---|---|---|
| Selector de sede en la barra superior: con una sola sede, solo texto; con varias, un `<details>` con las sedes permitidas y "Todas las sedes" si aplica, donde cada opción es un botón de un formulario POST | NUEVO, se diseña y aprueba con S3 (decisión 9) | S3 |
| Modo "todas" en el encabezado ("CONSOLIDADO · N SEDES") | NUEVO, se diseña y aprueba con S3 | S3 |
| Filtro "Sede" del tablero (`?sede=`) | Se elimina (decisión 10) | S2 |
| Comparativo de sedes y cuadre de caja por sede en el tablero | NUEVO, requiere maqueta aprobada | S5 |
| Caja, Comandas y Agenda en modo "todas" piden elegir una sede | NUEVO. Hoy esas pantallas no existen. | Con cada pantalla |
| Ajustes → Sedes: lista, crear, editar, horario, personal asignado y desactivar con página de confirmación. La sección "Reseñas de Google" la agrega el módulo de reseñas. | NUEVO, requiere maqueta aprobada | S3 |

## Pruebas obligatorias

- Un cajero de la sede A no ve ni escribe en la sede B por ninguna URL, ni con la sesión alterada, ni con el formulario alterado.
- El barbero solo opera en las sedes de su `BarberBranch`; uno sin sedes no se puede elegir en comandas.
- La base rechaza una sede de otra barbería (llave compuesta). La prueba corre con un superusuario, que no está sujeto a RLS, para que el rechazo solo pueda venir de la llave.
- Una sola caja abierta por sede. Ya existe la restricción; falta probarla también con la llave compuesta.
- Al crear una barbería existe su "Sede principal"; si falla la creación, no queda ni la barbería ni la sede.
- `max_branches` impide crear y reactivar sedes por encima del límite; desactivar una sede libera cupo.
- `add_payment` y `current_session` rechazan una sede inactiva.
- El selector de abonos por sede obtiene la sede por `cash_movement.session.branch`: un abono de un fiado de la sede A cobrado en la caja de la sede B aparece en B.
- El consolidado (modo "todas") es igual a la suma de las sedes.
- El rechazo por pestañas cruzadas.
- Traslados: atomicidad, concurrencia y no negativos.
- Las migraciones funcionan con datos existentes y son reversibles. Esto incluye: barberos con sede nula asignados a todas las activas, `origin_branch` de fiados con y sin comanda, `max_branches` y la eliminación de `current_stock`.
- Las tablas nuevas tienen RLS con FORCE: se prueba con un rol sin privilegios (`tests/rls_support.py`) y aparecen en `tests/security/test_rls_coverage.py`.

## Fases

| Fase | Contenido | Ya hecho | Tamaño |
|---|---|---|---|
| S1 | Modelo de datos. Ver el detalle debajo de esta tabla. | `Branch` con nombre único, dirección, teléfono y activa. Sede obligatoria en `Order` y `CashSession`. Una caja abierta por sede. RLS en `tenancy_branch`. Los servicios de caja, comandas, abonos y personal ya reciben una sede. | Grande |
| S2 | Solo backend: `request.branch_scope`, middleware, cambio de sede por POST y selectores con alcance. Tablero y Excel con el alcance, sin `?sede=`, con el ayudante único de filtro y los indicadores sumados en modo "todas" (decisión 10). | El tablero y el Excel ya filtran por una sede; los selectores de `apps/reports` y el Excel ya aceptan `branch=None` (todas). | Grande |
| S3 | Ajustes → Sedes, selector de sede en la barra superior y modo "todas" en el encabezado (requiere maqueta aprobada). Va inmediatamente después de S2. | Nada | Grande |
| S4a | Caja, comandas, gastos y precios por sede (`ServiceBranchPrice`). Escritura solo en modo "una" y rechazo por pestañas cruzadas. | Caja y comandas ya operan por sede. Los gastos ya van por `CashMovement` dentro de la sesión de la sede. | Mediana |
| S4b | Inventario por sede (decisión 6): `StockLevel`, `StockMovement.branch`, consumo por `order.branch`, alertas con `Alert.branch`, sin `Product.current_stock`, y traslados. | Nada: stock, movimientos y alertas son por barbería. | Grande |
| S5 | Comparativo por sede y cuadre de caja por sede en el tablero (requiere maqueta aprobada). | Los indicadores del modo "todas" llegan en S2. | Mediana |

**Detalle de S1**
- `Branch.city` y el único `(barbershop_id, id)`; `BranchHours`.
- Llaves compuestas e índices de `Order` y `CashSession`.
- Acceso por rol con `MembershipBranch` y `BarberBranch` (decisiones 1 y 2).
- `Receivable.origin_branch` (decisión 3).
- `Barbershop.max_branches` (decisión 8).
- Permisos `sedes.ver` y `sedes.gestionar` (decisión 11).
- "Sede principal" al crear la barbería (decisión 12).
- Sede activa obligatoria en `add_payment` y `current_session` (decisión 14).
- `Membership.last_branch` y `AuditLog.branch`.
- Servicio de crear, editar, desactivar y reactivar sedes.
- `cargar_demo` con 2 sedes (Centro y Norte) y `max_branches = 3`.

## Decisiones tomadas

Resuelven los conflictos que dejó el diagnóstico.

1. **Una sola fuente de acceso por rol.**
   - Decisión: el Cajero accede por `MembershipBranch`; el Barbero, por las sedes de su `Barber` en `BarberBranch`, a través de `Barber.membership`; Dueño, Administrador y Consultor, a todas por su rol.
   - Motivo: dos tablas de acceso para el mismo rol podían contradecirse. El Barbero ya tiene sedes por su trabajo, y duplicarlas en la membresía no agrega nada.
2. **`Barber.branch` pasa a `BarberBranch` (muchos a muchos).**
   - Decisión: en la migración, un barbero con sede nula queda asignado a todas las sedes activas de su barbería. Después, un barbero sin sedes no se puede elegir en comandas. Un barbero nuevo queda en la única sede activa; si hay varias, se indican al crearlo.
   - Motivo: hoy la sede nula equivale en la práctica a "trabaja en cualquiera"; asignarle todas conserva ese comportamiento sin dejar un caso especial en el código.
3. **Sede de origen del fiado y sede del abono.**
   - Decisión: `Receivable.origin_branch` es la sede de la comanda o, si el fiado es manual, la sede activa al crearlo. `ReceivablePayment` no lleva sede propia: la del abono es `cash_movement.session.branch`, la caja donde entró el dinero, que puede ser otra.
   - Datos existentes: `origin_branch` desde la comanda o la Sede principal. Los abonos no necesitan migración: `cash_movement` ya es obligatorio.
   - Motivo de no guardar la sede del abono: es la misma razón de la decisión 4; una segunda copia exigiría garantizar que coincida con la de la sesión.
   - Motivo: el fiado es del cliente y se puede pagar en cualquier sede, pero cada reporte por sede necesita saber dónde nació la deuda y dónde entró el dinero.
4. **`CashMovement` no lleva sede.**
   - Decisión: la hereda de su sesión, y los índices por sede y fecha van en `CashSession`.
   - Motivo: guardarla dos veces exigiría garantizar que coincidan (una FK compuesta `(session_id, branch_id)`). Filtrar por sesión ya resuelve el reporte.
5. **"Gastos" no es un modelo.**
   - Decisión: un gasto es un `CashMovement` con `kind="gasto"`.
   - Motivo: ya es así en `apps/cash/models.py`, y un modelo aparte partiría el libro de caja (regla 9).
6. **Inventario por sede (S4b).**
   - Existencias: `StockLevel` (producto, sede, cantidad >= 0, único por producto y sede). `StockMovement` lleva sede obligatoria.
   - Consumo: al cerrar una comanda se descuenta del inventario de `order.branch`.
   - Alertas: únicas por (tipo, producto, sede), con `Alert.branch`. Incluye las de por vencer, que solo se generan en sedes con existencia > 0.
   - Totales: se elimina `Product.current_stock` y el total se calcula sumando. El mínimo sigue por producto.
   - Motivo: con stock por sede, un total guardado aparte se desincroniza. Las alertas tienen que decir en qué sede falta el producto.
7. **Zona horaria por sede: aplazada.**
   - Decisión: `Branch` no lleva zona horaria y todo sigue con `Barbershop.timezone`.
   - Motivo: con zonas distintas, el consolidado mezclaría días diferentes, y hoy todas las sedes están en Colombia. Ver "Trabajo futuro".
8. **Límite de sedes.**
   - Decisión: `Barbershop.max_branches` con valor por defecto 1. La migración pone a las existentes `max(1, número de sedes)`. Solo lo aplica el servicio de crear o reactivar sedes y cuenta solo las sedes activas, así que desactivar una libera cupo. La demo tiene 2 sedes con `max_branches = 3`.
   - Motivo: ninguna barbería existente queda por encima de su límite. Las pruebas y la demo, que crean sedes directamente, no dependen del plan.
9. **S2 se divide.**
   - Decisión: S2 es solo backend (alcance, middleware, cambio de sede y selectores). El selector visual y el modo "todas" del encabezado se diseñan y se aprueban junto con S3.
   - Hueco aceptado: entre S2 y S3 no hay forma visual de cambiar de sede (solo el POST de cambio de sede). S3 sigue inmediatamente después de S2.
   - Motivo: no están en el diseño aprobado (`docs/diseno.md`) y la regla de diseño de `AGENTS.md` prohíbe inventarlos.
10. **`?sede=` desaparece.**
    - Decisión: el tablero y el Excel usan `request.branch_scope`. En modo "todas", los indicadores suman las sedes permitidas desde S2; el comparativo por sede llega en S5. El filtro repetido (`_in_branch` y el de `closed_orders`) se unifica en un solo ayudante.
    - Motivo: una sola fuente para la sede activa, validada en el servidor en cada petición, en lugar de un parámetro que cada vista interpreta a su manera.
11. **Permisos.**
    - Decisión: módulo `sedes` con `ver` (ver todas y el consolidado: Dueño, Administrador y Consultor) y `gestionar` (Dueño y Administrador).
    - Motivo: sigue la convención en español de `MODULE_ACTIONS` y cumple `test_el_consultor_solo_lee`. Reemplaza los nombres `view_all` y `ver_todas`.
12. **Sede principal automática.**
    - Decisión: al crear una barbería se crea su "Sede principal" en la misma transacción, como pasa con `BarbershopSettings`.
    - Datos existentes: en una barbería que ya tenía sedes, la Sede principal es la más antigua (menor `id`).
   - Motivo: ninguna barbería queda sin sede, así que el alcance y los servicios siempre tienen una sede válida.
13. **Citas futuras.**
    - Decisión: la regla de no desactivar una sede con citas futuras queda pendiente y se activa cuando exista la agenda (fase 3 de `docs/arquitectura.md`).
    - Motivo: hoy no hay citas que revisar.
14. **Defecto de sede activa.**
    - Decisión: `receivables.add_payment` y `cash.selectors.current_session` deben exigir una sede activa. Se corrige en S1.
    - Motivo: caja, comandas y personal ya lo exigen; una sede desactivada no debe recibir dinero.

## Trabajo futuro

- **Zona horaria por sede** (decisión 7). Si llega una sede en otra zona:
  - se agrega `Branch.timezone`;
  - "hoy" y los períodos pasan a la zona de la sede en modo "una", y a la de la barbería en modo "todas";
  - hay que definir cómo se agrupa el consolidado por día.

  Puntos que hoy usan `Barbershop.timezone`:
  - `apps/sales/selectors.py` (`local_today`, `day_bounds`)
  - `apps/reports/scope.py`, `apps/reports/selectors/cash.py` y `apps/reports/selectors/dashboard.py`
  - `apps/inventory/selectors.py` y `apps/receivables/selectors.py`
  - `apps/alerts/management/commands/generar_alertas.py`
- **Citas futuras** al desactivar una sede (decisión 13), con la agenda.
