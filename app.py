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

load_dotenv()

# Usando o modelo moderno e performático para interações de chat textuais
MODELO = "gemini-3.1-flash"

instrucoes = """
Você é o 'Sparky', o assistente virtual inteligente e companheiro da plataforma STEAM+ (Ciência, Tecnologia, Engenharia, Artes, Matemática e +).
Seu público-alvo é composto por alunos do 6º ao 8º ano do Ensino Fundamental II e seus respectivos professores. 
Toda a plataforma é gamificada com a temática de LEGO (avatares customizáveis, ganho de XP e conquista de Stickers de blocos).

Diretrizes Críticas de Personalidade e Formato:
1. Tom de Voz Adaptativo:
   - Se o usuário se identificar ou agir como ALUNO: Seja extremamente animado, motivador, use emojis de robôs/blocos (🤖, 🧱, 🚀) e linguagem amigável. Explique conceitos de robótica, circuitos ou lógica de programação de forma simples usando metáforas com peças de encaixe e Lego. Incentive o trabalho em equipe.
   - Se o usuário se identificar ou agir como PROFESSOR: Seja um parceiro de produtividade focado, profissional, polido e solícito. Ajude-o a otimizar a gestão de tempo, organização de equipes e metodologias ativas.

2. Respostas Objetivas e Escaneáveis:
   - Evite blocos massivos de texto. Use listas com marcadores e termos em negrito para facilitar a leitura rápida de alunos hiperconectados e professores ocupados.

3. Perguntas Frequentes da Base de Conhecimento:
   - ALUNOS perguntam sobre: Como ganhar XP e Stickers (fazendo tarefas e aguardando o professor avaliar/marcar como entregue); Como usar o XP (na lojinha de avatares para comprar acessórios LEGO); Ajuda com lógica de blocos (Scratch), montagem de protótipos ou circuitos elétricos em série/paralelo.
   - PROFESSORES perguntam sobre: Como criar e gerenciar grupos; Como aplicar autoavaliações e provas na plataforma; Como liberar os XPs e stickers (lembre-o de que o sistema distribui as recompensas automaticamente assim que ele atribui a nota e clica em "Marcar como Entregue").

Se o contexto inicial não deixar claro se o usuário é aluno ou professor, faça uma saudação amigável e pergunte educadamente quem está operando o painel para ajustar sua abordagem.
"""

client = genai.Client(api_key=os.getenv("GENAI_KEY"))
app = Flask(__name__)
app.secret_key = "steam_plus_lego_secret_super_key"
socketio = SocketIO(app, cors_allowed_origins="*")
active_chats = {}

def get_user_chat():
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())

    session_id = session['session_id']

    if session_id not in active_chats or active_chats[session_id] is None:
        try:
            chat_session = client.chats.create(
                model=MODELO,
                config=types.GenerateContentConfig(system_instruction=instrucoes)
            )
            active_chats[session_id] = chat_session
        except Exception as e:
            app.logger.error(f"Erro ao inicializar Sparky para {session_id}: {e}", exc_info=True)
            raise  

    return active_chats[session_id]

@app.route('/')
def root():
    return jsonify({
        "plataforma": "STEAM+",
        "modulo": "Assistente de Aprendizagem & Gestão",
        "avatar_tema": "LEGO Custom Build"
    })

@socketio.on('connect')
def handle_connect():
    try:
        get_user_chat()
        user_session_id = session.get('session_id', 'N/A')
        emit('status_conexao', {'data': 'Sparky inicializado com sucesso!', 'session_id': user_session_id})
    except Exception as e:
        app.logger.error(f"Erro ao conectar com Sparky: {e}", exc_info=True)
        emit('erro', {'erro': 'O Sparky está reiniciando seus blocos de memória. Tente em instantes.'})

@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    try:
        mensagem_usuario = data.get("mensagem")
        if not mensagem_usuario:
            emit('erro', {"erro": "Você não pode enviar um comando vazio."})
            return

        user_chat = get_user_chat()
        if user_chat is None:
            emit('erro', {"erro": "Conexão perdida com a central STEAM+."})
            return

        resposta_gemini = user_chat.send_message(mensagem_usuario)
        resposta_texto = (
            resposta_gemini.text
            if hasattr(resposta_gemini, 'text')
            else resposta_gemini.candidates[0].content.parts[0].text
        )
        
        emit('nova_mensagem', {"remetente": "bot", "texto": resposta_texto, "session_id": session.get('session_id')})

    except Exception as e:
        app.logger.error(f"Erro de processamento na mensagem: {e}", exc_info=True)
        emit('erro', {"erro": "Ocorreu uma falha ao conectar com o motor de IA. Tente reenviar."})

@socketio.on('disconnect')
def handle_disconnect():
    pass

if __name__ == "__main__":
    socketio.run(app)