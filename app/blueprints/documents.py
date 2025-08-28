import os, mimetypes
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, Response, send_from_directory
from flask_login import login_required
from werkzeug.utils import secure_filename
from ..models import Document, DocType
from .. import db

bp = Blueprint("documents", __name__)

ALLOWED={".pdf",".doc",".docx",".xls",".xlsx",".png",".jpg",".jpeg",".txt"}

def allowed(name): return os.path.splitext(name)[1].lower() in ALLOWED

@bp.route("/")
@login_required
def list_documents():
    docs=Document.query.order_by(Document.id.desc()).all()
    types=DocType.query.order_by(DocType.name.asc()).all()
    table=[]
    for d in docs:
        n=d.size_bytes or 0; units=["B","KB","MB","GB"]; i=0; s=float(n)
        while s>=1024 and i<len(units)-1: s/=1024; i+=1
        size=(f"{int(s)} {units[i]}" if i==0 else f"{s:.1f} {units[i]}")
        table.append({"id":d.id,"filename":d.filename,"case_ref":d.case_ref,"type":d.type.name if d.type else "-",
                      "uploaded_at":d.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),"size":size,"notes":d.notes or ""})
    return render_template("documents.html", documents=table, types=types)

@bp.route("/upload", methods=["POST"])
@login_required
def upload_document():
    f=request.files.get("file")
    case_ref=(request.form.get("case_ref") or "").strip()
    type_id=request.form.get("type_id") or None
    notes=(request.form.get("notes") or "").strip()

    if not f or not f.filename.strip():
        flash("Choose a file.","danger"); return redirect(url_for("documents.list_documents"))
    if not allowed(f.filename):
        flash("File type not allowed.","danger"); return redirect(url_for("documents.list_documents"))

    uploads=current_app.config["UPLOADS_DIR"]; os.makedirs(uploads, exist_ok=True)
    filename=secure_filename(f.filename); path=os.path.join(uploads, filename)
    name,ext=os.path.splitext(filename); i=1
    while os.path.exists(path):
        filename=f"{name}_{i}{ext}"; path=os.path.join(uploads, filename); i+=1
    f.save(path); size=os.path.getsize(path)

    db.session.add(Document(filename=filename, case_ref=case_ref, type_id=type_id, notes=notes,
                            uploaded_at=datetime.utcnow(), size_bytes=size))
    db.session.commit(); flash("Uploaded.","success")
    return redirect(url_for("documents.list_documents"))

@bp.route("/<int:id>/download")
@login_required
def download_document(id):
    d=Document.query.get_or_404(id)
    return send_from_directory(current_app.config["UPLOADS_DIR"], d.filename, as_attachment=True)

@bp.route("/<int:id>/preview")
@login_required
def preview_document(id):
    d=Document.query.get_or_404(id)
    path=os.path.join(current_app.config["UPLOADS_DIR"], d.filename)
    if not os.path.exists(path): abort(404)
    mime,_=mimetypes.guess_type(path); mime=mime or "application/octet-stream"
    with open(path,"rb") as fh: data=fh.read()
    return Response(data, mimetype=mime, headers={"Content-Disposition": f'inline; filename="{d.filename}"'})

@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_document(id):
    d=Document.query.get_or_404(id)
    try: os.remove(os.path.join(current_app.config["UPLOADS_DIR"], d.filename))
    except FileNotFoundError: pass
    db.session.delete(d); db.session.commit()
    flash("Deleted.","info"); return redirect(url_for("documents.list_documents"))
