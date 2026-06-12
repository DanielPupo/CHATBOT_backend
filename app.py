import sys

if sys.platform != "win32":
    try:
        from gevent import monkey
        monkey.patch_all()
    except ImportError:
        print("Gevent não instalado!")

from flask import Flask, request, session, jsonify
from flask_socketio import SocketIO, emit
from google import genai
from google.genai import types
from dotenv import load_dotenv
from uuid import uuid4
import os

# Carrega chaves privadas do ambiente
load_dotenv()

MODELO = "gemini-2.5-flash"

# PROMPT DE ALTO PADRÃO: A Alma e Inteligência da Pupo Parfums
instrucoes = """
Você é o renomado Haute Parfumeur e Sommelier Olfativo da "Pupo Parfums", uma Maison de alta perfumaria de nicho e luxuosa.
Sua missão é guiar os clientes a descobrirem suas assinaturas olfativas com recomendações exclusivas e extremamente diretas.
Aja como um somelier da perfumaria de alto padrão da europa, você é sofisticado, educado e respeitoso, sempre procurando e oferecendo a melhor experiência para os clientes, utilize de algumas, não muitas, palavras mais sofisticadas para demonstrar o seu alto conhecimento e classe!

Diretrizes Críticas de Personalidade e Formato:
1. Tom Exclusivo e Sucinto: Comporte-se como um embaixador elegante e refinado, porém altamente focado. Fale apenas o necessário para encantar o cliente sem desperdiçar o tempo dele.
2. Mensagens Curtas e Objetivas: Suas respostas devem ser breves, dinâmicas e de leitura rápida. Evite parágrafos longos ou introduções extensas. As pessoas hoje querem informações diretas e na hora.
3. Vocabulário Técnico Sem Enrolação: Indique as notas e conceitos essenciais ("projeção", "fixação", "notas de topo/coração/base") de forma pontual e polida. Use metáforas ricas com ingredientes nobres (ex: Oud cambojano, Rosa de Grasse), mas seja rápido na explicação.
4. Perfumes Reais e Sugestões Próximas: Indique SEMPRE perfumes reais existentes no mercado que se encaixem perfeitamente no clima (frio/calor), ambiente (reunião/balada) ou humor solicitado. Se não houver um idêntico, recomende fragrâncias de alta qualidade que sejam muito próximas e agradáveis para garantir a total satisfação.

Use a formatação markdown (negritos inteligentes) apenas para destacar os nomes dos perfumes e as notas principais, facilitando o escaneamento visual da mensagem.
"""

client = genai.Client(api_key=os.getenv("GENAI_KEY"))
app = Flask(__name__)
app.secret_key = "pupo_parfums_haute_couture_key"
socketio = SocketIO(app, cors_allowed_origins="*")
active_chats = {}

def get_user_chat():
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())

    session_id = session['session_id']

    if session_id not in active_chats:
        try:
            chat_session = client.chats.create(
                model=MODELO,
                config=types.GenerateContentConfig(system_instruction=instrucoes)
            )
            active_chats[session_id] = chat_session
        except Exception as e:
            app.logger.error(f"Erro ao criar chat Gemini para {session_id}: {e}", exc_info=True)
            raise  
    
    if session_id in active_chats and active_chats[session_id] is None:
        try:
            chat_session = client.chats.create(
                model=MODELO,
                config=types.GenerateContentConfig(system_instruction=instrucoes)
            )
            active_chats[session_id] = chat_session
        except Exception as e:
            app.logger.error(f"Erro ao recriar chat Gemini para {session_id}: {e}", exc_info=True)
            raise

    return active_chats[session_id]

@app.route('/')
def root():
    return jsonify({
        "maison": "Pupo Parfums",
        "status": "Atelier Operacional",
        "segmento": "Alta Perfumaria de Nicho"
    })

@socketio.on('connect')
def handle_connect():
    try:
        get_user_chat()
        user_session_id = session.get('session_id', 'N/A')
        emit('status_conexao', {'data': 'Conectado à Maison Pupo Parfums.', 'session_id': user_session_id})
    except Exception as e:
        app.logger.error(f"Erro no connect: {e}", exc_info=True)
        emit('erro', {'erro': 'O Atelier está temporariamente fechado para manutenção das essências.'})

@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    try:
        mensagem_usuario = data.get("mensagem")
        if not mensagem_usuario:
            emit('erro', {"erro": "A mensagem não pode ser vazia."})
            return

        user_chat = get_user_chat()
        if user_chat is None:
            emit('erro', {"erro": "Sessão perdida com o atelier olfativo."})
            return

        resposta_gemini = user_chat.send_message(mensagem_usuario)
        resposta_texto = (
            resposta_gemini.text
            if hasattr(resposta_gemini, 'text')
            else resposta_gemini.candidates[0].content.parts[0].text
        )
        
        emit('nova_mensagem', {"remetente": "bot", "texto": resposta_texto, "session_id": session.get('session_id')})

    except Exception as e:
        app.logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
        emit('erro', {"erro": "Houve uma interrupção na extração das notas. Por favor, tente enviar novamente."})

@socketio.on('disconnect')
def handle_disconnect():
    pass

if __name__ == "__main__":
    socketio.run(app)