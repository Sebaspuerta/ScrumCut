// Lo que dice cada pantalla de pérdida de acceso. El estado y la barbería (siempre la propia) los decide la API.
import type { Access } from "../api/types";

export interface AccessCopy {
  title: string;
  body: string;
}

const OTHER_ACCOUNT = "cierra sesión e inicia con otra cuenta.";

function contact(access: Access): string {
  return access.support_email
    ? `Escríbenos a ${access.support_email} para resolverlo, o ${OTHER_ACCOUNT}`
    : `Habla con el dueño de la barbería, o ${OTHER_ACCOUNT}`;
}

function severalBody(access: Access): string {
  const body = "Tu cuenta tiene acceso a varias barberías y todavía no puedes elegir con cuál trabajar.";
  return access.support_email ? `${body} Escríbenos a ${access.support_email} y lo resolvemos.` : body;
}

export function accessCopy(access: Access): AccessCopy {
  const shop = access.barbershop ?? "tu barbería";
  switch (access.status) {
    case "membership_inactive":
      return {
        title: `Ya no tienes acceso a ${shop}`,
        body: `Si es un error, pídele al dueño que te lo devuelva, o ${OTHER_ACCOUNT}`,
      };
    case "barbershop_suspended":
      return { title: `El acceso a ${shop} está suspendido`, body: contact(access) };
    case "barbershop_closed":
      return { title: `${shop} cerró su cuenta en ScrumCut`, body: contact(access) };
    case "several_barbershops":
      return { title: "Tienes acceso a varias barberías", body: severalBody(access) };
    default:
      return {
        title: "Tu cuenta no tiene una barbería",
        body: `Pídele al dueño de la barbería que te invite, o ${OTHER_ACCOUNT}`,
      };
  }
}
