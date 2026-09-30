import { useEffect, useState } from "react";

const API = "http://localhost:5000/api";
const brl = (v) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const CATEGORIAS_DESPESA = [
  "Alimentação", "Gastos Fixos", "Contas", "Cartões de crédito",
  "Diversão", "Transporte", "Saúde", "Outros",
];
const CATEGORIAS_RENDA = ["Trabalho", "Investimentos", "Outros"];
const CORES = ["#0e6b55", "#b4432b", "#2f5fa7", "#c9962b", "#7a4fa0", "#2a9d9d", "#8a8f3a", "#6b7280"];
const corDe = (cat) => {
  const i = CATEGORIAS_DESPESA.indexOf(cat);
  return CORES[i < 0 ? CORES.length - 1 : i];
};

async function chamar(caminho, corpo, token) {
  const opcoes = { headers: {} };
  if (token) opcoes.headers.Authorization = `Bearer ${token}`;
  if (corpo) {
    opcoes.method = "POST";
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }
  let resposta;
  try {
    resposta = await fetch(`${API}${caminho}`, opcoes);
  } catch {
    throw new Error("Não consegui falar com o servidor. O api.py está rodando?");
  }
  const dados = await resposta.json();
  if (!resposta.ok) {
    const e = new Error(dados.erro || "Algo deu errado.");
    e.status = resposta.status;
    throw e;
  }
  return dados;
}

function Acesso({ aoEntrar }) {
  const [modo, setModo] = useState("login");
  const [campos, setCampos] = useState({ nome: "", email: "", senha: "" });
  const [mensagem, setMensagem] = useState("");

  const mudar = (e) => setCampos({ ...campos, [e.target.name]: e.target.value });

  async function enviar(e) {
    e.preventDefault();
    setMensagem("");
    try {
      aoEntrar(await chamar(modo === "login" ? "/login" : "/cadastro", campos));
    } catch (err) {
      setMensagem(err.message);
    }
  }

  return (
    <main className="acesso">
      <h1>Safe Finanças</h1>
      <p className="sub">Saiba para onde vai o seu dinheiro.</p>

      <div className="abas" role="tablist">
        <button role="tab" aria-selected={modo === "login"} onClick={() => setModo("login")}>
          Entrar
        </button>
        <button role="tab" aria-selected={modo === "cadastro"} onClick={() => setModo("cadastro")}>
          Criar conta
        </button>
      </div>

      <form onSubmit={enviar}>
        {modo === "cadastro" && (
          <label>
            Nome de usuário
            <input name="nome" value={campos.nome} onChange={mudar} autoComplete="username" />
          </label>
        )}
        <label>
          E-mail
          <input name="email" type="email" value={campos.email} onChange={mudar} autoComplete="email" />
        </label>
        <label>
          Senha
          <input name="senha" type="password" value={campos.senha} onChange={mudar} autoComplete="current-password" />
        </label>
        {mensagem && <p className="erro" role="alert">{mensagem}</p>}
        <button className="primario" type="submit">
          {modo === "login" ? "Entrar" : "Criar conta"}
        </button>
      </form>
    </main>
  );
}

function Rosca({ fatias, total }) {
  let acumulado = 0;
  return (
    <div className="rosca">
      <svg viewBox="0 0 42 42" role="img" aria-label="Gastos por categoria">
        <circle cx="21" cy="21" r="15.9155" fill="none" stroke="#e3e9e5" strokeWidth="6" />
        {fatias.map((f) => {
          const pct = (f.total / total) * 100;
          const circulo = (
            <circle key={f.categoria} cx="21" cy="21" r="15.9155" fill="none"
              stroke={corDe(f.categoria)} strokeWidth="6"
              strokeDasharray={`${pct} ${100 - pct}`} strokeDashoffset={25 - acumulado} />
          );
          acumulado += pct;
          return circulo;
        })}
      </svg>
      <div className="rosca-centro">
        <small>Total gasto</small>
        <b>{brl(total)}</b>
      </div>
    </div>
  );
}

function Painel({ usuario, aoSair }) {
  const [resumo, setResumo] = useState({ saldo: 0, transacoes: [] });
  const [form, setForm] = useState({ tipo: "Despesa", valor: "", descricao: "", categoria: CATEGORIAS_DESPESA[0] });
  const [filtro, setFiltro] = useState(null);
  const [mensagem, setMensagem] = useState("");

  const carregar = () =>
    chamar("/resumo", null, usuario.token)
      .then(setResumo)
      .catch((e) => (e.status === 401 ? aoSair() : setMensagem(e.message)));
  useEffect(() => { carregar(); }, []);

  const despesas = resumo.transacoes.filter((t) => t.tipo === "Despesa");
  const totalEntrou = resumo.transacoes.filter((t) => t.tipo === "Renda").reduce((s, t) => s + t.valor, 0);
  const totalGasto = despesas.reduce((s, t) => s + t.valor, 0);

  const porCategoria = Object.values(
    despesas.reduce((mapa, t) => {
      const c = mapa[t.categoria] || (mapa[t.categoria] = { categoria: t.categoria, total: 0, qtd: 0 });
      c.total += t.valor;
      c.qtd += 1;
      return mapa;
    }, {})
  ).sort((a, b) => b.total - a.total);

  const extrato = filtro
    ? resumo.transacoes.filter((t) => t.tipo === "Despesa" && t.categoria === filtro)
    : resumo.transacoes;

  const listaCategorias = form.tipo === "Renda" ? CATEGORIAS_RENDA : CATEGORIAS_DESPESA;
  const mudar = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  const trocarTipo = (tipo) =>
    setForm({ ...form, tipo, categoria: (tipo === "Renda" ? CATEGORIAS_RENDA : CATEGORIAS_DESPESA)[0] });

  async function salvar(e) {
    e.preventDefault();
    setMensagem("");
    try {
      await chamar("/transacoes", { ...form, valor: form.valor.replace(",", ".") }, usuario.token);
      setForm({ ...form, valor: "", descricao: "" });
      carregar();
    } catch (err) {
      setMensagem(err.message);
    }
  }

  return (
    <main className="painel">
      <header>
        <span>Olá, {usuario.nome}</span>
        <button className="link" onClick={aoSair}>Sair da conta</button>
      </header>

      <section className="saldo">
        <p>Saldo atual</p>
        <strong className={resumo.saldo < 0 ? "negativo" : ""}>{brl(resumo.saldo)}</strong>
        <div className="totais">
          <span>Entrou <b className="entrada">{brl(totalEntrou)}</b></span>
          <span>Saiu <b className="saida">{brl(totalGasto)}</b></span>
        </div>
      </section>

      <div className="colunas">
        <form className="nova" onSubmit={salvar}>
          <h2>Nova movimentação</h2>
          <div className="alternar">
            {["Despesa", "Renda"].map((t) => (
              <button type="button" key={t} className={form.tipo === t ? "ativo " + t : ""} onClick={() => trocarTipo(t)}>
                {t === "Renda" ? "Renda" : "Gasto"}
              </button>
            ))}
          </div>
          <label>
            Valor (R$)
            <input name="valor" inputMode="decimal" value={form.valor} onChange={mudar} placeholder="0,00" required />
          </label>
          <label>
            Descrição
            <input name="descricao" value={form.descricao} onChange={mudar}
              placeholder={form.tipo === "Renda" ? "Ex: Salário mensal" : "Ex: Mercado"} />
          </label>
          <label>
            Categoria
            <select name="categoria" value={form.categoria} onChange={mudar}>
              {listaCategorias.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          {mensagem && <p className="erro" role="alert">{mensagem}</p>}
          <button className="primario" type="submit">Salvar {form.tipo === "Renda" ? "renda" : "gasto"}</button>
        </form>

        <div className="direita">
          <section className="bloco">
            <h2>Gastos por categoria</h2>
            {porCategoria.length === 0 ? (
              <p className="vazio">Quando você registrar gastos, o gráfico e a tabela aparecem aqui.</p>
            ) : (
              <>
                <Rosca fatias={porCategoria} total={totalGasto} />
                <div className="rolagem">
                  <table>
                    <thead>
                      <tr><th>Categoria</th><th>Lançamentos</th><th>Total</th><th>% dos gastos</th></tr>
                    </thead>
                    <tbody>
                      {porCategoria.map((c) => {
                        const pct = (c.total / totalGasto) * 100;
                        return (
                          <tr key={c.categoria} className={filtro === c.categoria ? "selecionada" : ""}>
                            <td>
                              <button className="cat" onClick={() => setFiltro(filtro === c.categoria ? null : c.categoria)}>
                                <i style={{ background: corDe(c.categoria) }} />
                                {c.categoria}
                              </button>
                            </td>
                            <td>{c.qtd}</td>
                            <td>{brl(c.total)}</td>
                            <td>
                              <div className="barra"><span style={{ width: `${pct}%`, background: corDe(c.categoria) }} /></div>
                              {pct.toFixed(1).replace(".", ",")}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="dica">Clique numa categoria para ver só os gastos dela no extrato.</p>
              </>
            )}
          </section>

          <section className="bloco extrato">
            <h2>
              Extrato{filtro && <> · {filtro} <button className="link" onClick={() => setFiltro(null)}>Mostrar tudo</button></>}
            </h2>
            {extrato.length === 0 ? (
              <p className="vazio">Nenhuma movimentação ainda. Registre sua primeira renda ou gasto ao lado.</p>
            ) : (
              <ul>
                {extrato.map((t, i) => (
                  <li key={i}>
                    <div>
                      <b>{t.descricao}</b>
                      <small>{t.categoria} · {t.data}</small>
                    </div>
                    <span className={t.tipo === "Renda" ? "entrada" : "saida"}>
                      {t.tipo === "Renda" ? "+" : "−"} {brl(t.valor)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

export default function App() {
  const [usuario, setUsuario] = useState(() => {
    try { return JSON.parse(localStorage.getItem("usuario")); } catch { return null; }
  });

  const entrar = (dados) => {
    localStorage.setItem("usuario", JSON.stringify(dados));
    setUsuario(dados);
  };
  const sair = () => {
    if (usuario) chamar("/logout", {}, usuario.token).catch(() => {});
    localStorage.removeItem("usuario");
    setUsuario(null);
  };

  return usuario
    ? <Painel usuario={usuario} aoSair={sair} />
    : <Acesso aoEntrar={entrar} />;
}