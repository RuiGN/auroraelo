"""Servidor SMTP mínimo que guarda cada mensagem recebida em um arquivo JSON por linha.

Só para o roteiro ponta a ponta: o servidor Django envia e-mail de verdade por SMTP
(para esta porta) e o teste lê o código de convite/recuperação da mensagem recebida.

    python smtp_sink.py <porta> <arquivo.jsonl>
"""
import asyncio
import email
import json
import sys
from email import policy


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, out: str) -> None:
    async def say(line: str) -> None:
        writer.write((line + "\r\n").encode())
        await writer.drain()

    await say("220 sink ESMTP")
    sender, recipients = "", []
    while True:
        raw = await reader.readline()
        if not raw:
            break
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        verb = line.split(" ", 1)[0].upper()
        if verb in ("EHLO", "HELO"):
            await say("250 sink")
        elif verb == "MAIL":
            sender, recipients = line.split(":", 1)[1].strip(), []
            await say("250 ok")
        elif verb == "RCPT":
            recipients.append(line.split(":", 1)[1].strip().strip("<>"))
            await say("250 ok")
        elif verb == "DATA":
            await say("354 end with <CR><LF>.<CR><LF>")
            chunks = []
            while True:
                part = await reader.readline()
                if part in (b".\r\n", b".\n", b""):
                    break
                chunks.append(part[1:] if part.startswith(b"..") else part)
            message = email.message_from_bytes(b"".join(chunks), policy=policy.default)
            body = message.get_body(preferencelist=("plain", "html"))
            with open(out, "a", encoding="utf-8") as handle_out:
                handle_out.write(
                    json.dumps(
                        {
                            "from": sender,
                            "to": recipients,
                            "subject": str(message["Subject"]),
                            "body": body.get_content() if body else "",
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            await say("250 queued")
        elif verb == "RSET":
            await say("250 ok")
        elif verb == "NOOP":
            await say("250 ok")
        elif verb == "QUIT":
            await say("221 bye")
            break
        else:
            await say("502 not implemented")
    writer.close()


async def main(port: int, out: str) -> None:
    server = await asyncio.start_server(lambda r, w: handle(r, w, out), "127.0.0.1", port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), sys.argv[2]))
