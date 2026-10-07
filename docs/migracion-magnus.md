# Migración de MAGNUS v1 a ScrumCut

Fuente: `../MAGNUS-PROJECTO` (FastAPI + SQLAlchemy + SQLite, una sola barbería), solo de consulta.
Se leyeron `backend/app/models/`, `services/`, `routes/` y `utils/`. Las rutas de origen de este documento son relativas a `backend/app/`.

Convenciones de ScrumCut que aplican a todas las tablas portadas, salvo que la tabla diga otra cosa:

- Heredan de `TenantScopedModel`: `barbershop`, `public_id` (UUID), `created_at`, `updated_at` con zona horaria. La migración termina con `EnableTenantRLS`.
- Dinero: `Numeric(12, 2)` → `DecimalField(max_digits=14, decimal_places=2)`, y se calcula con `Decimal` (MAGNUS suma en `float`).
- `datetime.utcnow` → `timezone.now()`. Los días de reporte se calculan con `Barbershop.timezone`, no con la constante `BUSINESS_TZ`.
- `is_deleted` → `SoftDeleteModel` (`deleted_at`). `is_active` se conserva donde significa "pausado" y no "borrado".
- Textos con valores fijos (`status`, `item_type`, `payment_method`, `movement_type`, `commission_type`) → `TextChoices`.
- Movimientos de caja, de inventario, pagos y abonos son solo-agregar: `on_delete=PROTECT`, sin `cascade="all, delete-orphan"`.
- `created_by_user_id` / `user_id` → FK a `accounts.User` (la persona) con `PROTECT`.

## a) Modelo MAGNUS → modelo ScrumCut

| Tabla MAGNUS | App ScrumCut | Modelo | Qué cambia | Qué se agrega |
|---|---|---|---|---|
| (sin tabla; `services.category` era texto libre) | catalog | `ServiceCategory` | — | Convenciones; `UniqueConstraint(barbershop, lower(name))` entre no borradas |
| `services` | catalog | `Service` | `category` texto libre → FK opcional a `ServiceCategory` (`PROTECT`); `estimated_duration_minutes` opcional → `duration_minutes` obligatorio y > 0 (lo usa la agenda); `uses_internal_consumables` se elimina (no se usa al descontar: lo decide la existencia de consumibles) | Convenciones; `UniqueConstraint(barbershop, lower(name))` entre no borrados, incluidos los desactivados; `CheckConstraint(price >= 0)` |
| `service_consumables` | inventory | `ServiceConsumable` | Borrado físico → se conserva físico (es configuración, no historial), pero con `PROTECT` hacia `Product` | `barbershop`; `UniqueConstraint(service, product)`; `CheckConstraint(quantity > 0)` |
| `categories` | inventory | `ProductCategory` | Índice único parcial por nombre → por barbería y sin distinguir mayúsculas | Convenciones |
| `products` | inventory | `Product` | `category` (texto heredado) se descarta; `product_type` → `TextChoices` (venta, consumible interno, perecedero); `photo_filename` → `ImageField` con almacenamiento por barbería | Convenciones; `CheckConstraint(current_stock >= 0)` |
| `inventory_movements` | inventory | `StockMovement` | `reference_type` + `reference_id` sueltos → FK opcionales a `OrderItem` (o `GenericForeignKey` si hay más orígenes) | `barbershop`, `public_id`; `unit_cost` copiado en cada salida; solo-agregar |
| `barbers` | staff | `Barber` | `user_id` → FK opcional a `tenancy.Membership` (rol Barbero); `commission_type` → `TextChoices` (porcentaje, fijo); `commission_value` validado (0–100 si es porcentaje); `quick_pin_hash` se descarta | Convenciones; `branch` opcional |
| `clients` | clients | `Client` | `is_active` se usa como borrado → `SoftDeleteModel`; documento normalizado al guardar | Convenciones; `UniqueConstraint(barbershop, document_number)` entre no borrados; base legal de datos personales (`legal`) |
| `orders` | sales | `Order` | `status` y `payment_status` → `TextChoices`; `discount` con `CheckConstraint(0 <= discount <= subtotal)` | Convenciones; `branch`; `closed_by`; `cancelled_at`, `cancelled_by`, `cancel_reason`; `commission_total` copiado al cerrar |
| `order_items` | sales | `OrderItem` | `item_type` → `TextChoices`; el precio siempre se toma del catálogo; ítem de producto exige `product` | `barbershop`, `public_id`; copiados al cerrar: `unit_price`, `unit_cost`, `consumables_cost`, `commission_type`, `commission_rate`, `commission_amount`, `name` |
| `payments` | sales | `Payment` | `payment_method` → `TextChoices`; `cash_register_id` → FK a `cash.CashSession` | Convenciones; solo-agregar (una anulación es un pago negativo con referencia) |
| `cash_registers` | cash | `CashSession` | `is_closed` se deriva de `closed_at`; `closing_amount` → `counted_amount` | Convenciones; `branch`; `expected_amount` y `difference` guardados al cerrar; `UniqueConstraint(barbershop, branch)` con condición `closed_at IS NULL` |
| `cash_movements` | cash | `CashMovement` | `movement_type` → `TextChoices` con dirección (ingreso/egreso); `amount` con signo o campo `direction` | Convenciones; FK opcionales a `Payment` / `ReceivablePayment`; solo-agregar. Es la única fuente del arqueo |
| `accounts_receivable` | receivables | `Receivable` | `status` → `TextChoices` (pendiente, pagado, vencido); `paid_amount` y `balance` se recalculan desde los abonos; `is_active` → `SoftDeleteModel` o anulación explícita | Convenciones; `UniqueConstraint(order)`; `CheckConstraint(balance >= 0)` |
| `accounts_receivable_payments` | receivables | `ReceivablePayment` | `payment_method` → `TextChoices`; `cash_register_id` → FK a `CashSession` | Convenciones; solo-agregar |
| `alerts` | alerts | `Alert` | `reference_type` + `reference_id` → FK opcionales o `GenericForeignKey` | Convenciones; `UniqueConstraint(alert_type, referencia)` entre no leídas |
| `audit_logs` | audit (existe) | `AuditLog` | Ya existe con `before`/`after` en JSON | — |
| `users`, `roles`, `permissions`, `role_permissions` | accounts / tenancy (existen) | `User`, `Membership`, `roles.py` | No se portan: el rol vive en `Membership` y la matriz en código | — |
| `system_config` | tenancy | campos de `Barbershop` o un `BarbershopSettings` tipado | Clave-valor libre → campos con tipo y validación | — |
| `master_code_config` | — | — | No se porta | — |
| (sin tabla) reportes y dashboard | reports | solo `selectors.py` | Consultas agregadas sin N+1 | Exportación a Excel con marca de la barbería (dato), no fija |

**Decisiones tomadas:**

1. Stock por barbería. Si llega el multi-sede, se agrega una tabla de stock por sede.
2. Caja por sede: `UniqueConstraint(barbershop, branch)` con condición `closed_at IS NULL`.
3. La comisión se calcula **solo sobre líneas de servicio**, nunca sobre productos. Porcentaje: sobre el precio neto de la línea, después de repartir el descuento de la comanda en proporción al subtotal. Monto fijo: por unidad de servicio, no por comanda. Se calcula y se copia en `OrderItem` al cerrar.
4. Métodos de pago: `TextChoices` fijos (`efectivo`, `nequi`, `daviplata`, `tarjeta`, `transferencia`, `bre_b`); cada barbería activa en su configuración los que usa. "Combinado" son varios `Payment`. "Cortesía" no es un método: es un descuento del 100 % con motivo obligatorio.
5. Los umbrales del estado del cliente son configurables por barbería. Valores por defecto (los de MAGNUS): VIP con ≥ 200 000 de gasto o ≥ 10 visitas, Frecuente con ≥ 3 visitas, Inactivo con más de 90 días sin visita y sin deuda.
6. (Defecto 11) Una comanda **no** se cierra con saldo: se paga completa o se convierte en fiado, con cliente obligatorio.

## b) Reglas de negocio

Origen como `archivo.función` dentro de `services/`, salvo que se indique otro directorio.

### Comandas (`order_service`)

1. Al crear: el cliente es opcional pero debe existir; el barbero es opcional pero no puede estar eliminado. — `order_service.create_order`
2. Estado inicial: comanda `abierta`, pago `pendiente`, pagado 0, subtotal y total 0. — `order_service.create_order`
3. Solo se modifican comandas en `abierta` o `pendiente`. — `order_service._validate_order_modifiable`
4. Ítem de servicio: servicio obligatorio, activo y no eliminado; precio del catálogo; descripción = la enviada, o la del servicio, o su nombre. — `order_service.add_order_item`
5. Ítem de producto: si trae producto, debe estar activo y no eliminado. — `order_service.add_order_item`
6. Total de línea = precio unitario × cantidad; cantidad > 0 y precio ≥ 0. — `order_service.add_order_item`, `update_order_item`, `schemas/order.OrderItemCreate`
7. Subtotal = suma de líneas; total = subtotal − descuento, nunca menor que 0. — `order_service._recalculate_order_totals`
8. Editar ítem cambia cantidad, precio o descripción y recalcula totales. — `order_service.update_order_item`
9. Quitar ítem lo elimina y recalcula totales. — `order_service.delete_order_item`
10. Una comanda se puede marcar `pendiente` (en espera). — `order_service.mark_order_pending`
11. Para cerrar: no puede estar cerrada ni cancelada, debe tener al menos un ítem y un barbero activo asignado (se puede asignar al cerrar). — `order_service.close_order`
12. Al cerrar se descuenta inventario: cada producto vendido descuenta su cantidad y cada servicio descuenta sus consumibles (cantidad del consumible × cantidad del ítem). Si algún producto no alcanza, el cierre falla. Cada descuento deja un movimiento (`salida_venta` o `salida_servicio`) con stock anterior, stock nuevo y referencia a la comanda. — `order_service._reserve_inventory_for_order`
13. Cobro al cerrar (comanda no fiada con saldo): el método es obligatorio, el monto por defecto es el saldo, debe ser > 0 y no puede superar el saldo. La caja es la indicada (abierta) o la única abierta; falla si no hay ninguna o si hay varias. Crea el pago y un movimiento de caja `ingreso_venta`. — `order_service.close_order`
14. Estado de pago al cerrar: `fiado` si la comanda es fiada; `pagado` si lo pagado ≥ total; si no, `parcial`. — `order_service.close_order`
15. Fiado con saldo: exige cliente y crea (o actualiza) la cuenta por cobrar con total, pagado y saldo. — `order_service._sync_accounts_receivable_for_order`
16. El cierre completo (inventario, pago, caja, fiado, auditoría) es una sola transacción con rollback ante cualquier error. — `order_service.close_order`
17. Registro rápido: tipo `corte` o `producto`, método de pago obligatorio, barbero activo, precio siempre del catálogo, sin cliente y sin fiado; crea, agrega el ítem y cierra en una sola transacción. — `order_service.quick_register_order`
18. No se cancela una comanda cerrada o ya cancelada. — `order_service.cancel_order`
19. El historial muestra el nombre guardado en la venta y agrega "(eliminado)" si el servicio, producto, barbero o categoría se borró después. — `order_service._item_display_name`, `utils/deleted_labels`

### Pagos (`payment_service`)

20. No se paga una comanda cancelada; la caja es opcional, pero si se indica debe estar abierta; el pago suma a lo pagado y fija el estado `pagado` o `parcial`; si hay caja, deja un movimiento. — `payment_service.create_payment`

### Caja (`cash_register_service`, `cash_movement_service`)

21. Solo puede haber una caja abierta. — `cash_register_service.open_cash_register`
22. El monto de apertura es ≥ 0. — `schemas/cash_register.CashRegisterOpenRequest`
23. No se cierra una caja ya cerrada. — `cash_register_service.close_cash_register`
24. Arqueo: esperado = apertura + pagos de comandas en efectivo + abonos de fiados en efectivo ligados a la caja. Los demás métodos no cuentan como efectivo físico. Diferencia = contado − esperado. — `cash_register_service.close_cash_register`
25. Un movimiento manual exige una caja existente y abierta, y un monto > 0. — `cash_movement_service.create_cash_movement`

### Fiados (`accounts_receivable_service`)

26. Fiado manual: el cliente debe existir, la comanda es opcional, el total es > 0, el saldo inicial es igual al total y el estado inicial es `pendiente`. — `accounts_receivable_service.create_accounts_receivable`
27. Abono: monto > 0; queda ligado a la caja abierta más reciente si existe, y la falta de caja nunca bloquea el abono; solo el abono en efectivo crea movimiento de caja; recalcula pagado, saldo y estado (`pagado` si el saldo es ≤ 0). — `accounts_receivable_service.add_accounts_receivable_payment`
28. Vencido: fiado activo, con saldo, con fecha de vencimiento anterior a hoy (en la zona del negocio) y no pagado. — `accounts_receivable_service.refresh_overdue_status`
29. Resumen: cantidad y saldo de fiados pendientes y de vencidos. — `accounts_receivable_service.get_accounts_receivable_summary`

### Inventario (`inventory_service`, `category_service`)

30. Tipos de producto: venta, consumible interno, perecedero. — `inventory_service.create_product`, `update_product`
31. La categoría asignada debe existir y no estar eliminada. — `inventory_service._validate_category_id`
32. El stock nunca queda negativo. — `inventory_service.update_product`, `create_inventory_adjustment`
33. Entrada: cantidad > 0 y motivo obligatorio; deja un movimiento `entrada` con stock anterior y nuevo. — `inventory_service.create_inventory_entry`
34. Ajuste: cantidad con signo y motivo obligatorio; no puede dejar el stock negativo; deja un movimiento `ajuste`. — `inventory_service.create_inventory_adjustment`
35. Borrado lógico de producto: un producto eliminado no se usa ni se edita, pero su historial queda. — `inventory_service.delete_product`, `get_live_product`
36. Foto de producto: el formato se valida con el contenido real (PNG, JPEG o WEBP) y se guarda recortada a un cuadrado de 200 × 200 px. — `inventory_service.save_product_photo`
37. Categoría: nombre obligatorio y único entre las vivas, sin distinguir mayúsculas. Al borrarla, sus productos pasan a "Sin categoría" o se borran lógicamente, a elección. "Sin categoría" aparece en la lista solo si tiene productos activos. — `category_service.create_category`, `delete_category`, `list_categories`

### Catálogo (`service_service`, `service_consumable_service`)

38. El nombre de un servicio es único entre los activos. — `service_service.create_service`, `update_service`
39. Un servicio se desactiva o se borra lógicamente. — `service_service.deactivate_service`, `delete_service`
40. Consumible de servicio: servicio y producto activos, un solo registro por par servicio-producto, cantidad > 0. — `service_consumable_service.create_service_consumable`

### Barberos (`barber_service`)

41. Un usuario se vincula a lo sumo a un barbero. — `barber_service.create_barber`, `update_barber`
42. Borrado lógico de barbero; el barbero del dueño no se puede borrar. — `barber_service.delete_barber`
43. Acceso de barbero: contraseña de al menos 8 caracteres con letra y número; usuario derivado del nombre y único. En ScrumCut se reemplaza por una invitación por correo que crea la `Membership` con rol Barbero. — `barber_service.create_barber_user`, `reset_barber_password`, `toggle_barber_access`
44. Rendimiento: comandas cerradas en un rango (por defecto los últimos 30 días, en la zona del negocio), ventas y comisión: porcentaje sobre el total, o monto fijo por comanda. — `barber_service.get_barber_performance`
45. Los selectores de formularios reciben solo id y nombre de los barberos activos, sin datos administrativos. — `barber_service.list_active_barbers_basic`

### Clientes (`client_service`)

46. Duplicados: mismo teléfono, o mismo documento (sin espacios, en mayúsculas), entre clientes activos. Se puede forzar la creación. — `client_service.find_duplicate_active_client`, `create_client`
47. Perfil: visitas (comandas cerradas), gasto total, última visita, saldo pendiente y estado. Los estados son Deudor (tiene saldo), VIP (≥ 200 000 de gasto o ≥ 10 visitas), Frecuente (≥ 3 visitas), Nuevo, e Inactivo (más de 90 días sin visita y sin deuda). — `client_service.get_client_profile`

### Alertas (`alert_service`)

48. Alertas automáticas: agotado (stock ≤ 0), stock bajo (≤ mínimo), por vencer (≤ 30 días) y fiado vencido. No se duplica una alerta activa no leída para la misma referencia. — `alert_service.generate_system_alerts`

### Reportes y tablero (`reports_service`, `dashboard_service`, `excel_report_service`)

49. Rango por defecto: los últimos 30 días. Los días se interpretan en la zona del negocio y las ventas se agrupan por día local. — `reports_service._resolve_range`, `sales_by_period`
50. Ventas por barbero con comisión estimada. — `reports_service.sales_by_barber`
51. Productos más vendidos, por cantidad. — `reports_service.top_products`
52. Cierres de caja con el mismo criterio del arqueo. — `reports_service.cash_closings`
53. Tablero: ingresos del día (pagos + abonos, todos los métodos), comandas cerradas hoy, comandas abiertas, caja abierta con su esperado, inventario crítico, fiados y alertas no leídas. — `dashboard_service.get_dashboard_summary`
54. "Mis cortes de hoy": el barbero ve solo su conteo, sin dinero. — `dashboard_service.get_my_cuts_today`
55. Exportación contable: ventas con costo por línea de producto (los servicios no tienen costo directo; la comisión va aparte), comisiones, fiados, movimientos, cierres, estado de resultados y panorama. — `excel_report_service.generate_business_report_excel`

### Seguridad (ya cubierta por ScrumCut; solo referencia)

56. Bloqueo tras 5 intentos fallidos durante 15 minutos. — `security_service.authenticate_user` → axes
57. Matriz de permisos `modulo.accion` por rol. — `security_service.seed_initial_security` → `apps/tenancy/roles.py`. En MAGNUS el Barbero puede abrir caja; la matriz de ScrumCut decide.
58. Toda escritura deja auditoría con usuario, módulo y acción. — `security_service.create_audit_log` → `audit.AuditLog`

## c) No se porta

| Qué | Origen | Por qué |
|---|---|---|
| Marca Magnus: nombre de la app, "Administrador MAGNUS", banners, logos, colores y pie del Excel, créditos | `config.py`, `security_service.seed_initial_security`, `excel_report_service` (identidad visual) | Regla 1 y marca neutra (regla 2): la identidad es dato de `Barbershop` |
| Código maestro de recuperación | `models/master_code.py`, `services/master_code_service.py`, `routes/security_routes.py` | Restablece cualquier cuenta con un secreto compartido (S3); se usa recuperación por correo |
| JWT en `localStorage`, `python-jose`, `HTTPBearer` | `utils/security.py` | Sesión en cookie `HttpOnly` (S2, S12) |
| Tablas `users`, `roles`, `permissions`, `role_permissions` y su seed | `models/security.py`, `security_service` | Ya existen `User`, `Membership` y la matriz en `roles.py` |
| Dueño identificado por nombre de usuario (`mateo`, `admin`) | `utils/security.OWNER_USERNAME(S)`, `require_owner`, `barber_service.is_owner_barber`, `security_service.deactivate_user` | El dueño es un rol (S5) |
| Administrador inicial desde `ADMIN_PASSWORD` | `security_service.seed_initial_security` | Alta de barbería con dueño verificado (S8) |
| Cambio y validación de contraseña propios | `security_service.change_password`, `barber_service._validate_password` | allauth + validadores de Django (S7) |
| Frontend HTML/JS y su montaje con `StaticFiles` | `frontend/`, `main.py` | Regla 1; la interfaz se diseña con las pautas de `CLAUDE.md` |
| `system_config` clave-valor | `models/system_config.py`, `system_config_service` | Sin tipos ni validación; se reemplaza por campos tipados de la barbería |
| `quick_pin_hash` del barbero | `models/barber.py` | Se guarda pero ningún flujo lo usa |
| `Product.category` (texto libre heredado) | `models/inventory.py` | Reemplazado por FK a categoría |
| `Service.uses_internal_consumables` | `models/service.py` | Ninguna regla lo consulta |
| SQLite, `create_tables.py`, ejecutable empaquetado | `database.py`, `create_tables.py`, `config.py` | PostgreSQL con migraciones y RLS |
| Endpoint para crear alertas a mano | `alert_service.create_alert` | Las alertas son del sistema; si se necesitan avisos manuales, se diseñan aparte |

## d) Defectos de MAGNUS a corregir al portar

### Dinero y comisiones

1. **La comisión se calcula con la configuración actual del barbero**, no con la vigente al cerrar: si cambia su porcentaje, cambian las comisiones ya pagadas. — `barber_service.get_barber_performance`, `reports_service.sales_by_barber`, `excel_report_service._build_comisiones_sheet` → copiar `commission_type`, `commission_rate` y `commission_amount` en `OrderItem` al cerrar (regla 10).
2. **El costo de venta usa el `purchase_cost` actual del producto**: cambiar el costo reescribe la utilidad de meses pasados. — `excel_report_service._build_ventas_sheet` → copiar `unit_cost` y el costo de consumibles al cerrar.
3. **Base de comisión ambigua**: porcentaje sobre `Order.total` (incluye productos y fiados no cobrados) y monto fijo por comanda, no por servicio. — `barber_service.get_barber_performance`, `reports_service.sales_by_barber` → decisión 3.
4. **Dinero en `float`**: la base guarda `Numeric`, pero todo se convierte a `float` para sumar y comparar (con tolerancia de 0,01). — en todos los services → `Decimal` de punta a punta.
5. **Descuento sin validar**: uno negativo sube el total y uno mayor que el subtotal se recorta a 0 en silencio. — `schemas/order.OrderCreate.discount`, `order_service._recalculate_order_totals`

### Comandas

6. **`list_orders` no filtra por barbero** ni pagina: un barbero ve todas las comandas y `get_order_by_id` abre cualquiera por id. — `order_service.list_orders`, `get_order_by_id` → selector filtrado por dueño (regla 5).
7. **Precio manipulable**: el ítem de producto toma `unit_price` del payload y `update_order_item` deja cambiar el precio de cualquier ítem con el permiso `comandas.editar`, que tiene el barbero. — `order_service.add_order_item`, `update_order_item`
8. **`item_type` es texto libre**: cualquier valor distinto de `servicio` se trata como producto, y un "producto" sin `product_id` es una línea libre con precio libre. — `order_service.add_order_item`
9. **`mark_order_pending` no valida el estado**: una comanda cerrada vuelve a `pendiente`, se edita y se cierra otra vez, lo que descuenta inventario y cobra de nuevo. — `order_service.mark_order_pending`
10. **Cierre sin bloqueo de la comanda**: dos solicitudes simultáneas (doble clic) pasan el chequeo de estado y la cierran dos veces. — `order_service.close_order` → `select_for_update` sobre la comanda.
11. **Una comanda no fiada se cierra con pago parcial y el saldo desaparece**: queda `parcial`, sin fiado, porque `_sync_accounts_receivable_for_order` solo se llama si `is_fiado`. — `order_service.close_order` → decisión 6: se paga completa o se convierte en fiado.
12. **Cancelar no revierte los pagos** ya registrados ni sus movimientos de caja. — `order_service.cancel_order`
13. **`str(e)` devuelto al usuario** (S6). — `order_service.close_order`

### Inventario

14. **Falta `select_for_update` al descontar stock**: es leer, restar y escribir sin bloqueo, así que dos cierres simultáneos pierden un descuento o dejan stock negativo. — `order_service._reserve_inventory_for_order`, `inventory_service.create_inventory_entry`, `create_inventory_adjustment` → `select_for_update` + `F()` + `CheckConstraint(current_stock >= 0)`.
15. **Editar un producto fija `current_stock` directamente**, sin dejar movimiento. — `inventory_service.update_product` → el stock solo cambia por entradas, ajustes y ventas.
16. **Movimientos y pagos se borran en cascada** (`cascade="all, delete-orphan"`). — `models/inventory.Product.movements`, `models/cash_register.CashRegister.movements`, `models/order.Order.payments`, `models/accounts_receivable.AccountsReceivable.payments` → solo-agregar con `PROTECT` (regla 9).

### Caja y pagos

17. **"Solo una caja abierta" sin respaldo en la base**: dos aperturas simultáneas abren dos cajas. — `cash_register_service.open_cash_register` → `UniqueConstraint` condicional.
18. **El arqueo ignora los movimientos manuales** (gastos, retiros, ingresos), y `movement_type` es texto libre con monto siempre positivo, sin dirección. — `cash_register_service.close_cash_register`, `cash_movement_service.create_cash_movement` → el arqueo se calcula desde `CashMovement`.
19. **El arqueo compara `payment_method == "efectivo"` exacto** sobre texto libre: "Efectivo" queda fuera del esperado. — `cash_register_service.close_cash_register`, `reports_service.cash_closings`
20. **La diferencia del arqueo no se guarda**: solo queda en el texto de auditoría y se recalcula en los reportes. — `cash_register_service.close_cash_register`
21. **Libro de caja inconsistente**: el cobro al cerrar crea movimiento para cualquier método, el abono de fiado solo para efectivo, y el pago suelto solo si se indicó caja. Además usan tipos distintos (`ingreso_venta` frente a `pago`). — `order_service.close_order`, `accounts_receivable_service.add_accounts_receivable_payment`, `payment_service.create_payment`
22. **El pago suelto no valida el saldo**: permite pagar de más y pagar comandas cerradas. — `payment_service.create_payment`
23. **El "esperado en caja" del tablero solo cuenta pagos de hoy**: con una caja abierta desde ayer, el tablero y el arqueo dan cifras distintas. — `dashboard_service.get_dashboard_summary`

### Fiados

24. **El abono no valida el saldo** (puede dejarlo negativo), permite abonar a fiados pagados o inactivos y no bloquea la fila. — `accounts_receivable_service.add_accounts_receivable_payment`
25. **El resumen de fiados escribe en la base** (marca vencidos y hace commit en cada consulta). — `accounts_receivable_service.get_accounts_receivable_summary` → tarea programada.

### Lecturas con efectos y rendimiento

26. **Cargar el tablero genera alertas y hace commit** en cada solicitud. — `dashboard_service.get_dashboard_summary` → tarea programada (fase 2).
27. **Consultas N+1** en reportes (una consulta por barbero, producto o cliente) y en categorías (un conteo por categoría). — `reports_service.sales_by_barber`, `top_products`, `accounts_receivable_report`, `category_service.serialize_category`

### Fechas

28. **Fechas sin zona horaria**: `datetime.utcnow` en todos los modelos y services, conversión manual "UTC naivo ↔ Bogotá" en reportes, tablero y rendimiento, y `get_client_profile` compara contra `utcnow`. — `models/*`, `reports_service._resolve_range`, `dashboard_service._today_bounds`, `barber_service.get_barber_performance`, `client_service.get_client_profile` → `timezone.now()` y `Barbershop.timezone`.

### Capas y permisos

29. **Un service lanza `HTTPException`**, lo que mezcla capas. — `barber_service.delete_barber`
30. **Escrituras con permiso de lectura** (S11). — `routes/alerts_routes.py`
31. **La auditoría de "alerta leída" se agrega después del commit** y nunca se guarda. — `alert_service.mark_alert_as_read`
32. **La unicidad del servicio solo cuenta los activos**: se puede crear un servicio con el nombre de uno desactivado. El cliente duplicado solo se valida en la aplicación. — `service_service.create_service`, `client_service.create_client` → restricciones en la base.

## e) Orden de migración propuesto

Ya existen `core`, `tenancy` (Barbershop, Branch, Membership), `accounts`, `audit` y `legal`.

| Paso | App | Depende de | Contenido |
|---|---|---|---|
| 1 | catalog | tenancy | `Service` |
| 2 | staff | tenancy (`Membership`, `Branch`) | `Barber` y comisión vigente |
| 3 | clients | tenancy, legal | `Client`, duplicados y perfil (el perfil completo espera a sales y receivables) |
| 4 | inventory | catalog | `ProductCategory`, `Product`, `StockMovement`, `ServiceConsumable`, entradas y ajustes con bloqueo |
| 5 | cash | tenancy (`Branch`), accounts | `CashSession`, `CashMovement`, apertura, cierre y arqueo |
| 6 | sales | catalog, staff, clients, inventory, cash | `Order`, `OrderItem`, `Payment`; cierre con descuento de stock, cobro y copia de precio, costo y comisión; registro rápido. Al principio sin fiado |
| 7 | receivables | clients, sales, cash | `Receivable`, `ReceivablePayment`; habilita "cerrar como fiado" en sales y los abonos |
| 8 | alerts | inventory, receivables | `Alert` y la generación como tarea programada |
| 9 | reports | todas las anteriores | Selectores de ventas, comisiones, top de productos, fiados, cierres, tablero y exportación |

Los pasos 1 a 7 son la fase 1 (operación diaria) y los pasos 8 y 9 la fase 2 (gerencia) de `docs/arquitectura.md`. Decisiones que aplica cada paso: la 1 en el paso 4; la 2 y la 4 en el 5; la 3 en el 2 y el 6; la 5 en el 3; la 6 en el 6 y el 7.
