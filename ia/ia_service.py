import os
import pickle
from flask import Blueprint, request, jsonify
from .detector import analisar_texto

ia_bp = Blueprint('ia', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'modelo_river.pkl')

modelo_river = None
if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, 'rb') as f:
            modelo_river = pickle.load(f)
        print(f"Modelo River carregado com sucesso a partir de: {MODEL_PATH}")
    except Exception as e:
        print(f"Erro ao carregar o modelo River: {e}")
else:
    print(f"Arquivo '{MODEL_PATH}' não encontrado.")

_ORDEM_RISCO = {'seguro': 0, 'atencao': 1, 'perigo': 2}


def _nivel_river(prob_predador: float) -> str:
    # Com o modelo balanceado, probabilidades acima de 0.25 já indicam atenção e acima de 0.55 perigo
    if prob_predador >= 0.55:
        return 'perigo'
    if prob_predador >= 0.25:
        return 'atencao'
    return 'seguro'


@ia_bp.route('/api/ia/analisar', methods=['POST'])
def analisar_mensagem():
    data = request.get_json(silent=True) or {}
    texto = str(data.get('texto', '')).strip()

    if not texto:
        return jsonify({'error': 'O campo "texto" é obrigatório.'}), 400

    # Camada 1 — detector de palavras-chave em PT-BR (baseado em regras)
    resultado_detector = analisar_texto(texto)

    # Camada 2 — modelo Naive Bayes incremental (River)
    prob_predador = 0.0
    modelo_nome = 'Sem modelo (.pkl não encontrado)'
    if modelo_river is not None:
        try:
            # Normaliza o texto para minúsculas antes de passar no pipeline
            texto_normalizado = texto.lower()
            probas = modelo_river.predict_proba_one(texto_normalizado)
            prob_predador = float(probas.get(True, 0.0))
            modelo_nome = 'River-MultinomialNB'
        except Exception as e:
            return jsonify({'error': f'Falha ao processar texto na IA: {str(e)}'}), 500

    nivel_ia = _nivel_river(prob_predador)

    # Combinação: o maior nível de risco entre Detector PT-BR e Modelo ML prevalece
    nivel_final = max(resultado_detector['nivel'], nivel_ia, key=lambda n: _ORDEM_RISCO[n])

    return jsonify({
        'nivel': nivel_final,
        'is_predator': nivel_final != 'seguro',
        'score_ia': round(prob_predador, 4),
        'score_palavras_chave': resultado_detector['pontuacao'],
        'categorias_detectadas': resultado_detector['categorias'],
        'modelo': modelo_nome,
    }), 200