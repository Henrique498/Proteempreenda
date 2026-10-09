import hashlib
import os
import pickle
import re
import threading
import time

from flask import Blueprint, request, jsonify, g

from auth import require_auth
from conexao import get_connection, executar
from subscription import usuario_tem_plano_pago_ativo
from .detector import analisar_texto
from .model_store import carregar_modelo_do_banco, salvar_modelo_no_banco

ia_bp = Blueprint("ia", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "modelo_river.pkl")  # semente inicial

FEEDBACK_PESO = 3          # quantas vezes cada feedback é aprendido
SYNC_INTERVALO = 2.0       # s entre checagens de feedback novo (outros workers)
MAX_TEXTO = 2000

modelo_river = None
_lock = threading.RLock()
_ultimo_feedback_id = 0
_ultimo_sync = 0.0
_overrides = {}            # texto_hash -> bool (feedback mais recente)


# ── Utilidades ────────────────────────────────────────────────
def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip().lower())


def _hash(texto: str) -> str:
    return hashlib.sha256(_normalizar(texto).encode("utf-8")).hexdigest()


def _revalidar_plano_pipeline(modelo):
    build_plan = getattr(modelo, "_build_plan", None)
    if callable(build_plan):
        try:
            build_plan()
        except Exception as e:
            print(f"Aviso: falha ao revalidar plano do Pipeline: {e}")


def carregar_modelo():
    """Carrega o modelo BASE (banco -> pkl local) e reaplica todo o log de feedback."""
    global modelo_river, _ultimo_feedback_id

    try:
        modelo_river = carregar_modelo_do_banco()
        if modelo_river is not None:
            _revalidar_plano_pipeline(modelo_river)
            print("Modelo base carregado do banco.")
    except Exception as e:
        print(f"Aviso: falha ao carregar modelo do banco: {e}")

    if modelo_river is None and os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                modelo_river = pickle.load(f)
            _revalidar_plano_pipeline(modelo_river)
            salvar_modelo_no_banco(modelo_river)  # semente, só na 1ª vez
            print("Modelo local carregado e salvo como base no banco.")
        except Exception as e:
            print(f"Erro ao carregar o modelo local: {e}")

    if modelo_river is None:
        print("Nenhum modelo encontrado.")
        return

    _ultimo_feedback_id = 0
    _sincronizar_feedback(force=True)  # replay do log inteiro


# ── Sincronização do feedback (instantâneo) ───────────────────
def _aplicar_feedback(row: dict):
    global _ultimo_feedback_id
    label = bool(row["is_predator"])
    texto_proc = row["texto"].lower()
    if modelo_river is not None:
        for _ in range(FEEDBACK_PESO):
            modelo_river.learn_one(texto_proc, label)
    _overrides[row["texto_hash"].strip()] = label
    _ultimo_feedback_id = row["id"]


def _sincronizar_feedback(force: bool = False):
    """Aplica no modelo em memória todo feedback novo do banco."""
    global _ultimo_sync
    agora = time.time()
    if not force and agora - _ultimo_sync < SYNC_INTERVALO:
        return
    with _lock:
        _ultimo_sync = agora
        try:
            rows = executar(
                "SELECT id, texto, texto_hash, is_predator FROM feedback_ia "
                "WHERE id > %s ORDER BY id",
                (_ultimo_feedback_id,),
                fetch=True,
            )
            for r in rows:
                _aplicar_feedback(r)
            if rows:
                print(f"{len(rows)} feedback(s) aplicado(s) ao modelo.")
        except Exception as e:
            print(f"Aviso: falha ao sincronizar feedback: {e}")


carregar_modelo()

_ORDEM_RISCO = {"seguro": 0, "atencao": 1, "perigo": 2}


def _nivel_river(prob_predador: float) -> str:
    if prob_predador >= 0.90:
        return "perigo"
    if prob_predador >= 0.60:
        return "atencao"
    return "seguro"

# ── Analisar (login obrigatório, plano pago NÃO) ──────────────
@ia_bp.route("/api/ia/analisar", methods=["POST"])
@require_auth
def analisar_mensagem():
    data = request.get_json(silent=True) or {}
    texto = str(data.get("texto", "")).strip()
    if not texto:
        return jsonify({"error": 'O campo "texto" é obrigatório.'}), 400

    _sincronizar_feedback()  # pega feedback feito em outros workers

    # Override: esta mesma mensagem já recebeu feedback humano
    h = _hash(texto)
    if h in _overrides:
        is_pred = _overrides[h]
        return jsonify({
            "nivel": "perigo" if is_pred else "seguro",
            "is_predator": is_pred,
            "score_ia": 1.0 if is_pred else 0.0,
            "score_palavras_chave": 0,
            "categorias_detectadas": [],
            "modelo": "Feedback confirmado pelo responsável",
        }), 200

    resultado_detector = analisar_texto(texto)
    prob_predador = 0.0
    modelo_nome = "Sem modelo carregado"

    if modelo_river is not None:
        try:
            with _lock:
                probas = modelo_river.predict_proba_one(texto.lower())
            prob_predador = float(probas.get(True, 0.0))
            modelo_nome = "River-MultinomialNB (PT-BR direto, sem tradução)"
        except Exception as e:
            print(f"!!! ERRO NA ANALISE IA: {e}")
            return jsonify({"error": f"Falha ao processar texto na IA: {e}"}), 500

    nivel_ia = _nivel_river(prob_predador)

    nivel_det = resultado_detector["nivel"]
    if nivel_det == "perigo":
        nivel_final = "perigo"      # palavras fortes de aliciamento bastam
    elif nivel_ia == "perigo" and nivel_det == "seguro":
        nivel_final = "atencao"     # só o modelo desconfiou: no máximo atenção
    else:
        nivel_final = max(nivel_det, nivel_ia, key=lambda n: _ORDEM_RISCO[n])

    return jsonify({
        "nivel": nivel_final,
        "is_predator": nivel_final != "seguro",
        "score_ia": round(prob_predador, 4),
        "score_palavras_chave": resultado_detector["pontuacao"],
        "categorias_detectadas": resultado_detector["categorias"],
        "modelo": modelo_nome,
    }), 200


# ── Aprender (plano pago) ─────────────────────────────────────
@ia_bp.route("/api/ia/aprender", methods=["POST"])
@require_auth
def aprender_mensagem():
    if not usuario_tem_plano_pago_ativo(g.user_id):
        return jsonify({"error": "Esse recurso é exclusivo para assinantes (plano Básico ou superior)."}), 403

    data = request.get_json(silent=True) or {}
    texto = str(data.get("texto", "")).strip()
    is_predator = data.get("is_predator")

    if not texto or not isinstance(is_predator, bool):
        return jsonify({"error": 'Envie "texto" (string) e "is_predator" (boolean).'}), 400
    if len(texto) > MAX_TEXTO:
        return jsonify({"error": "Texto muito longo."}), 400

    try:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO feedback_ia (user_id, texto, texto_hash, is_predator) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (g.user_id, texto, _hash(texto), is_predator),
            )
            feedback_id = cur.fetchone()[0]
            conn.commit()
        finally:
            conn.close()

        # Aplica AGORA neste worker; os outros pegam em até SYNC_INTERVALO s.
        _sincronizar_feedback(force=True)

        return jsonify({
            "sucesso": True,
            "mensagem": "Feedback aprendido.",
            "feedback_id": feedback_id,
            "is_predator": is_predator,
        }), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao registrar feedback: {e}"}), 500