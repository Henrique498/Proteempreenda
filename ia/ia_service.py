import os
import pickle
from flask import Blueprint, request, jsonify, g
from deep_translator import GoogleTranslator

from auth import require_auth
from subscription import usuario_tem_plano_pago_ativo
from .detector import analisar_texto
from .model_store import carregar_modelo_do_banco, salvar_modelo_no_banco

ia_bp = Blueprint('ia', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'modelo_river.pkl')  # só usado como semente inicial

modelo_river = None


def carregar_modelo():
    """
    Ordem de carregamento:
    1. Banco (Supabase) — fonte da verdade, sobrevive a redeploy.
    2. Arquivo local versionado no git — só na primeiríssima vez,
       quando o banco ainda não tem nenhum modelo salvo.
    """
    global modelo_river

    try:
        modelo_river = carregar_modelo_do_banco()
        if modelo_river is not None:
            print("Modelo River carregado do banco de dados (Supabase).")
            return
    except Exception as e:
        print(f"Aviso: falha ao carregar modelo do banco: {e}")

    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                modelo_river = pickle.load(f)
            print(f"Modelo local carregado a partir de: {MODEL_PATH}")
            salvar_modelo_no_banco(modelo_river)
            print("Modelo local salvo no banco pela primeira vez.")
        except Exception as e:
            print(f"Erro ao carregar o modelo local: {e}")
    else:
        print(f"Nenhum modelo encontrado (nem banco, nem {MODEL_PATH}).")


carregar_modelo()

_ORDEM_RISCO = {'seguro': 0, 'atencao': 1, 'perigo': 2}


def _nivel_river(prob_predador: float) -> str:
    if prob_predador >= 0.75:
        return 'perigo'
    if prob_predador >= 0.45:
        return 'atencao'
    return 'seguro'


def _traduzir_se_necessario(texto: str) -> str:
    try:
        traducao = GoogleTranslator(source='auto', target='en').translate(texto)
        return traducao if traducao else texto
    except Exception as e:
        print(f"Aviso de tradução: {e}. Usando texto original.")
        return texto


# ── Testar mensagem — precisa estar logado, mas NÃO precisa de plano pago ──
@ia_bp.route('/api/ia/analisar', methods=['POST'])
@require_auth
def analisar_mensagem():
    data = request.get_json(silent=True) or {}
    texto = str(data.get('texto', '')).strip()

    if not texto:
        return jsonify({'error': 'O campo "texto" é obrigatório.'}), 400

    resultado_detector = analisar_texto(texto)

    prob_predador = 0.0
    modelo_nome = 'Sem modelo carregado'

    if modelo_river is not None:
        try:
            #texto_en = _traduzir_se_necessario(texto)
            #probas = modelo_river.predict_proba_one(texto_en.lower())
            probas = modelo_river.predict_proba_one(texto.lower())
            prob_predador = float(probas.get(True, 0.0))
            modelo_nome = 'River-MultinomialNB (com Tradução PT->EN)'
        except Exception as e:
            print(f"!!! ERRO NA ANALISE IA: {str(e)}")
            import traceback; traceback.print_exc()
            return jsonify({'error': f'Falha ao processar texto na IA: {str(e)}'}), 500

    nivel_ia = _nivel_river(prob_predador)

    if resultado_detector['pontuacao'] == 0 and nivel_ia == 'atencao' and prob_predador < 0.65:
        nivel_final = 'seguro'
    else:
        nivel_final = max(resultado_detector['nivel'], nivel_ia, key=lambda n: _ORDEM_RISCO[n])

    return jsonify({
        'nivel': nivel_final,
        'is_predator': nivel_final != 'seguro',
        'score_ia': round(prob_predador, 4),
        'score_palavras_chave': resultado_detector['pontuacao'],
        'categorias_detectadas': resultado_detector['categorias'],
        'modelo': modelo_nome,
    }), 200


# ── Ensinar o modelo — precisa de plano pago (Básico, Premium ou Escola) ──
@ia_bp.route('/api/ia/aprender', methods=['POST'])
@require_auth
def aprender_mensagem():
    global modelo_river

    if not usuario_tem_plano_pago_ativo(g.user_id):
        return jsonify({
            'error': 'Esse recurso é exclusivo para assinantes (plano Básico ou superior).'
        }), 403

    data = request.get_json(silent=True) or {}
    texto = str(data.get('texto', '')).strip()
    is_predator = data.get('is_predator')

    if not texto or is_predator is None:
        return jsonify({'error': 'Envie os campos "texto" (string) e "is_predator" (boolean).'}), 400

    if modelo_river is None:
        return jsonify({'error': 'Modelo de IA não carregado.'}), 500

    try:
        texto_en = _traduzir_se_necessario(texto).lower()
        modelo_river.learn_one(texto_en, bool(is_predator))

        # Persiste no Supabase — sobrevive a redeploy do Render.
        salvar_modelo_no_banco(modelo_river)

        return jsonify({
            'sucesso': True,
            'mensagem': 'Novo aprendizado incorporado e salvo no banco com sucesso!',
            'texto_processado': texto_en,
            'is_predator': bool(is_predator),
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar o modelo: {str(e)}'}), 500