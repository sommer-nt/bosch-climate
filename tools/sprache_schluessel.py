"""Alle übersetzbaren Texte (``T("…")``/``N_("…")``) aus den Quellen sammeln – für Test und Pflege von
``splitklima/sprache_en.py``. Aufruf: ``python tools/sprache_schluessel.py .`` (listet alle Texte mit Fundstelle)."""
import ast, sys, pathlib
DATEIEN = ["ui_v2.py", "app_v2.py", "splitklima/v2/auswahl.py", "splitklima/v2/zubehoer.py", "splitklima/v2/katalog.py",
           "splitklima/v2/angebot.py", "splitklima/v2/assistent.py", "splitklima/v2/fotos.py",
           "splitklima/v2/speichern.py", "splitklima/ki_plan.py", "splitklima/sprache.py"]
def sammeln(wurzel):
    out = {}
    for d in DATEIEN:
        baum = ast.parse(pathlib.Path(wurzel, d).read_text())
        konst = {}
        for n in ast.walk(baum):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                konst[n.targets[0].id] = n.value
        for n in ast.walk(baum):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) in ("T", "N_") and n.args:
                a = n.args[0]
                if isinstance(a, ast.Name) and a.id in konst:
                    a = konst[a.id]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    out.setdefault(a.value, f"{d}:{n.lineno}")
    return out
if __name__ == "__main__":
    for k, w in sammeln(sys.argv[1]).items():
        print(repr(k), "#", w)
