"""
gz_migrator/app.py
==================
Flask web application for the Gazebo Classic → Gazebo Harmonic migration tool.
"""

import os
import io
import json
import tempfile
import traceback
from flask import (
    Flask, request, jsonify, render_template,
    send_file, make_response
)
from migrator import GazeboMigrator, MigrationReport

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max upload


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/migrate", methods=["POST"])
def migrate():
    """
    Accepts a .world / .sdf file upload and returns JSON with:
      - output_sdf: migrated XML string
      - report: { changes, warnings, errors, summary }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Read content
    try:
        content = f.read().decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "File is not valid UTF-8 text"}), 400

    # Run migration
    try:
        migrator = GazeboMigrator(content)
        output_xml, report = migrator.migrate()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": f"Internal error: {exc}", "traceback": traceback.format_exc()}), 500

    # Determine output filename
    base = os.path.splitext(f.filename)[0]
    out_filename = f"{base}_harmonic.sdf"

    return jsonify({
        "output_sdf": output_xml,
        "output_filename": out_filename,
        "report": {
            "changes": report.changes,
            "warnings": report.warnings,
            "errors": report.errors,
            "summary": report.summary(),
        }
    })


@app.route("/migrate_text", methods=["POST"])
def migrate_text():
    """
    Accepts raw XML text in JSON body { "xml": "..." } and returns migrated result.
    """
    data = request.get_json(silent=True)
    if not data or "xml" not in data:
        return jsonify({"error": "No XML provided in request body"}), 400

    try:
        migrator = GazeboMigrator(data["xml"])
        output_xml, report = migrator.migrate()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": f"Internal error: {exc}"}), 500

    return jsonify({
        "output_sdf": output_xml,
        "report": {
            "changes": report.changes,
            "warnings": report.warnings,
            "errors": report.errors,
            "summary": report.summary(),
        }
    })


@app.route("/download", methods=["POST"])
def download():
    """
    Accepts { "xml": "...", "filename": "..." } and returns file download.
    """
    data = request.get_json(silent=True)
    if not data or "xml" not in data:
        return jsonify({"error": "No XML provided"}), 400

    xml_bytes = data["xml"].encode("utf-8")
    filename = data.get("filename", "migrated.sdf")

    buf = io.BytesIO(xml_bytes)
    buf.seek(0)

    response = make_response(send_file(
        buf,
        mimetype="application/xml",
        as_attachment=True,
        download_name=filename,
    ))
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)
