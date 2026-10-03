/**
 * Identificador aleatório (UUID v4) para chaves de idempotência. Não é segredo: serve só
 * para o servidor reconhecer o reenvio da mesma gravação, então `Math.random` basta.
 */
export function newRequestId(): string {
  const hex = "0123456789abcdef";
  let out = "";
  for (let index = 0; index < 36; index += 1) {
    if (index === 8 || index === 13 || index === 18 || index === 23) {
      out += "-";
    } else if (index === 14) {
      out += "4";
    } else if (index === 19) {
      out += hex[8 + Math.floor(Math.random() * 4)];
    } else {
      out += hex[Math.floor(Math.random() * 16)];
    }
  }
  return out;
}
