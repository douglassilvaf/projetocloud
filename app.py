from datetime import datetime
from flask import Flask, request, jsonify
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date
# --- CONFIGURAÇÃO DA APLICAÇÃO E BANCO DE DADOS ---

app = Flask(__name__)

# Pega o caminho absoluto da pasta onde o app.py está.
# Isso garante que o caminho para o certificado funcione em qualquer computador.
basedir = os.path.abspath(os.path.dirname(__file__))

# Suas credenciais
DB_USERNAME = 'douglasdsilva'
DB_PASSWORD = 'Admin123'
DB_HOST = 'douglasserverbigproj.mysql.database.azure.com'
DB_NAME = 'projcloud'

# 1. REMOVEMOS o '?ssl_mode=REQUIRED' do final da URI.
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# 2. ADICIONAMOS esta nova configuração para passar as opções de SSL diretamente para o "motor" do SQLAlchemy.
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'ssl_ca': os.path.join(basedir, 'DigiCertGlobalRootG2.crt.pem')
    }
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa a extensão SQLAlchemy
db = SQLAlchemy(app)


# --- MODELOS (REPRESENTAÇÃO DAS TABELAS DO BANCO DE DADOS) ---

exposicao_obras = db.Table('exposicao_obras',
    db.Column('exposicao_id', db.Integer, db.ForeignKey('exposicao.id'), primary_key=True),
    db.Column('obra_id', db.Integer, db.ForeignKey('obra_de_arte.id'), primary_key=True)
)

# ... (classe ObraDeArte) ...

class Exposicao(db.Model):
    __tablename__ = 'exposicao'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data_inicio = db.Column(Date, nullable=False)
    data_fim = db.Column(Date, nullable=True)

    # Relacionamento muitos-para-muitos com ObraDeArte
    # 'secondary=exposicao_obras' informa ao SQLAlchemy para usar nossa tabela de associação.
    obras = db.relationship('ObraDeArte', secondary=exposicao_obras, lazy='subquery',
                            back_populates='exposicoes')

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'data_inicio': self.data_inicio.isoformat(),
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            # Inclui uma lista simplificada das obras na exposição
            'obras': [obra.to_dict_simple() for obra in self.obras]
        }

class Artista(db.Model):
    __tablename__ = 'artista'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    biografia = db.Column(db.Text, nullable=True)
    data_nascimento = db.Column(Date, nullable=False)

    def __repr__(self):
        return f'<Artista {self.nome}>'
    
    obras = db.relationship('ObraDeArte', back_populates='artista', lazy=True)

    def to_dict(self):
        """Converte o objeto Artista para um dicionário, útil para criar JSONs."""
        return {
            'id': self.id,
            'nome': self.nome,
            'biografia': self.biografia,
            # Converte o objeto data para uma string no formato 'Ano-Mês-Dia'
            'data_nascimento': self.data_nascimento.isoformat()
        }
    
class ObraDeArte(db.Model):
    __tablename__ = 'obra_de_arte'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data_criacao = db.Column(Date, nullable=False)
    imagem_url = db.Column(db.String(255), nullable=True) # Campo para a URL da imagem

    # Chave Estrangeira: vincula esta tabela à tabela 'artista'.
    # 'artista.id' refere-se à coluna 'id' da tabela 'artista'.
    artista_id = db.Column(db.Integer, db.ForeignKey('artista.id'), nullable=False)

    # Relacionamento reverso: permite fazer obra.artista para acessar o objeto Artista.
    artista = db.relationship('Artista', back_populates='obras')

    # Relacionamento muitos-para-muitos com Exposicao
    exposicoes = db.relationship('Exposicao', secondary=exposicao_obras, lazy='subquery', back_populates='obras')

    def to_dict(self):
        """Converte o objeto ObraDeArte para um dicionário."""
        return {
            'id': self.id,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'data_criacao': self.data_criacao.isoformat(),
            'imagem_url': self.imagem_url,
            'artista_id': self.artista_id,
            # Inclui o nome do artista no dicionário para facilitar a exibição.
            'nome_artista': self.artista.nome if self.artista else None
        }
    def to_dict_simple(self):
        """Converte para um dicionário mais simples, sem incluir as exposições."""
        return {
            'id': self.id,
            'titulo': self.titulo,
            'nome_artista': self.artista.nome if self.artista else None
        }

@app.route('/artistas', methods=['POST'])
def criar_artista():
    # Pega os dados JSON enviados na requisição.
    dados = request.get_json()

    # Verifica se todos os dados necessários foram enviados.
    if not dados or not 'nome' in dados or not 'data_nascimento' in dados:
        return jsonify({'mensagem': 'Erro: Dados incompletos. Nome e data de nascimento são obrigatórios.'}), 400

    # Cria uma nova instância do modelo Artista com os dados recebidos.
    # O .get('biografia', None) pega a biografia se ela existir, senão, define como None (nulo).
    novo_artista = Artista(
        nome=dados['nome'],
        biografia=dados.get('biografia'),
        data_nascimento=dados['data_nascimento']
    )

    # Adiciona o novo artista à sessão do banco de dados.
    db.session.add(novo_artista)
    # Efetiva (salva) as mudanças no banco de dados.
    db.session.commit()

    # Retorna uma mensagem de sucesso com o ID do novo artista.
    return jsonify({'mensagem': 'Artista cadastrado com sucesso!', 'id_artista': novo_artista.id}), 201

# ROTA PARA LISTAR TODOS OS ARTISTAS
@app.route('/artistas', methods=['GET'])
def get_artistas():
    # Pega todos os registros da tabela 'artista'.
    artistas = Artista.query.all()
    # Converte cada objeto 'artista' para um dicionário usando a função to_dict e cria uma lista.
    lista_de_artistas = [artista.to_dict() for artista in artistas]
    return jsonify(lista_de_artistas), 200

# ROTA PARA BUSCAR UM ARTISTA ESPECÍFICO PELO ID
@app.route('/artistas/<int:id>', methods=['GET'])
def get_artista_por_id(id):
    # Busca um artista pelo seu ID. Se não encontrar, retorna um erro 404 (Not Found) automaticamente.
    artista = Artista.query.get_or_404(id)
    return jsonify(artista.to_dict()), 200

# ROTA PARA ATUALIZAR UM ARTISTA EXISTENTE
@app.route('/artistas/<int:id>', methods=['PUT'])   
def atualizar_artista(id):
    artista = Artista.query.get_or_404(id)
    dados = request.get_json()

    if not dados:
        return jsonify({'mensagem': 'Erro: Nenhum dado enviado.'}), 400

    if 'nome' in dados:
        artista.nome = dados['nome']
    if 'biografia' in dados:
        artista.biografia = dados['biografia']
    if 'data_nascimento' in dados:
        artista.data_nascimento = dados['data_nascimento']

    db.session.commit()
    return jsonify({'mensagem': 'Artista atualizado com sucesso!', 'artista': artista.to_dict()}), 200

# ROTA PARA DELETAR UM ARTISTA
@app.route('/artistas/<int:id>', methods=['DELETE'])
def deletar_artista(id):
    artista = Artista.query.get_or_404(id)
    db.session.delete(artista)
    db.session.commit()
    return jsonify({'mensagem': 'Artista deletado com sucesso!'}), 204
# --- ROTAS (ENDPOINTS DA API)   ---

@app.route('/')
def index():
    return "Modelo 'Artista' definido. Próximo passo: criar a tabela no banco de dados."

# --- ROTAS PARA OBRAS DE ARTE ---

# ROTA PARA CADASTRAR UMA NOVA OBRA DE ARTE
# Substitua a função criar_obra_de_arte por esta versão final e robusta:
@app.route('/obras', methods=['POST'])
def criar_obra_de_arte():
    dados = request.get_json()

    if isinstance(dados, list):
        obras_a_processar = dados
    else:
        obras_a_processar = [dados]

    obras_criadas = []
    erros = [] # Lista para guardar as obras que falharam e o motivo.

    # Itera sobre cada item da lista.
    for obra_dados in obras_a_processar:
        # 1. Validação de dados incompletos
        if not obra_dados or not all(k in obra_dados for k in ('titulo', 'data_criacao', 'artista_id')):
            erros.append({'dados_recebidos': obra_dados, 'erro': 'Dados incompletos.'})
            continue # Pula para o próximo item

        # 2. Validação da existência do artista
        artista = Artista.query.get(obra_dados['artista_id'])
        if not artista:
            erros.append({'dados_recebidos': obra_dados, 'erro': f"Artista com id {obra_dados['artista_id']} não encontrado."})
            continue # Pula para o próximo item
        
        # Se passou em todas as validações, cria a nova obra
        nova_obra = ObraDeArte(
            titulo=obra_dados['titulo'],
            descricao=obra_dados.get('descricao'),
            data_criacao=obra_dados['data_criacao'],
            imagem_url=obra_dados.get('imagem_url'),
            artista_id=obra_dados['artista_id']
        )
        
        db.session.add(nova_obra)
        obras_criadas.append(nova_obra)

    # Se ao menos uma obra foi processada corretamente, salva no banco.
    if obras_criadas:
        db.session.commit()

    # Monta a resposta final
    resposta = {
        'mensagem': f"Processamento concluído. {len(obras_criadas)} obra(s) criada(s), {len(erros)} com erro."
    }
    if obras_criadas:
        resposta['criadas'] = [obra.to_dict() for obra in obras_criadas]
    if erros:
        resposta['erros'] = erros

    # Define o código de status: 201 se tudo foi criado, 207 (Multi-Status) se houve sucessos e falhas.
    status_code = 201 if not erros else 207

    return jsonify(resposta), status_code

# ROTA PARA LISTAR TODAS AS OBRAS DE ARTE
@app.route('/obras', methods=['GET'])
def get_obras():
    # Pega todos os registros da tabela 'obra_de_arte'.
    obras = ObraDeArte.query.all()
    # Usa a função to_dict() que já criamos em cada objeto para converter para uma lista de dicionários.
    return jsonify([obra.to_dict() for obra in obras]), 200

# ROTA PARA BUSCAR UMA OBRA DE ARTE ESPECÍFICA PELO ID
@app.route('/obras/<int:id>', methods=['GET'])
def get_obra_por_id(id):
    # Busca uma obra pelo seu ID. Se não encontrar, retorna um erro 404 (Not Found).
    obra = ObraDeArte.query.get_or_404(id)
    return jsonify(obra.to_dict()), 200

# ROTA PARA ATUALIZAR UMA OBRA DE ARTE EXISTENTE
@app.route('/obras/<int:id>', methods=['PUT'])
def atualizar_obra(id):
    obra = ObraDeArte.query.get_or_404(id)
    dados = request.get_json()

    if not dados:
        return jsonify({'mensagem': 'Erro: Nenhum dado enviado.'}), 400

    if 'titulo' in dados:
        obra.titulo = dados['titulo']
    if 'descricao' in dados:
        obra.descricao = dados['descricao']
    if 'data_criacao' in dados:
        try:
            # Tenta converter a string para um objeto de data
            data_convertida = datetime.strptime(dados['data_criacao'], '%Y-%m-%d').date()
            obra.data_criacao = data_convertida
        except ValueError:
            # Se o formato for inválido, retorna um erro claro.
            return jsonify({'mensagem': 'Erro: Formato de data inválido. Use AAAA-MM-DD.'}), 400
    if 'imagem_url' in dados:
        obra.imagem_url = dados['imagem_url']
    if 'artista_id' in dados:
        artista = Artista.query.get(dados['artista_id'])
        if not artista:
            return jsonify({'mensagem': f"Artista com id {dados['artista_id']} não encontrado."}), 400
        obra.artista_id = dados['artista_id']

    db.session.commit()
    return jsonify({'mensagem': 'Obra de arte atualizada com sucesso!', 'obra': obra.to_dict()}), 200

# ROTA PARA DELETAR UMA OBRA DE ARTE
@app.route('/obras/<int:id>', methods=['DELETE'])
def deletar_obra(id):
    obra = ObraDeArte.query.get_or_404(id)
    db.session.delete(obra)
    db.session.commit()
    return '', 204

# --- ROTAS PARA EXPOSIÇÕES ---

@app.route('/exposicoes', methods=['POST'])
def criar_exposicao():
    dados = request.get_json()

    if not dados or not all(k in dados for k in ('nome', 'data_inicio')):
        return jsonify({'mensagem': 'Erro: Nome e data de início são obrigatórios.'}), 400

    # Cria o objeto da exposição com os dados básicos
    nova_exposicao = Exposicao(
        nome=dados['nome'],
        descricao=dados.get('descricao'),
        data_inicio=dados['data_inicio'],
        data_fim=dados.get('data_fim')
    )

    # Verifica se foram enviados IDs de obras para associar
    if 'obras_ids' in dados and isinstance(dados['obras_ids'], list):
        # Itera sobre a lista de IDs de obras
        for obra_id in dados['obras_ids']:
            # Busca a obra no banco de dados
            obra = ObraDeArte.query.get(obra_id)
            # Se a obra existir, adiciona à lista de obras da exposição
            if obra:
                nova_exposicao.obras.append(obra)

    # Adiciona a nova exposição (com as obras já vinculadas) à sessão
    db.session.add(nova_exposicao)
    # Salva no banco. SQLAlchemy irá inserir na tabela 'exposicao' e na 'exposicao_obras'.
    db.session.commit()

    return jsonify({'mensagem': 'Exposição criada com sucesso!', 'exposicao': nova_exposicao.to_dict()}), 201

# --- EXECUÇÃO DA APLICAÇÃO ---

if __name__ == '__main__':
    app.run(debug=True)