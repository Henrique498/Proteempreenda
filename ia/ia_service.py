import os
import pickle
from flask import Blueprint, request, jsonify
from deep_translator import GoogleTranslator
from .detector import analisar_texto

ia_bp = Blueprint('ia', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'modelo_river.pkl')

modelo_river = None


def carregar_modelo():
    global modelo_river
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                modelo_river = pickle.load(f)
            print(f"Modelo River carregado com sucesso a partir de: {MODEL_PATH}")
        except Exception as e:
            print(f"Erro ao carregar o modelo River: {e}")
    else:
        print(f"Arquivo '{MODEL_PATH}' não encontrado.")


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


@ia_bp.route('/api/ia/analisar', methods=['POST'])
def analisar_mensagem():
    data = request.get_json(silent=True) or {}
    texto = str(data.get('texto', '')).strip()

    if not texto:
        return jsonify({'error': 'O campo "texto" é obrigatório.'}), 400

    # Camada 1 — detector de palavras-chave em PT-BR
    resultado_detector = analisar_texto(texto)

    # Camada 2 — modelo Naive Bayes incremental (River)
    prob_predador = 0.0
    modelo_nome = 'Sem modelo (.pkl não encontrado)'

    if modelo_river is not None:
        try:
            texto_en = _traduzir_se_necessario(texto)
            probas = modelo_river.predict_proba_one(texto_en.lower())
            prob_predador = float(probas.get(True, 0.0))
            modelo_nome = 'River-MultinomialNB (com Tradução PT->EN)'
        except Exception as e:
            return jsonify({'error': f'Falha ao processar texto na IA: {str(e)}'}), 500

    nivel_ia = _nivel_river(prob_predador)

    # Filtro inteligente de decisão:
    # Se o detector não achou nada (score = 0) E a IA deu alerta moderado baixo (< 0.65), trata como seguro.
    # Caso contrário, se o detector encontrou termos de risco, prevalece o alerta do detector!
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


@ia_bp.route('/api/ia/aprender', methods=['POST'])
def aprender_mensagem():
    global modelo_river

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

        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(modelo_river, f)

        return jsonify({
            'sucesso': True,
            'mensagem': 'Novo aprendizado incorporado e salvo no modelo com sucesso!',
            'texto_processado': texto_en,
            'is_predator': bool(is_predator)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar o modelo: {str(e)}'}), 500