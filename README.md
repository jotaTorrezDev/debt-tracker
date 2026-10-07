# Minhas Dívidas

Aplicativo para Windows para organizar dívidas e acompanhar pagamentos por pessoa. Os valores são exibidos em reais, e os dados ficam salvos em um banco SQLite local.

## Recursos

- Cadastro de dívidas com valor, pessoa e data de vencimento opcional.
- Registro de pagamentos parciais ou quitação do saldo.
- Lista de dívidas em aberto, pagas e vencidas.
- Resumo dos valores devidos, pagos e restantes.
- Histórico mensal e lista de pagamentos, com opção para desfazer um pagamento.

## Como executar

ter Python 3 instalado. Na pasta do projeto, execute:

```bat
python app.py
```

No Windows, também é possível abrir `Minhas Dividas.bat`.

## Gerar o executável

Com Python instalado, execute `criar_exe.bat`. O script instala o PyInstaller e gera `MinhasDividas.exe` na pasta do projeto.

## Dados

O aplicativo cria o arquivo `dividas.db` na mesma pasta de onde está sendo executado. Esse banco contém os registros de dívidas e pagamentos; faça uma cópia de segurança para preservar seus dados.

O banco de dados e o executável não são incluídos no Git. Ao baixar o projeto em outro computador, o aplicativo cria um banco vazio na primeira execução.
