from datetime import datetime

usuario_cadastrado = {
    "saldo": 0.0,
    "transacoes": []  # Lista para guardar o histórico de movimentações
}
logado = False


# --- FUNÇÕES DO SISTEMA ---
def registrar_transacao(tipo, valor, descricao, categoria):
    transacao = {
        "tipo": tipo,
        "valor": valor,
        "descricao": descricao,
        "categoria": categoria,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    usuario_cadastrado["transacoes"].append(transacao)


def exibir_extrato():
    print("\n================ EXTRATO DETALHADO ================")
    if not usuario_cadastrado["transacoes"]:
        print("Nenhuma movimentação registrada.")
    else:
        for t in usuario_cadastrado["transacoes"]:
            sinal = "+" if t["tipo"] == "Renda" else "-"
            print(f"[{t['data']}] {t['categoria']} - {t['descricao']}: {sinal}R$ {t['valor']:.2f}")
    print(f"\nSaldo Atual: R$ {usuario_cadastrado['saldo']:.2f}")
    print("==================================================")


# --- MENU INICIAL ---
print("Safe Finanças - Sistema de Gestão Financeira")
print("1 - Fazer Login")
print("2 - Criar Conta")

opcao = input("Escolha uma opção (1 ou 2): ")

if opcao == "2":
    print("\n--- CRIAR CONTA ---")
    nome = input("Digite seu nome de usuário: ")
    email = input("Digite seu e-mail: ")
    senha = input("Digite sua senha: ")
    
    usuario_cadastrado["nome"] = nome
    usuario_cadastrado["email"] = email
    usuario_cadastrado["senha"] = senha
    usuario_cadastrado["saldo"] = 0.0
    usuario_cadastrado["transacoes"] = []
    
    print("Conta criada com sucesso!")
    logado = True

elif opcao == "1":
    print("\n--- FAZER LOGIN ---")
    
    if "email" not in usuario_cadastrado:
        print("Nenhuma conta encontrada! Crie uma conta primeiro.")
    else:
        email_login = input("Digite seu e-mail: ")
        senha_login = input("Digite sua senha: ")
        
        if email_login == usuario_cadastrado["email"] and senha_login == usuario_cadastrado["senha"]:
            print(f"\nLogin realizado com sucesso! Bem-vindo(a), {usuario_cadastrado['nome']}!")
            logado = True
        else:
            print("E-mail ou senha incorretos!")


# --- PAINEL FINANCEIRO PROFISSIONAL ---
if logado:
    while True:
        print("\n=== PAINEL FINANCEIRO ===")
        print(f"Saldo Atual: R$ {usuario_cadastrado['saldo']:.2f}")
        print("1 - Registrar Salário / Renda")
        print("2 - Registrar Gasto / Despesa")
        print("3 - Ver Extrato Completo")
        print("4 - Sair da Conta")
        
        opcao_menu = input("Escolha uma opção: ")
        
        if opcao_menu == "1":
            valor = float(input("Digite o valor da renda: R$ "))
            descricao = input("Descrição (ex: Salário Mensal, Freela): ")
            categoria = input("Categoria (ex: Trabalho, Investimentos): ")
            
            usuario_cadastrado["saldo"] += valor
            registrar_transacao("Renda", valor, descricao, categoria)
            print("✓ Renda e histórico registrados com sucesso!")
            
        elif opcao_menu == "2":
            valor = float(input("Digite o valor do gasto: R$ "))
            descricao = input("Descrição (ex: O que foi comprado?): ")
            categoria = input("Categoria (ex: Alimentação, Moradia, Diversão...): ")
            
            usuario_cadastrado["saldo"] -= valor
            registrar_transacao("Despesa", valor, descricao, categoria)
            print("✓ Despesa e histórico registrados com sucesso!")
            
        elif opcao_menu == "3":
            exibir_extrato()
            
        elif opcao_menu == "4":
            print("A sair do sistema...")
            break
        else:
            print("Opção inválida!")