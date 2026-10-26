// Nombres cortos para los esquemas generados. Ningún tipo de la API se define a mano: todos salen de schema.d.ts.
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Me = Schemas["Me"];
export type BranchState = Schemas["BranchState"];
export type BranchOption = Schemas["BranchOption"];
export type Navigation = Schemas["Navigation"];
export type NavGroup = Schemas["NavGroup"];
export type NavItem = Schemas["NavItem"];
export type Theme = Schemas["ThemeEnum"];
export type AlertItem = Schemas["AlertItem"];
export type Notifications = Schemas["Notifications"];
export type AdministrationSummary = Schemas["AdministrationSummary"];
export type Dashboard = Schemas["Dashboard"];
export type CalendarDay = Schemas["CalendarDay"];
export type CalendarWeek = Schemas["CalendarWeek"];
export type CashFlow = Schemas["CashFlow"];
export type OrderList = Schemas["OrderList"];
export type OrderRow = Schemas["OrderRow"];
export type OrderTab = Schemas["OrderTabEnum"];
export type OrderDetail = Schemas["OrderDetail"];
export type OrderLine = Schemas["OrderLine"];
export type OrderCatalog = Schemas["OrderCatalog"];
export type ClientChoice = Schemas["ClientChoice"];
export type Option = Schemas["Option"];
export type NewLine = Schemas["NewLineRequest"];
export type PaymentPart = Schemas["PaymentPartRequest"];
export type CheckoutRequest = Schemas["CheckoutRequest"];
export type CashState = Schemas["CashState"];
export type CashSession = Schemas["CashSession"];
export type CashMovement = Schemas["CashMovement"];
export type Closing = Schemas["Closing"];
export type Closings = Schemas["Closings"];
export type ManualKind = Schemas["ManualMovementRequest"]["kind"];
