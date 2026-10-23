import { useEffect, useState } from 'react'
import {
  Banknote, BarChart3, Bell, BookOpen, Boxes, CalendarDays, ChevronLeft,
  ChevronRight, ClipboardList, Command, CreditCard, LayoutDashboard, Moon,
  Package, RefreshCw, Search, Sparkles, Star, Sun, Users, X
} from 'lucide-react'

type Page = 'Tablero' | 'Comandas' | 'Caja' | 'Clientes' | 'Fiados' | 'Reportes' | 'Sistema'
type Role = 'Dueño' | 'Cajero'

const money = (n: number) => '$' + new Intl.NumberFormat('es-CO').format(n)
const nav = [
  ['OPERACIÓN', [['Tablero',LayoutDashboard],['Agenda · Pronto',CalendarDays],['Comandas',ClipboardList],['Caja',Banknote]]],
  ['CLIENTES', [['Clientes',Users],['Fiados',CreditCard],['Reseñas · Pronto',Star]]],
  ['CATÁLOGO', [['Servicios',BookOpen],['Inventario',Boxes]]],
  ['ANÁLISIS', [['Reportes',BarChart3],['Comparativo de sedes',BarChart3]]],
] as const

function Button({ children, kind = 'primary', onClick }: { children: React.ReactNode; kind?: string; onClick?: () => void }) {
  return <button className={`btn ${kind}`} onClick={onClick}>{children}</button>
}
function Pill({ children, tone = '' }: { children: React.ReactNode; tone?: string }) {
  return <span className={`pill ${tone}`}>{children}</span>
}
function Logo({ compact = false }: { compact?: boolean }) {
  return <div className="logo"><img src={compact ? '/scrumcut-mark.svg' : '/scrumcut-logo.svg'} /><div><b>SCRUMCUT</b>{!compact && <small>Gestión para barberías</small>}</div></div>
}
function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  const paths = ['4,18 15,14 27,16 39,8 51,11 63,4 76,7','4,15 15,17 27,10 39,13 51,7 63,9 76,3','4,18 15,12 27,14 39,10 51,12 63,5 76,8']
  return <div className="metric"><span>{label}</span><strong>{value}</strong><svg className="trend" viewBox="0 0 80 22" aria-hidden="true"><polyline points={paths[label.length%3]}/></svg><small className="delta">{note}</small></div>
}
function Dots() { return <button className="icon-btn" aria-label="Más opciones">•••</button> }

function Dashboard() {
  const days = Array.from({length:35},(_,i)=>{
    const day=i-2
    if(day<1 || day>31) return null
    const future=day>22
    const noSale=[4,11,18].includes(day)
    const level=noSale?0:((day*7)%5)+1
    const amount=noSale?0:level*241000+(day%4)*37000
    return {day,future,noSale,level,amount,orders:noSale?0:level*3+2}
  })
  const weeks=Array.from({length:5},(_,w)=>days.slice(w*7,w*7+7).reduce((s,d)=>s+(d?.amount||0),0))
  return <>
    <div className="title-row"><div><p className="eyebrow">TABLERO</p><h1>Resumen ejecutivo</h1><p>Jueves, 22 de octubre de 2026 · Todas las sedes</p></div><div className="page-tools"><span>Actualizado hace 2 min</span><button className="refresh" aria-label="Refrescar"><RefreshCw size={16}/></button><Button kind="secondary">Exportar informe</Button></div></div>
    <div className="metrics">
      <Metric label="INGRESOS DE HOY" value="$3.440.000" note="▴ +12,4 % vs. miércoles anterior" />
      <Metric label="COMANDAS CERRADAS" value="47" note="8 abiertas ahora" />
      <Metric label="TICKET PROMEDIO" value="$73.191" note="▴ +$4.200 esta semana" />
      <Metric label="ESPERADO EN CAJA" value="$1.284.000" note="Centro · Caja principal" />
      <Metric label="FIADOS PENDIENTES" value="$682.000" note="▾ −$80.000 · 4 vencidos" />
    </div>
    <div className="grid-main">
      <section className="panel calendar-panel">
        <div className="panel-head"><div><h2>Ventas por día</h2><div className="month-nav"><button aria-label="Mes anterior"><ChevronLeft size={16}/></button><p>Octubre de 2026</p><button aria-label="Mes siguiente"><ChevronRight size={16}/></button></div></div><div className="seg"><button className="active">Calendario</button><button>Torres 3D</button></div></div>
        <div className="week-head">{['Lun','Mar','Mié','Jue','Vie','Sáb','Dom','Semana'].map(x=><b key={x}>{x}</b>)}</div>
        <div className="calendar">{days.map((d,i)=><div className={`day ${d?.future?'future':d?`h${d.level}`:'outside'} ${d?.day===22?'today':''}`} key={i}>{d&&<><span>{d.day}</span>{!d.future&&(d.noSale?<em>Sin ventas</em>:<b>{money(d.amount)}</b>)}{!d.future&&!d.noSale&&<span className="day-tip"><strong>Jueves, {d.day} de octubre</strong><i>Vendido <b>{money(d.amount)}</b></i><i>Comandas <b>{d.orders}</b></i><i>Ticket promedio <b>{money(Math.round(d.amount/d.orders))}</b></i></span>}</>}</div>).flatMap((cell,i)=>i%7===6?[cell,<div className="week-total" key={`w${i}`}><span>Total</span><b>{money(weeks[Math.floor(i/7)])}</b></div>]:[cell])}</div>
        <div className="legend"><span>Menor venta</span><i className="h1"/><i className="h2"/><i className="h3"/><i className="h4"/><i className="h5"/><span>Mayor venta</span></div>
      </section>
      <section className="panel cash">
        <div className="panel-head"><div><h2>Cuadre de caja</h2><p>Centro · En curso</p></div><Pill tone="positive">Abierta</Pill></div>
        {[['Apertura','$400.000'],['+ Ventas en efectivo','$1.126.000'],['+ Abonos recibidos','$106.000'],['− Gastos','−$148.000'],['− Retiros','−$200.000']].map(x=><div className="cash-row" key={x[0]}><span>{x[0]}</span><b>{x[1]}</b></div>)}
        <div className="cash-row total"><span>Esperado</span><strong>$1.284.000</strong></div>
        <div className="cash-row"><span>Contado hasta ahora</span><b>—</b></div>
        <Button kind="secondary">Ir a caja</Button>
      </section>
    </div>
    <div className="grid-lower">
      <section className="panel"><div className="panel-head"><div><h2>Rendimiento por barbero</h2><p>Ventas y comisión de hoy</p></div><Dots/></div><table><thead><tr><th>Barbero</th><th>Comandas</th><th>Ventas</th><th>Comisión</th></tr></thead><tbody>
        {[
          ['Mauricio Ríos','12','$896.000','$313.600'],['Felipe Gómez','10','$742.000','$259.700'],['Andrés Mena','9','$668.000','$233.800'],['Julián Castro','8','$591.000','$206.850']
        ].map(r=><tr key={r[0]}>{r.map((x,i)=><td key={x} className={i>0?'num':''}>{i===0?<><span className="avatar">{x[0]}{x.split(' ')[1][0]}</span>{x}</>:x}</td>)}</tr>)}
      </tbody></table></section>
      <section className="panel alerts"><div className="panel-head"><div><h2>Requiere atención</h2><p>6 alertas activas</p></div><button className="text-btn">Ver todas</button></div>
        <div><i className="alert-dot"/><p><b>Cera Matte Urban</b><span>Agotado · Sede Centro</span></p><Pill>Inventario</Pill></div>
        <div><i className="alert-dot"/><p><b>Diego Vargas</b><span>Fiado vencido hace 18 días</span></p><Pill>Cartera</Pill></div>
        <div><i className="alert-dot"/><p><b>After shave Proraso</b><span>3 unidades · stock bajo</span></p><Pill>Inventario</Pill></div>
      </section>
    </div>
  </>
}

const commands = [
  ['#1048','Santiago Mora','Mauricio Ríos','Corte clásico + barba','$82.000','Abierta'],
  ['#1047','Juan David Ruiz','Felipe Gómez','Corte premium','$58.000','Abierta'],
  ['#1046','Carlos Mejía','Andrés Mena','Barba + cera matte','$76.000','Abierta'],
  ['#1045','Nicolás Torres','Julián Castro','Corte + barba + cejas','$95.000','Cerrada'],
]
function Commandas() {
  return <><div className="title-row"><div><p className="eyebrow">OPERACIÓN</p><h1>Comandas</h1><p>Servicios, productos y cobros del día</p></div><Button>+ Nueva comanda</Button></div>
    <div className="tabs"><button className="active">Abiertas <b>8</b></button><button>Cerradas hoy <b>47</b></button><button>Anuladas</button></div>
    <div className="split-view"><section className="panel list"><div className="search">Buscar cliente o número de comanda</div>{commands.map((r,i)=><button className={`command ${i===0?'selected':''}`} key={r[0]}><span><b>{r[1]}</b><small>{r[0]} · {r[2]}</small></span><span><b>{r[4]}</b><small>{r[5]}</small></span></button>)}</section>
    <section className="panel receipt"><div className="panel-head"><div><p className="eyebrow">COMANDA #1048</p><h2>Santiago Mora</h2><p>Hoy, 2:42 p. m. · Mauricio Ríos</p></div><Pill tone="positive">Abierta</Pill></div>
      <div className="line"><span><b>Corte clásico</b><small>Mauricio Ríos · 35 % comisión</small></span><b>$46.000</b></div>
      <div className="line"><span><b>Diseño de barba</b><small>Mauricio Ríos · 35 % comisión</small></span><b>$36.000</b></div>
      <div className="cash-row total"><span>Total</span><strong>$82.000</strong></div>
      <h3>Forma de pago</h3><div className="pay-grid">{['Efectivo','Nequi','Daviplata','Tarjeta','Transferencia','Bre-B','Fiado'].map((x,i)=><button className={i===0?'active':''} key={x}>{x}</button>)}</div>
      <div className="field"><label>Recibido</label><div>$100.000</div></div><div className="change"><span>Vueltas</span><b>$18.000</b></div>
      <Button>Cobrar $82.000</Button><button className="text-btn center">Dividir el pago</button>
    </section></div></>
}

function Caja() {
  return <><div className="title-row"><div><p className="eyebrow">OPERACIÓN · CENTRO</p><h1>Caja</h1><p>Control de efectivo y movimientos · 22 oct. 2026</p></div><Pill tone="positive">Abierta desde 8:02 a. m.</Pill></div>
    <div className="notice">Esta caja viene de otro día. Revisa los movimientos antes de continuar.<Button kind="text">Revisar</Button></div>
    <div className="metrics"><Metric label="APERTURA" value="$400.000" note="Registrada por Laura" /><Metric label="ENTRADAS" value="$1.232.000" note="Ventas y abonos" /><Metric label="SALIDAS" value="$348.000" note="Gastos y retiros" /><Metric label="ESPERADO" value="$1.284.000" note="Efectivo calculado" /></div>
    <div className="grid-main"><section className="panel"><div className="panel-head"><div><h2>Movimientos</h2><p>Hoy · 26 registros</p></div><Button kind="secondary">Registrar movimiento</Button></div><table><thead><tr><th>Hora</th><th>Concepto</th><th>Responsable</th><th>Valor</th></tr></thead><tbody>{[['2:48 p. m.','Venta #1044','Laura Peña','+$96.000'],['1:32 p. m.','Compra de insumos','Laura Peña','−$148.000'],['12:10 p. m.','Abono fiado · Diego V.','Camila Ruiz','+$106.000'],['11:45 a. m.','Retiro parcial','Laura Peña','−$200.000']].map(r=><tr key={r[0]}>{r.map((x,i)=><td className={i===3?'num':''} key={x}>{x}</td>)}</tr>)}</tbody></table></section>
    <section className="panel"><h2>Arqueo por billetes</h2><p>Cuenta el efectivo disponible</p>{[['$100.000','6'],['$50.000','8'],['$20.000','10'],['$10.000','7']].map(r=><div className="denom" key={r[0]}><span>{r[0]}</span><span className="input">{r[1]}</span><b>{money(Number(r[0].replace(/\D/g,''))*Number(r[1]))}</b></div>)}<div className="cash-row total"><span>Contado</span><strong>$1.270.000</strong></div><div className="difference"><span>Diferencia</span><b>▾ −$14.000 · faltante</b></div><div className="field"><label>Nota obligatoria</label><div>Describe la diferencia encontrada</div></div></section></div>
  </>
}

function Clients({ debt = false }: { debt?: boolean }) {
  const rows = debt ? [['Diego Vargas','Centro','$286.000','18 días'],['Óscar Parra','Norte','$178.000','34 días'],['Samuel León','Centro','$124.000','8 días'],['Mateo Díaz','Norte','$94.000','Al día']] : [['Santiago Mora','Oro · Centro','Mauricio Ríos','21 oct. 2026'],['Juan David Ruiz','Plata · Norte','Felipe Gómez','22 oct. 2026'],['Carlos Mejía','Oro · Centro','Andrés Mena','22 oct. 2026'],['Nicolás Torres','Bronce · Norte','Julián Castro','20 oct. 2026']]
  return <><div className="title-row"><div><p className="eyebrow">CLIENTES</p><h1>{debt?'Fiados':'Clientes'}</h1><p>{debt?'Cartera, antigüedad y recaudo':'Historia y relación con cada cliente'}</p></div><Button>{debt?'+ Registrar abono':'+ Nuevo cliente'}</Button></div>
    {debt && <div className="aging"><div><b>$682.000</b><span>Cartera total</span></div>{[['Al día','14 %'],['1 a 15 días','28 %'],['16 a 30 días','39 %'],['Más de 30','19 %']].map(x=><div key={x[0]}><span>{x[0]}</span><b>{x[1]}</b><i style={{width:x[1]}}/></div>)}</div>}
    <div className="split-view"><section className="panel list"><div className="search">Buscar por nombre o celular</div><table><thead><tr><th>Cliente <span className="sort">↑</span></th><th>{debt?'Sede':'Nivel por sede'}</th><th>{debt?'Deuda':'Barbero habitual'} <span className="sort">↕</span></th><th>{debt?'Antigüedad':'Última visita'} <span className="sort">↕</span></th></tr></thead><tbody>{rows.map((r,i)=><tr className={i===0?'selected-row':''} key={r[0]}>{r.map((x,j)=><td key={x} className={j>1?'num':''}>{j===0?<b>{x}</b>:x}</td>)}</tr>)}</tbody></table><div className="pagination"><span>1–50 de 312</span><div><button disabled><ChevronLeft size={15}/></button><button><ChevronRight size={15}/></button></div></div></section>
    <section className="panel profile"><div className="profile-head"><span className="avatar big">{debt?'DV':'SM'}</span><div><h2>{debt?'Diego Vargas':'Santiago Mora'}</h2><p>+57 315 742 8801 · Cliente desde 2023</p></div></div>{debt?<><div className="amount-block"><span>Saldo pendiente</span><strong>$286.000</strong><small>Vence desde el 4 oct. 2026</small></div><div className="field"><label>Valor del abono</label><div>$100.000</div></div><div className="field"><label>Medio de pago</label><div>Nequi</div></div><Button>Registrar abono</Button></>:<><p className="eyebrow">NIVEL EN SEDE CENTRO</p><h3>Oro · 8 de 10 visitas</h3><div className="progress"><i/></div><p>2 visitas para alcanzar nivel Negro</p><div className="facts"><span>Barbero habitual<b>Mauricio Ríos</b></span><span>Ticket promedio<b>$78.400</b></span><span>Deuda actual<b>$0</b></span></div><h3>Últimas visitas</h3><div className="line"><span>Corte clásico + barba<small>21 oct. · Mauricio Ríos</small></span><b>$82.000</b></div></>}</section></div>
  </>
}

const tokenRows = [
 ['Fondo','#F5F3EE','#111311'],['Superficie','#FCFBF8','#181B18'],['Elevada','#FFFFFF','#20231F'],['Barra lateral','#EDEAE2','#0C0E0C'],['Barra superior','#FCFBF8','#181B18'],['Línea','#D7D3C8','#343832'],['Texto principal','#1B201C','#F2F0E9'],['Texto secundario','#62685F','#A8AFA4'],['Acento','#876B32','#C7A85F'],['Acento suave','#E8DFC8','#332C1D'],['Positivo','#386248','#79A889'],['Atención','#8A5B28','#D6A363'],['Deshabilitado','#A8AAA5','#666B64']]
function System() {
 return <><div className="title-row"><div><p className="eyebrow">IDENTIDAD VISUAL</p><h1>Sistema ScrumCut</h1><p>Precisión operativa, oficio y alta gerencia</p></div><Logo/></div>
 <section className="panel"><div className="panel-head"><div><h2>Color semántico</h2><p>Bronce mineral · contraste AA en ambos modos</p></div></div><div className="tokens">{tokenRows.map(t=><div key={t[0]}><span className="swatch" style={{background:t[1]}}/><b>{t[0]}</b><code>{t[1]}</code><span className="swatch dark-swatch" style={{background:t[2]}}/><code>{t[2]}</code></div>)}</div></section>
 <div className="grid-main"><section className="panel"><h2>Tipografía</h2><div className="type-brand">SCRUMCUT</div><p>Libre Baskerville · marca y títulos grandes</p><div className="type-ui">Gestión clara para decisiones precisas</div><p>Manrope · interfaz, tablas y cifras tabulares</p><h3>Escala de espacio</h3><div className="spacing">{[4,8,12,16,24,32,40,56,72].map(x=><i key={x} style={{width:x}}>{x}</i>)}</div></section>
 <section className="panel"><h2>Componentes</h2><div className="component-demo"><Button>Acción principal</Button><Button kind="secondary">Secundario</Button><Button kind="text">Texto</Button><div className="field"><label>Etiqueta del campo</label><div>Contenido del campo</div></div><div><Pill tone="positive">Confirmado</Pill> <Pill>En revisión</Pill></div><div className="notice">La información se guardó correctamente.</div><div className="skeleton"/><div className="skeleton short"/></div></section></div></>
}

function Admin({ close }: { close:()=>void }) {
 const groups = [['Barbería','Datos de la barbería','Sedes','Horarios de atención','Medios de pago'],['Equipo','Barberos','Usuarios y roles','Permisos por rol','Comisiones'],['Catálogo y precios','Servicios','Precios por sede','Productos y categorías','Insumos por servicio'],['Clientes y fiados','Niveles de cliente','Reglas de fiado','Recordatorios','Reseñas'],['Seguridad y datos','Auditoría','Seguridad de acceso','Datos personales · Ley 1581','Exportar información'],['Cuenta y plan','Plan y facturación','Integraciones','Textos legales','Soporte']]
 return <div className="overlay" onClick={close}><div className="admin" onClick={e=>e.stopPropagation()}><div className="admin-top"><h2>Administración</h2><button onClick={close}>×</button></div><div className="admin-body"><div className="admin-groups">{groups.map(g=><div key={g[0]}><h3>{g[0]}</h3>{g.slice(1).map(x=><button key={x}>{x}<span>›</span></button>)}</div>)}</div><aside><p className="eyebrow">ESTADO DE LA CUENTA</p><h3>Plan Profesional</h3><div className="facts"><span>Sedes activas<b>2 de 3</b></span><span>Usuarios activos<b>18</b></span><span>Próxima factura<b>1 jul. 2025</b></span></div><p className="eyebrow">ÚLTIMO CAMBIO</p><p>Laura Peña actualizó los permisos de Cajero.</p><small>Hoy, 10:42 a. m.</small></aside></div></div></div>
}
function Assistant({ close }: { close:()=>void }) {
 return <div className="assistant"><div className="assistant-head"><div><h2>Asistente</h2><p>Responde con los datos de tu barbería</p></div><button onClick={close}>×</button></div><div className="chat"><Pill>Disponible pronto</Pill><p className="bot">Hola, Laura. Puedo ayudarte a entender la operación de tus sedes.</p><p className="user">¿Cuánto vendí hoy?</p><p className="bot">Hoy llevas <b>$3.440.000</b> en ventas: Centro aportó $2.184.000 y Norte $1.256.000. Es un 12,4 % más que el miércoles anterior.</p></div><div className="suggestions">{['¿Cuánto vendí hoy?','¿Quién debe fiados vencidos?','¿Qué barbero vendió más?'].map(x=><button key={x}>{x}</button>)}</div><div className="composer"><span>Escribe tu pregunta</span><Button>Enviar</Button></div></div>
}

function CommandPalette({ close, go }: { close:()=>void; go:(page:string)=>void }) {
 const items = [
  [Users,'Buscar cliente','Santiago Mora, celular o documento','⌘ C','Clientes'],
  [ClipboardList,'Buscar comanda','Número, cliente o barbero','⌘ O','Comandas'],
  [Package,'Nueva comanda','Abrir una nueva atención','N','Comandas'],
  [CreditCard,'Cobro rápido','Registrar un cobro sin comanda','R','Caja'],
  [Search,'Buscar en todo ScrumCut','Configuración, reportes y acciones','/','Tablero'],
 ] as const
 return <div className="overlay command-overlay" onClick={close}><div className="command-palette" onClick={e=>e.stopPropagation()}>
  <div className="command-search"><Search size={19}/><input autoFocus placeholder="Buscar clientes, comandas y acciones…"/><kbd>ESC</kbd></div>
  <div className="command-list"><label>SUGERENCIAS</label>{items.map(([Icon,title,note,key,page])=><button key={title} onClick={()=>{go(page);close()}}><Icon size={18}/><span><b>{title}</b><small>{note}</small></span><kbd>{key}</kbd></button>)}</div>
  <footer><span><kbd>↑</kbd><kbd>↓</kbd> para navegar</span><span><kbd>↵</kbd> para abrir</span></footer>
 </div></div>
}

function Notifications({ close }: { close:()=>void }) {
 const groups = [
  ['HOY',[[Package,'Cera Matte Urban agotada','Sede Centro · hace 12 min'],[Boxes,'Stock bajo: After shave Proraso','3 unidades · hace 1 h'],[CreditCard,'Fiado vencido de Diego Vargas','$286.000 · hace 3 h']]],
  ['ANTERIORES',[[CalendarDays,'Producto próximo a vencer','Tónico Capilar · 28 oct. 2026'],[Banknote,'Cierre de caja con diferencia','Norte · ▾ −$8.000 · ayer']]],
 ] as const
 return <div className="notification-panel"><div className="notification-head"><div><h2>Notificaciones</h2><p>6 pendientes</p></div><button aria-label="Cerrar" onClick={close}><X size={18}/></button></div>{groups.map(([group,items])=><div className="notification-group" key={group}><label>{group}</label>{items.map(([Icon,title,note])=><button key={title}><span className="notification-icon"><Icon size={17}/></span><span><b>{title}</b><small>{note}</small></span><i/></button>)}</div>)}<button className="all-notifications">Ver todas las notificaciones</button></div>
}

function App() {
 const [dark,setDark]=useState(false), [page,setPage]=useState<Page>('Tablero'), [role,setRole]=useState<Role>('Dueño'), [admin,setAdmin]=useState(false), [assistant,setAssistant]=useState(false), [mobileNav,setMobileNav]=useState(false), [commands,setCommands]=useState(false), [notifications,setNotifications]=useState(false)
 const allowed = role==='Cajero' ? ['Tablero','Comandas','Caja','Clientes','Fiados'] : null
 const go=(x:string)=>{if(['Tablero','Comandas','Caja','Clientes','Fiados','Reportes','Sistema'].includes(x)){setPage(x as Page);setMobileNav(false)}}
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();setCommands(v=>!v)}if(e.key==='Escape'){setCommands(false);setNotifications(false)}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[])
 return <div className={dark?'app dark':'app'}>
   <header><button className="mobile-menu" onClick={()=>setMobileNav(!mobileNav)}><Command size={20}/></button><Logo/><div className="branch"><small>BARBERÍA</small><b>Distrito Barber Club</b></div><button className="selector">Todas las sedes <span>· vista consolidada</span>⌄</button><div className="top-actions"><button className="command-trigger" onClick={()=>setCommands(true)}><Search size={15}/><span>Buscar</span><kbd>Ctrl K</kbd></button><Button>+ Nuevo <kbd>N</kbd></Button><button className="icon-btn bell" aria-label="Notificaciones" onClick={()=>setNotifications(v=>!v)}><Bell size={19}/><i>6</i></button>{role==='Dueño'&&<Button kind="secondary" onClick={()=>setAdmin(true)}>Administración</Button>}<button className="theme-toggle" onClick={()=>setDark(!dark)} aria-label={dark?'Usar modo claro':'Usar modo oscuro'}>{dark?<Sun size={18}/>:<Moon size={18}/>}</button><button className="account"><span>LP</span><b>Laura Peña<small>{role}</small></b></button></div>{notifications&&<Notifications close={()=>setNotifications(false)}/>}</header>
   <aside className={`sidebar ${mobileNav?'open':''}`}><div className="mobile-logo"><Logo/></div><nav>{nav.map(([group,items])=><div key={group}><label>{group}</label>{items.map(([name,Icon])=>{const base=name.split(' ·')[0]; if(allowed&&!allowed.includes(base)) return null; return <button className={page===base?'active':''} onClick={()=>go(base)} key={name}><Icon size={18} strokeWidth={1.5}/>{base}{name.includes('Pronto')&&<Pill>Pronto</Pill>}</button>})}</div>)}</nav><div className="side-foot"><button onClick={()=>setAssistant(true)}><Sparkles size={18} strokeWidth={1.5}/><b>Asistente</b><span>›</span></button><small>ScrumCut · por ScrumTech Solutions</small></div></aside>
   <main>{page==='Tablero'?<Dashboard/>:page==='Comandas'?<Commandas/>:page==='Caja'?<Caja/>:page==='Clientes'?<Clients/>:page==='Fiados'?<Clients debt/>:page==='Sistema'?<System/>:<Dashboard/>}</main>
   <div className="role-switch"><span>Vista de rol</span><button className={role==='Dueño'?'active':''} onClick={()=>setRole('Dueño')}>Dueño</button><button className={role==='Cajero'?'active':''} onClick={()=>{setRole('Cajero');if(page==='Sistema')setPage('Tablero')}}>Cajero</button></div>
   {admin&&<Admin close={()=>setAdmin(false)}/>} {assistant&&<Assistant close={()=>setAssistant(false)}/>} {commands&&<CommandPalette close={()=>setCommands(false)} go={go}/>}
 </div>
}
export default App
