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
