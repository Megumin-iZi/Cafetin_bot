# bot.py
import os
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")   # <-- aquí pegarás tu token de BotFather
DB_PATH = "cafetin.db"

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY,
                codigo TEXT UNIQUE,
                nombre TEXT,
                telefono TEXT,
                limite REAL,
                saldo REAL DEFAULT 0
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY,
                cliente_id INTEGER,
                tipo TEXT,          -- 'fiado' o 'pago'
                monto REAL,
                concepto TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Uso: /registrar Nombre Telefono Limite")
        return
    nombre = args[0]
    telefono = args[1]
    try:
        limite = float(args[2])
    except:
        await update.message.reply_text("Límite debe ser número")
        return
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT COUNT(*) FROM clientes")
        num = con.fetchone()[0] + 1
        codigo = f"{num:03d}"
        con.execute(
            "INSERT INTO clientes (codigo, nombre, telefono, limite, saldo) VALUES (?,?,?,?,0)",
            (codigo, nombre, telefono, limite)
        )
    await update.message.reply_text(
        f"✅ Cliente registrado\n"
        f"Código: {codigo}\n"
        f"Nombre: {nombre}\n"
        f"Límite: S/ {limite:.2f}"
    )

async def fiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Uso: /fiar Codigo Monto Concepto")
        return
    codigo = args[0]
    monto = float(args[1])
    concepto = " ".join(args[2:])
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id, saldo, limite FROM clientes WHERE codigo=?", (codigo,))
        row = con.fetchone()
        if not cli:
            await update.message.reply_text("Cliente no encontrado")
            return
        cid, saldo, limite = cli
        if saldo + monto > limite:
            await update.message.reply_text(f"❌ Excede límite (S/ {limite:.2f})")
            return
        con.execute("UPDATE clientes SET saldo = saldo + ? WHERE id=?", (monto, cid))
        con.execute("INSERT INTO movimientos (cliente_id, tipo, monto, concepto) VALUES (?, 'fiado', ?, ?)", (cid, monto, " ".join(args[2:])))
    await update.message.reply_text(f"✅ Fiado registrado\nCliente: {codigo}\nMonto: S/ {monto:.2f}\nConcepto: {args[2:]}")

async def pagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /pagar Codigo Monto [metodo]")
        return
    codigo = args[0]
    monto = float(args[1])
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id, saldo FROM clientes WHERE codigo=?", (codigo,))
        row = con.fetchone()
        if not cli:
            await update.message.reply_text("Cliente no existe")
            return
        cid, saldo = cli
        if monto > saldo:
            await update.message.reply_text(f"❌ Pago excede deuda (S/ {saldo:.2f})")
            return
        con.execute("UPDATE clientes SET saldo = saldo - ? WHERE id=?", (monto, cid))
        con.execute("INSERT INTO movimientos (cliente_id, tipo, monto, concepto) VALUES (?, 'pago', ?, ?)", (cid, monto, "pago"))
    await update.message.reply_text(f"✅ Pago registrado\nCliente: {codigo}\nMonto: S/ {monto:.2f}")

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /saldo Codigo")
        return
    codigo = args[0]
    with sqlite3.connect(DB_PATH) as con:
        cli = con.execute("SELECT nombre, saldo, limite FROM clientes WHERE codigo=?", (codigo,)).fetchone()
        if not cli:
            await update.message.reply_text("Cliente no existe")
            return
        nombre, saldo, limite = cli
        await update.message.reply_text(
            f"💳 {nombre} ({codigo})\n"
            f"Deuda: S/ {saldo:.2f}\n"
            f"Límite: S/ {limite:.2f}\n"
            f"Disponible: S/ {limite - saldo:.2f}"
        )

async def deudores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute("SELECT codigo, nombre, saldo FROM clientes WHERE saldo > 0 ORDER BY saldo DESC").fetchall()
        if not rows:
            await update.message.reply_text("✅ No hay deudores")
            return
        txt = "📋 DEUDORES:\n" + "\n".join(f"{c} - {n}: S/ {s:.2f}" for c, n, s in rows)
        await update.message.reply_text(txt)

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📋 COMANDOS:
/registrar Nombre Telefono Limite
/fiar Codigo Monto Concepto
/pagar Codigo Monto [metodo]
/saldo Codigo
/deudores
/ayuda""", parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("registrar", registrar))
    app.add_handler(CommandHandler("fiar", fiar))
    app.add_handler(CommandHandler("pagar", pagar))
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("deudores", deudores))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.run_polling()

if __name__ == "__main__":
    main()