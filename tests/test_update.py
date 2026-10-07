"""Council 자체 업데이트 테스트: 임시 원격 저장소(가짜 GitHub)와 PC 복제본으로 확인.
실행: python tests/test_update.py  (git 필요)
"""
import os, sys, shutil, subprocess, tempfile, pathlib
SRC = pathlib.Path(__file__).resolve().parent.parent
T = pathlib.Path(tempfile.mkdtemp())
def sh(*a, cwd=None): return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
G = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]
dev = T/"dev"; shutil.copytree(SRC, dev, ignore=shutil.ignore_patterns(".git", "__pycache__", "data"))
sh("git", "init", "-q", "-b", "main", cwd=dev); sh(*G, "add", "-A", cwd=dev); sh(*G, "commit", "-qm", "v1", cwd=dev)
sh("git", "clone", "-q", "--bare", str(dev), str(T/"remote.git"))
sh("git", "remote", "add", "origin", str(T/"remote.git"), cwd=dev); sh("git", "fetch", "-q", "origin", cwd=dev)
pc = T/"pc"; sh("git", "clone", "-q", str(T/"remote.git"), str(pc))
(pc/"data"/"conversations").mkdir(parents=True); (pc/"data"/"conversations"/"x.jsonl").write_text("내 대화", encoding="utf-8")
sys.path.insert(0, str(pc)); os.chdir(pc)
import council_update as u
assert u.ROOT == pc, u.ROOT
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m) or (c or sys.exit(1))
cur = u.file_version((pc/"ai_council_web.py").read_text(encoding="utf-8"))
r = u.check(cur, force=True); ok(r["status"] == "latest", f"latest {r}")
# 새 버전을 GitHub(원격)에 올림
w = (dev/"ai_council_web.py").read_text(encoding="utf-8").replace(f'VERSION = "{cur}"', 'VERSION = "9.9.9"')
(dev/"ai_council_web.py").write_text(w, encoding="utf-8"); sh(*G, "commit", "-qam", "bump 9.9.9", cwd=dev); sh("git", "push", "-q", "origin", "main", cwd=dev)
r = u.check(cur, force=True); ok(r["status"] == "available" and r["behind"] == 1 and r["remote"] == "9.9.9" and "bump 9.9.9" in r["commits"][0], f"available {r}")
r = u.apply(cur); ok(r["status"] == "updated" and r["version"] == "9.9.9", f"applied {r}")
ok((pc/"data"/"conversations"/"x.jsonl").read_text(encoding="utf-8") == "내 대화", "data kept")
# 로컬에서 직접 수정 → 업데이트 차단
(dev/"README.md").write_text("new readme", encoding="utf-8"); sh(*G, "commit", "-qam", "readme", cwd=dev); sh("git", "push", "-q", "origin", "main", cwd=dev)
(pc/"council_core.py").write_text((pc/"council_core.py").read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8")
try: u.apply("9.9.9"); ok(False, "should block")
except u.UpdateError as e: ok("council_core.py" in str(e), "local edit blocks update: " + str(e).splitlines()[0])
sh("git", "checkout", "--", "council_core.py", cwd=pc)
# 오늘 PC 상황 재현: 파일은 최신인데 기록만 뒤처짐 (+CRLF 차이)
(pc/"README.md").write_bytes(b"new readme".replace(b"\n", b"\r\n"))
(dev/"NEWFILE.md").write_text("added", encoding="utf-8"); sh(*G, "add", "-A", cwd=dev); sh(*G, "commit", "-qm", "new file", cwd=dev); sh("git", "push", "-q", "origin", "main", cwd=dev)
(pc/"NEWFILE.md").write_text("added", encoding="utf-8")
(dev/"ANOTHER.md").write_text("x", encoding="utf-8"); sh(*G, "add", "-A", cwd=dev); sh(*G, "commit", "-qm", "another", cwd=dev); sh("git", "push", "-q", "origin", "main", cwd=dev)
r = u.apply("9.9.9"); ok(r["status"] == "synced", f"synced history only {r}")
ok(sh("git", "status", "--porcelain", cwd=pc) == "" and (pc/"ANOTHER.md").exists(), "clean after sync, missing new file restored")
r = u.check("9.9.9", force=True); ok(r["status"] == "latest", "latest after sync")
# 로컬 커밋이 있으면 차단
sh(*G, "commit", "--allow-empty", "-qm", "local", cwd=pc)
try: u.apply("9.9.9"); ok(False, "should block ahead")
except u.UpdateError as e: ok("커밋" in str(e), "local commit blocks")
ok(u.is_newer("0.10.0","0.9.0") and not u.is_newer("0.8.0","0.9.0") and not u.is_newer("0.9.0","0.9.0"), "version compare")
r = u.check("99.0.0", force=True); ok(r["status"] == "latest", "running newer than GitHub -> no downgrade offer")
# Update.cmd 와 같은 방식(화면 없이)으로 업데이트
sh("git", "reset", "-q", "--soft", "HEAD~1", cwd=pc)  # 위에서 만든 로컬 커밋 정리
w = (dev/"ai_council_web.py").read_text(encoding="utf-8").replace('VERSION = "9.9.9"', 'VERSION = "9.9.10"')
(dev/"ai_council_web.py").write_text(w, encoding="utf-8"); sh(*G, "commit", "-qam", "cli release", cwd=dev); sh("git", "push", "-q", "origin", "main", cwd=dev)
env = dict(os.environ, PYTHONUTF8="1")
out = subprocess.run([sys.executable, str(pc/"council_update.py")], cwd=pc, input="y\n", capture_output=True, text=True, env=env, timeout=120)
ok(out.returncode == 0 and "새 버전 V9.9.10" in out.stdout and "[완료] V9.9.10" in out.stdout, "cli update: " + out.stdout.strip().splitlines()[-1])
ok('VERSION = "9.9.10"' in (pc/"ai_council_web.py").read_text(encoding="utf-8"), "cli updated files")
out = subprocess.run([sys.executable, str(pc/"council_update.py")], cwd=pc, input="", capture_output=True, text=True, env=env, timeout=120)
ok("이미 최신 버전" in out.stdout, "cli says latest")
# git 저장소가 아닌 폴더
u.ROOT = T/"dev"/"web"; ok(u.check("1")["status"] == "not_repo", "zip install detected")
shutil.rmtree(T); print("ALL PASS")
