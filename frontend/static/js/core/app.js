// Arranque de la interfaz: registra los componentes de Alpine (versión CSP) y lo inicia.
import Alpine from "../../vendor/alpinejs-csp-3.17.4.esm.min.js";
import accountMenu from "../components/account-menu.js";
import periodFilter from "../components/period-filter.js";
import shell from "../components/shell.js";

Alpine.data("shell", shell);
Alpine.data("accountMenu", accountMenu);
Alpine.data("periodFilter", periodFilter);
Alpine.start();
