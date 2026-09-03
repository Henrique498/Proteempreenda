import os
import pickle
from flask import Blueprint, request, jsonify, g

from auth import require_auth
from subscription import usuario_tem_plano_pago_ativo
from .detector import analisar_texto
from .model_store import carregar_modelo_do_banco, salvar_modelo_no_banco

ia_bp = Blueprint("ia", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "modelo_river.pkl")  # só usado como semente inicial

modelo_river = None


def _revalidar_plano_pipeline(modelo):
    """
    Modelos salvos (pickle) em versões antigas do River podem ter o cache
    interno do Pipeline (`_plan`, `_last_step_cached`, `_last_step_params`)
    desatualizado em relação à versão do River instalada agora — o pickle
    restaura apenas os atributos que existiam no momento em que foi salvo.

    Isso quebra silenciosamente `predict_proba_one`/`predict_one` com:
        AttributeError: 'Pipeline' object has no attribute '_last_step_params'

    Forçar `_build_plan()` recalcula esse cache a partir de `steps` (que
    continua íntegro no pickle), sem precisar retreinar nada.
    """
    build_plan = getattr(modelo, "_build_plan", None)
    if callable(build_plan):
        try:
            build_plan()
        except Exception as e:
            print(f"Aviso: falha ao revalidar plano do Pipeline: {e}")


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
            _revalidar_plano_pipeline(modelo_river)
            print("Modelo River carregado do banco de dados (Supabase).")
            try:
                salvar_modelo_no_banco(modelo_river)
                print(
                    "Modelo revalidado e regravado no banco (cache do Pipeline atualizado)."
                )
            except Exception as e:
                print(f"Aviso: falha ao regravar modelo revalidado no banco: {e}")
            return
    except Exception as e:
        print(f"Aviso: falha ao carregar modelo do banco: {e}")

    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                modelo_river = pickle.load(f)
            _revalidar_plano_pipeline(modelo_river)
            print(f"Modelo local carregado a partir de: {MODEL_PATH}")
            salvar_modelo_no_banco(modelo_river)
            print("Modelo local salvo no banco pela primeira vez.")
        except Exception as e:
            print(f"Erro ao carregar o modelo local: {e}")
    else:
        print(f"Nenhum modelo encontrado (nem banco, nem {MODEL_PATH}).")


carregar_modelo()

_ORDEM_RISCO = {"seguro": 0, "atencao": 1, "perigo": 2}


def _nivel_river(prob_predador: float) -> str:
    if prob_predador >= 0.75:
        return "perigo"
    if prob_predador >= 0.45:
        return "atencao"
    return "seguro"


# ── Testar mensagem — precisa estar logado, mas NÃO precisa de plano pago ──
@ia_bp.route("/api/ia/analisar", methods=["POST"])
@require_auth
def analisar_mensagem():
    data = request.get_json(silent=True) or {}
    texto = str(data.get("texto", "")).strip()

    if not texto:
        return jsonify({"error": 'O campo "texto" é obrigatório.'}), 400

    resultado_detector = analisar_texto(texto)

    prob_predador = 0.0
    modelo_nome = "Sem modelo carregado"

    if modelo_river is not None:
        try:
            # O modelo foi treinado direto em PT-BR (corpus pan12-br-*, ver
            # treinar_pan12.py) — sem nenhuma tradução. Prever em EN faz o
            # modelo tratar o texto como vocabulário desconhecido e cai pra
            # "seguro" independente do conteúdo real. NÃO traduzir aqui.
            probas = modelo_river.predict_proba_one(texto.lower())
            prob_predador = float(probas.get(True, 0.0))
            modelo_nome = "River-MultinomialNB (PT-BR direto, sem tradução)"
        except Exception as e:
            print(f"!!! ERRO NA ANALISE IA: {str(e)}")
            import traceback

            traceback.print_exc()
            return jsonify({"error": f"Falha ao processar texto na IA: {str(e)}"}), 500

    nivel_ia = _nivel_river(prob_predador)

    if (
        resultado_detector["pontuacao"] == 0
        and nivel_ia == "atencao"
        and prob_predador < 0.65
    ):
        nivel_final = "seguro"
    else:
        nivel_final = max(
            resultado_detector["nivel"], nivel_ia, key=lambda n: _ORDEM_RISCO[n]
        )

    return (
        jsonify(
            {
                "nivel": nivel_final,
                "is_predator": nivel_final != "seguro",
                "score_ia": round(prob_predador, 4),
                "score_palavras_chave": resultado_detector["pontuacao"],
                "categorias_detectadas": resultado_detector["categorias"],
                "modelo": modelo_nome,
            }
        ),
        200,
    )


# ── Ensinar o modelo — precisa de plano pago (Básico, Premium ou Escola) ──
@ia_bp.route("/api/ia/aprender", methods=["POST"])
@require_auth
def aprender_mensagem():
    global modelo_river

    if not usuario_tem_plano_pago_ativo(g.user_id):
        return (
            jsonify(
                {
                    "error": "Esse recurso é exclusivo para assinantes (plano Básico ou superior)."
                }
            ),
            403,
        )

    data = request.get_json(silent=True) or {}
    texto = str(data.get("texto", "")).strip()
    is_predator = data.get("is_predator")

    if not texto or is_predator is None:
        return (
            jsonify(
                {"error": 'Envie os campos "texto" (string) e "is_predator" (boolean).'}
            ),
            400,
        )

    if modelo_river is None:
        return jsonify({"error": "Modelo de IA não carregado."}), 500

    try:
        # Mesma regra do analisar_mensagem: sem tradução. O modelo (River +
        # BagOfWords) foi treinado direto em PT-BR — aprender em EN criava
        # um vocabulário isolado que o predict (em PT) nunca alcançava.
        texto_proc = texto.lower()
        modelo_river.learn_one(texto_proc, bool(is_predator))

        # Persiste no Supabase — sobrevive a redeploy do Render.
        salvar_modelo_no_banco(modelo_river)

        return (
            jsonify(
                {
                    "sucesso": True,
                    "mensagem": "Novo aprendizado incorporado e salvo no banco com sucesso!",
                    "texto_processado": texto_proc,
                    "is_predator": bool(is_predator),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Erro ao atualizar o modelo: {str(e)}"}), 500
