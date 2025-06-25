# Passo 1: Imagem Base
# Começamos com uma imagem oficial do Python. A versão '3.11-slim' é leve e otimizada.
FROM python:3.11-slim

# Passo 2: Configurar o Ambiente de Trabalho
# Define o diretório de trabalho dentro do contêiner. Todos os comandos seguintes serão executados a partir daqui.
WORKDIR /app

# Passo 3: Copiar e Instalar as Dependências
# Copia o requirements.txt primeiro para aproveitar o cache do Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Passo 4: Copiar o Código da Aplicação
# Copia todos os outros arquivos (app.py, o certificado .pem) da sua pasta para o /app no contêiner.
COPY . .

# Passo 5: Expor a Porta
# Informa ao Docker que a aplicação dentro do contêiner irá rodar na porta 5000.
EXPOSE 5000

# Passo 6: Comando para Rodar a Aplicação
# Define o comando que será executado quando o contêiner iniciar.
# Usamos o 'gunicorn' como um servidor de produção.
# '--bind 0.0.0.0:5000' faz o servidor aceitar conexões de fora do contêiner.
# 'app:app' diz para o gunicorn encontrar o objeto 'app' dentro do arquivo 'app.py'.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]