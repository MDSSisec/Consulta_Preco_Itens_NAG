from __future__ import annotations

from flask import Blueprint, render_template


metodologia_bp = Blueprint("metodologia", __name__)


@metodologia_bp.route("/metodologia", methods=["GET"])
def metodologia_index():
    return render_template("metodologia.html", aba_atual="metodologia")
