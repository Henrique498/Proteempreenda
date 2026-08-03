import os
import pickle
from flask import Blueprint, request, jsonify

# 1. Cria o Blueprint da IA
ia_bp = Blueprint('ia', __name__)

# 2. Localiza o caminho do modelo modelo_river.pkl na mesma pasta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'modelo_river.pkl')

modelo_river = None

# Tenta carregar o modelo treinado em disco
if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, 'rb') as f:
            modelo_river = pickle.load(f)
        print(f"✅ Modelo River carregado com sucesso a partir de: {MODEL_PATH}")
    except Exception as e:
        print(f"⚠️ Erro ao carregar o modelo River: {e}")
else:
    print(f"ℹ️ Arquivo '{MODEL_PATH}' não encontrado. O endpoint responderá com valores padrão até o modelo ser gerado.")

# 3. Rota /api/ia/analisar que o Flutter (IAService) chama via POST
@ia_bp.route('/api/ia/analisar', methods=['POST'])
def analisar_mensagem():
    data = request.get_json(silent=True) or {}
    texto = str(data.get('texto', '')).strip()

    if not texto:
        return jsonify({'error': 'O campo "texto" é obrigatório.'}), 400

    # Se o modelo ainda não existe no servidor
    if modelo_river is None:
        return jsonify({
            'is_predator': False,
            'score_ia': 0.0,
            'modelo': 'Sem modelo (.pkl não encontrado)'
        }), 200

    try:
        # Predição usando a biblioteca River
        probas = modelo_river.predict_proba_one(texto)
        prob_predador = float(probas.get(True, 0.0))

        # Classifica como risco se a probabilidade for igual ou superior a 50%
        is_predator = prob_predador >= 0.5

        return jsonify({
            'is_predator': is_predator,
            'score_ia': round(prob_predador, 4),
            'modelo': 'River-MultinomialNB'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Falha ao processar texto na IA: {str(e)}'}), 500