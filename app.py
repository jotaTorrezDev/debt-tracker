import os, sys, sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

BASE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
DB = os.path.join(BASE, "dividas.db")


def conectar():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS lancamentos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, pessoa TEXT NOT NULL,
        centavos INTEGER NOT NULL, data TEXT NOT NULL, validade TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS pagamentos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, pessoa TEXT NOT NULL,
        centavos INTEGER NOT NULL, data TEXT NOT NULL)""")
    cols = [c[1] for c in con.execute("PRAGMA table_info(lancamentos)")]
    if "pago_em" in cols:  # converte o "pago" da versão anterior em pagamentos
        con.execute("""INSERT INTO pagamentos(pessoa, centavos, data)
                       SELECT pessoa, centavos, pago_em FROM lancamentos WHERE pago_em IS NOT NULL""")
        con.execute("UPDATE lancamentos SET pago_em = NULL")
    con.commit()
    return con


def brl(c):
    s = f"{c / 100:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def parse_valor(txt):
    txt = txt.replace("R$", "").strip()
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    v = Decimal(txt)
    if v <= 0:
        raise InvalidOperation
    return int(v * 100)


def to_date(iso):
    return datetime.strptime(iso, "%Y-%m-%d").date()


def fmt_data(iso):
    return to_date(iso).strftime("%d/%m/%Y") if iso else "—"


def situacao(validade):
    if not validade:
        return "sem prazo", ""
    d = (to_date(validade) - date.today()).days
    if d < 0:
        return f"vencida há {-d} dia(s)", "atrasada"
    if d == 0:
        return "vence hoje", "atrasada"
    return f"vence em {d} dia(s)", ("aviso" if d <= 7 else "")


def criar_tree(parent, colunas):
    t = ttk.Treeview(parent, columns=[c[0] for c in colunas[1:]], show="tree headings", selectmode="browse")
    t.heading("#0", text=colunas[0][1])
    t.column("#0", width=colunas[0][2], anchor="w")
    for c, titulo, larg in colunas[1:]:
        t.heading(c, text=titulo)
        t.column(c, width=larg, anchor="w")
    t.tag_configure("pessoa", font=("Segoe UI", 10, "bold"), background="#e5e7eb")
    t.tag_configure("atrasada", foreground="#dc2626")
    t.tag_configure("aviso", foreground="#d97706")
    t.tag_configure("quitado", foreground="#15803d")
    return t


def carregar(con):
    """Agrupa por pessoa e distribui os pagamentos nas dívidas mais antigas primeiro."""
    pessoas = {}
    for i, p, c, d, v in con.execute("SELECT id, pessoa, centavos, data, validade FROM lancamentos "
                                     "ORDER BY pessoa COLLATE NOCASE, data, id"):
        pessoas.setdefault(p, {"l": [], "devido": 0, "pago": 0})
        pessoas[p]["l"].append({"id": i, "c": c, "data": d, "val": v})
        pessoas[p]["devido"] += c
    for p, tot in con.execute("SELECT pessoa, SUM(centavos) FROM pagamentos GROUP BY pessoa"):
        if p in pessoas:
            pessoas[p]["pago"] = tot
    for dados in pessoas.values():
        sobra = dados["pago"]
        for l in dados["l"]:
            l["quitado"] = min(sobra, l["c"])
            sobra -= l["quitado"]
            l["falta"] = l["c"] - l["quitado"]
        dados["falta"] = max(dados["devido"] - dados["pago"], 0)
    return pessoas


class App:
    def __init__(self, root):
        self.con = conectar()
        self.root = root
        root.title("Minhas Dívidas")
        root.geometry("960x640")
        root.minsize(800, 520)

        f = ttk.LabelFrame(root, text=" Nova dívida / somar valor a quem já devo ")
        f.pack(fill="x", padx=10, pady=10)
        for i, t in enumerate(("Nome", "Valor (R$)", "Validade (dd/mm/aaaa)")):
            ttk.Label(f, text=t).grid(row=0, column=i, sticky="w", padx=6)
        self.nome = ttk.Combobox(f, width=26)
        self.valor = ttk.Entry(f, width=14)
        self.validade = ttk.Entry(f, width=18)
        self.nome.grid(row=1, column=0, padx=6, pady=(0, 8))
        self.valor.grid(row=1, column=1, padx=6, pady=(0, 8))
        self.validade.grid(row=1, column=2, padx=6, pady=(0, 8))
        ttk.Button(f, text="➕ Adicionar / Somar", command=self.adicionar).grid(row=1, column=3, padx=6, pady=(0, 8))
        for w in (self.nome, self.valor, self.validade):
            w.bind("<Return>", lambda e: self.adicionar())

        abas = ttk.Notebook(root)
        abas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ---- aba 1: devendo ----
        a1 = ttk.Frame(abas); abas.add(a1, text="💸 Devendo")
        self.tree = criar_tree(a1, [("#0", "Pessoa", 170), ("valor", "Valor", 105), ("pago", "Já paguei", 105),
                                    ("falta", "Falta", 105), ("data", "Data", 85), ("venc", "Vencimento", 90),
                                    ("sit", "Situação", 190)])
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar)
        self.tree.bind("<Double-1>", lambda e: self.pagar())
        b1 = ttk.Frame(a1); b1.pack(fill="x", pady=8)
        ttk.Button(b1, text="💰 Registrar pagamento", command=self.pagar).pack(side="left")
        ttk.Button(b1, text="✅ Quitar tudo da pessoa", command=self.quitar).pack(side="left", padx=6)
        ttk.Button(b1, text="🗑 Excluir dívida", command=self.excluir).pack(side="left")
        self.mostrar_quitados = tk.BooleanVar(value=True)
        ttk.Checkbutton(b1, text="mostrar quitados", variable=self.mostrar_quitados,
                        command=self.atualizar).pack(side="left", padx=10)
        self.total = ttk.Label(b1, font=("Segoe UI", 12, "bold"), foreground="#b91c1c")
        self.total.pack(side="right")

        # ---- aba 2: resumo ----
        a2 = ttk.Frame(abas); abas.add(a2, text="📊 Resumo")
        self.l_devido = ttk.Label(a2, font=("Segoe UI", 12)); self.l_devido.pack(anchor="w", padx=10, pady=(12, 0))
        self.l_pago = ttk.Label(a2, font=("Segoe UI", 12), foreground="#15803d"); self.l_pago.pack(anchor="w", padx=10)
        self.l_falta = ttk.Label(a2, font=("Segoe UI", 14, "bold"), foreground="#b91c1c"); self.l_falta.pack(anchor="w", padx=10)
        self.barra = ttk.Progressbar(a2, maximum=100, length=500); self.barra.pack(anchor="w", padx=10, pady=6)
        self.l_msg = ttk.Label(a2, font=("Segoe UI", 11, "bold")); self.l_msg.pack(anchor="w", padx=10, pady=(0, 8))
        ttk.Label(a2, text="Mês a mês (para comparar com o mês anterior):").pack(anchor="w", padx=10)
        self.tree3 = criar_tree(a2, [("#0", "Mês", 100), ("novas", "Novas dívidas", 140),
                                     ("pagos", "Paguei no mês", 140), ("saldo", "Faltava no fim do mês", 190)])
        self.tree3.pack(fill="both", expand=True, padx=10, pady=8)

        # ---- aba 3: histórico de pagamentos ----
        a3 = ttk.Frame(abas); abas.add(a3, text="🧾 Pagamentos feitos")
        self.tree4 = criar_tree(a3, [("#0", "Pessoa", 200), ("valor", "Valor pago", 130), ("data", "Data", 110)])
        self.tree4.pack(fill="both", expand=True)
        b3 = ttk.Frame(a3); b3.pack(fill="x", pady=8)
        ttk.Button(b3, text="↩ Desfazer pagamento selecionado", command=self.desfazer).pack(side="left")
        self.total4 = ttk.Label(b3, font=("Segoe UI", 12, "bold"), foreground="#15803d"); self.total4.pack(side="right")
        self.atualizar()

    # ---------- telas ----------
    def atualizar(self):
        pessoas = carregar(self.con)
        self.tree.delete(*self.tree.get_children())
        geral_falta = 0
        for nome, d in pessoas.items():
            geral_falta += d["falta"]
            quitado = d["falta"] == 0
            if quitado and not self.mostrar_quitados.get():
                continue
            if quitado:
                sit = "✅ QUITADO"
            else:
                aberta = next(l for l in d["l"] if l["falta"] > 0)
                sit = f"devendo há {(date.today() - to_date(aberta['data'])).days} dia(s)"
            pid = self.tree.insert("", "end", iid=f"p:{nome}", text=nome, open=not quitado,
                                   tags=("pessoa", "quitado") if quitado else ("pessoa",),
                                   values=(brl(d["devido"]), brl(d["pago"]), brl(d["falta"]), "", "", sit))
            for l in d["l"]:
                if l["falta"] == 0:
                    txt, tag = "✅ quitado", "quitado"
                else:
                    txt, tag = situacao(l["val"])
                    if l["quitado"]:
                        txt = "parcial · " + txt
                self.tree.insert(pid, "end", iid=f"l:{l['id']}", text="",
                                 values=(brl(l["c"]), brl(l["quitado"]), brl(l["falta"]),
                                         fmt_data(l["data"]), fmt_data(l["val"]), txt),
                                 tags=(tag,) if tag else ())
        self.nome["values"] = list(pessoas)
        self.total.config(text=f"Ainda devo: {brl(geral_falta)}")

        devido = self.con.execute("SELECT COALESCE(SUM(centavos),0) FROM lancamentos").fetchone()[0]
        pago = self.con.execute("SELECT COALESCE(SUM(centavos),0) FROM pagamentos").fetchone()[0]
        self.l_devido.config(text=f"Total que já devi (somando tudo):  {brl(devido)}")
        self.l_pago.config(text=f"Já paguei:  {brl(pago)}")
        self.l_falta.config(text=f"Ainda falta pagar:  {brl(geral_falta)}")
        self.barra["value"] = min(100, pago * 100 / devido) if devido else 0
        if devido == 0:
            self.l_msg.config(text="Nenhuma dívida cadastrada.", foreground="#6b7280")
        elif geral_falta == 0:
            self.l_msg.config(text="🎉 TUDO QUITADO! Você não deve a ninguém.", foreground="#15803d")
        else:
            self.l_msg.config(text=f"{self.barra['value']:.0f}% pago — faltam {brl(geral_falta)}", foreground="#b45309")

        meses = {}
        for m, t in self.con.execute("SELECT substr(data,1,7), SUM(centavos) FROM lancamentos GROUP BY 1"):
            meses.setdefault(m, [0, 0])[0] = t
        for m, t in self.con.execute("SELECT substr(data,1,7), SUM(centavos) FROM pagamentos GROUP BY 1"):
            meses.setdefault(m, [0, 0])[1] = t
        self.tree3.delete(*self.tree3.get_children())
        acum = 0
        linhas = []
        for m in sorted(meses):
            novas, pagos = meses[m]
            acum += novas - pagos
            linhas.append((m, novas, pagos, acum))
        for m, novas, pagos, saldo in reversed(linhas):
            self.tree3.insert("", "end", text=f"{m[5:]}/{m[:4]}",
                              values=(brl(novas), brl(pagos), brl(max(saldo, 0))))

        self.tree4.delete(*self.tree4.get_children())
        for i, p, c, d in self.con.execute("SELECT id, pessoa, centavos, data FROM pagamentos ORDER BY data DESC, id DESC"):
            self.tree4.insert("", "end", iid=f"g:{i}", text=p, values=(brl(c), fmt_data(d)))
        self.total4.config(text=f"Total pago: {brl(pago)}")

    def pessoa_selecionada(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Atenção", "Clique numa pessoa (ou num valor dela) da lista primeiro.")
            return None
        iid = sel[0]
        return iid[2:] if iid.startswith("p:") else self.tree.item(self.tree.parent(iid), "text")

    def ao_selecionar(self, _):
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            self.nome.set(iid[2:] if iid.startswith("p:") else self.tree.item(self.tree.parent(iid), "text"))

    # ---------- ações ----------
    def adicionar(self):
        nome = self.nome.get().strip()
        if not nome:
            return messagebox.showwarning("Atenção", "Informe o nome da pessoa.")
        try:
            cent = parse_valor(self.valor.get())
        except (InvalidOperation, ValueError):
            return messagebox.showwarning("Atenção", "Valor inválido. Exemplo: 150,50")
        val = None
        if self.validade.get().strip():
            try:
                val = datetime.strptime(self.validade.get().strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                return messagebox.showwarning("Atenção", "Data inválida. Use dd/mm/aaaa. Exemplo: 25/12/2026")
        ex = self.con.execute("SELECT pessoa FROM lancamentos WHERE pessoa = ? COLLATE NOCASE LIMIT 1", (nome,)).fetchone()
        if ex:
            nome = ex[0]
        self.con.execute("INSERT INTO lancamentos(pessoa, centavos, data, validade) VALUES (?,?,?,?)",
                         (nome, cent, date.today().isoformat(), val))
        self.con.commit()
        self.nome.set(""); self.valor.delete(0, "end"); self.validade.delete(0, "end")
        self.atualizar()
        self.nome.focus()

    def registrar(self, nome, cent):
        self.con.execute("INSERT INTO pagamentos(pessoa, centavos, data) VALUES (?,?,?)",
                         (nome, cent, date.today().isoformat()))
        self.con.commit()
        self.atualizar()

    def pagar(self):
        nome = self.pessoa_selecionada()
        if not nome:
            return
        falta = carregar(self.con)[nome]["falta"]
        if falta == 0:
            return messagebox.showinfo("Quitado", f"Você já quitou tudo com {nome}. 🎉")
        txt = simpledialog.askstring("Registrar pagamento",
                                     f"Quanto você pagou a {nome}?\n(ainda falta {brl(falta)})",
                                     initialvalue=f"{falta / 100:.2f}".replace(".", ","), parent=self.root)
        if not txt:
            return
        try:
            cent = parse_valor(txt)
        except (InvalidOperation, ValueError):
            return messagebox.showwarning("Atenção", "Valor inválido. Exemplo: 150,50")
        if cent > falta:
            return messagebox.showwarning("Atenção", f"Esse valor é maior do que falta ({brl(falta)}).")
        self.registrar(nome, cent)

    def quitar(self):
        nome = self.pessoa_selecionada()
        if not nome:
            return
        falta = carregar(self.con)[nome]["falta"]
        if falta == 0:
            return messagebox.showinfo("Quitado", f"Você já quitou tudo com {nome}. 🎉")
        if messagebox.askyesno("Quitar", f"Registrar o pagamento de {brl(falta)} e quitar tudo com {nome}?"):
            self.registrar(nome, falta)

    def excluir(self):
        sel = self.tree.selection()
        if not sel or not sel[0].startswith("l:"):
            return messagebox.showinfo("Excluir", "Clique em um valor (linha de uma dívida) para excluir.")
        if messagebox.askyesno("Excluir", "Excluir esta dívida (cadastrada por engano)?"):
            self.con.execute("DELETE FROM lancamentos WHERE id=?", (sel[0][2:],))
            self.con.commit()
            self.atualizar()

    def desfazer(self):
        sel = self.tree4.selection()
        if not sel:
            return messagebox.showinfo("Desfazer", "Clique num pagamento da lista primeiro.")
        if messagebox.askyesno("Desfazer", "Desfazer este pagamento? A dívida volta a aparecer."):
            self.con.execute("DELETE FROM pagamentos WHERE id=?", (sel[0][2:],))
            self.con.commit()
            self.atualizar()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()