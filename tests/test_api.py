"""AI Council API 테스트 (실제 GPT/Claude를 호출하지 않음 — tests/fake_bin 의 가짜 CLI 사용).

실행: 저장소 루트에서  python tests/test_api.py
대화 데이터는 임시 폴더에만 만들고 끝나면 지웁니다.
"""
import json, os, sys, threading, urllib.request, urllib.parse, tempfile, pathlib, shutil
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
T = str(HERE)  # fake_bin, fixtures 위치
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["AI_COUNCIL_DATA_DIR"] = str(tmp/"data"); os.environ["AI_COUNCIL_EXPORT_DIR"] = str(tmp/"exports")
os.environ["FAKE_LOG"] = str(tmp/"claude.log")
os.environ["PATH"] = str(HERE/"fake_bin") + os.pathsep + os.environ["PATH"]
os.environ["T"] = str(tmp)
sys.path.insert(0, str(ROOT))
import ai_council_web as w, council_context as cc
from http.server import ThreadingHTTPServer
srv = ThreadingHTTPServer(("127.0.0.1", 0), w.Handler); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{port}"
def get(p): return json.loads(urllib.request.urlopen(B+p).read())
def post(p, body=None, raw=False):
    r = urllib.request.Request(B+p, data=json.dumps(body or {}).encode(), headers={"Content-Type":"application/json"})
    try: data = urllib.request.urlopen(r).read().decode()
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
    return [json.loads(l) for l in data.splitlines() if l] if raw else json.loads(data)
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m) or (c or sys.exit(1))

ok(urllib.request.urlopen(B+"/").status == 200, "index 200")
s = get("/api/status"); ok(s["ok"] and s["cli"] == {"codex": True, "claude": True}, f"status {s}")
c1 = post("/api/conversations")["id"]; c2 = post("/api/conversations")["id"]
ok(len(get("/api/conversations")["items"]) == 2, "create+list")
# chat both
ev = post("/api/chat", {"question":"첫 질문입니다 ComfyUI","conversation_id":c1,"target":"both","gpt_model":"gpt-6.1-sol","claude_model":"account default"}, raw=True)
types = [e["type"] for e in ev]; ok(types.count("answer")==3 and types[-1]=="done", f"chat both events {types}")
d = get("/api/conversation?id="+c1); ok([i["model"] for i in d["items"]]==["사용자","GPT","Claude","Council"], "saved 4 messages")
ok(d["meta"]["title"]=="첫 질문입니다 ComfyUI", "auto title")
ok(d["items"][1].get("cli_model")=="gpt-6.1-sol", "cli_model recorded")
# chat claude only — check shared context contains GPT label
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"두번째","conversation_id":c1,"target":"claude"}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
ok("[GPT]\nGPT 답변" in log and "You are Claude" in log and "[Council 최종 결론]" in log, "claude sees GPT history with labels")
# gpt failure in both mode -> claude still answers, no council
ev = post("/api/chat", {"question":"FAILGPT 테스트","conversation_id":c1,"target":"both"}, raw=True)
types=[e["type"] for e in ev]; ok("model_error" in types and types.count("answer")==1 and types[-1]=="done", f"partial failure {types}")
ok(get("/api/conversation?id="+c1)["items"][-1]["role"]=="error", "partial failure persisted")
# busy conflict
w._busy.add(c1); r = post("/api/conversation/delete", {"id":c1}); ok(r[0]==409, "busy delete blocked"); w._busy.discard(c1)
# rename / archive
ok(post("/api/conversation/rename", {"id":c1,"title":"  워크플로우   분석 "})["meta"]["title"]=="워크플로우 분석", "rename")
ok(post("/api/conversation/archive", {"id":c1,"archived":True})["meta"]["archived"], "archive")
ok(post("/api/conversation/archive", {"id":c1,"archived":False})["meta"]["archived"] is False, "unarchive")
# rename then new message keeps user title
post("/api/chat", {"question":"세번째","conversation_id":c1,"target":"gpt"}, raw=True)
ok(get("/api/conversation?id="+c1)["meta"]["title"]=="워크플로우 분석", "user title kept")
# search
r = get("/api/search?q="+urllib.parse.quote("comfyui")); ok(len(r["items"])>=1 and r["items"][0]["conversation_id"]==c1 and "ComfyUI" in r["items"][0]["snippet"], "search case-insensitive")
ok(get("/api/search?q=")["items"]==[], "empty search returns nothing")
ok(get("/api/search?q="+urllib.parse.quote("워크플로우"))["items"][0]["kind"] in ("title","message"), "title search")
# export twice -> collision
e1 = post("/api/export", {"id":c1}); e2 = post("/api/export", {"id":c1})
ok(e1["filename"]!=e2["filename"] and e2["filename"].endswith("_2.md"), f"export collision {e1['filename']} {e2['filename']}")
md = pathlib.Path(e1["path"]).read_text(encoding="utf-8"); ok("# 워크플로우 분석" in md and "### Council 최종 결론" in md and "### GPT · gpt-6.1-sol" in md and "한글" in md, "markdown content")
from council_store import safe_filename
ok(safe_filename('a<b>:c"/d\\e|f?g*') == "a_b__c__d_e_f_g_" and safe_filename("CON").startswith("_") and safe_filename("...") == "대화", "safe filename")
# delete -> trash -> restore -> delete -> purge
ok(post("/api/conversation/delete", {"id":c2})["ok"], "delete")
ok([x["id"] for x in get("/api/conversations?scope=trash")["items"]]==[c2] and c2 not in [x["id"] for x in get("/api/conversations")["items"]], "in trash")
ok(post("/api/conversation/restore", {"id":c2})["meta"]["id"]==c2, "restore")
post("/api/conversation/delete", {"id":c2}); r = post("/api/conversation/purge", {"id":c1}); ok(r[0]==400, "purge requires trash")
ok(post("/api/conversation/purge", {"id":c2})["ok"] and not get("/api/conversations?scope=trash")["items"], "purge")
# bad ids
ok(post("/api/conversation/rename", {"id":"../x","title":"a"})[0]==400, "bad id rejected")
# ---- summarization ----
c3 = post("/api/conversations")["id"]
st = w.store
big = "가" * 3000
for k in range(14): st.append_message(c3, "user" if k%2==0 else "assistant", f"메시지{k} "+big, "사용자" if k%2==0 else "GPT")
before = pathlib.Path(st._paths(c3)[0]).read_bytes()
os.environ["FAIL_SUMMARY"]="1"
ev = post("/api/chat", {"question":"요약 실패 테스트","conversation_id":c3,"target":"claude"}, raw=True)
types=[e["type"] for e in ev]; ok("warning" in types and types.count("answer")==1, f"summary failure non-fatal {types}")
m = get("/api/conversation?id="+c3)["meta"]; ok(m["summary_error"] and m["summarized_through"]==0, "summary error recorded")
ok(pathlib.Path(st._paths(c3)[0]).read_bytes().startswith(before), "raw jsonl untouched")
saved = [e for e in ev if e["type"]=="saved"][0]["context"]; ok(saved["omitted"]>0, f"omitted counted {saved}")
del os.environ["FAIL_SUMMARY"]
ev = post("/api/chat", {"question":"요약 성공 테스트","conversation_id":c3,"target":"claude"}, raw=True)
types=[e["type"] for e in ev]; ok("summary" in types, f"summary updated {types}")
m = get("/api/conversation?id="+c3)["meta"]; ok(m["summary"].startswith("- 사용자") and m["summarized_through"]>0 and m["summary_model"]=="Claude" and not m["summary_error"], f"meta summary {m['summarized_through']}")
ctx, info = cc.build_context(st, c3)
ok("Long-term summary" in ctx and info["omitted"]==0, f"context uses summary {info}")
# message-unit: every recent block starts with a label and full content
rec = ctx.split("## Recent conversation (verbatim, oldest first)\n")[1]
ok(all(b.startswith("[") for b in rec.split("\n\n")), "no mid-message cut")
items = st.load_messages(c3)
ok(rec.split("\n\n") == [cc.message_block(i) for i in items[info["recent_from"]:]], "recent blocks are whole messages")
# below threshold -> skipped
ok(cc.maybe_summarize(st, c3)["status"]=="skipped", "no resummarize below threshold")
# huge single message truncated with marker
c4 = post("/api/conversations")["id"]; st.append_message(c4,"user","나"*50000,"사용자")
ctx,info = cc.build_context(st,c4); ok("앞부분" in ctx and len(ctx) < 26000, "single huge message trimmed with marker")
# clear -> backup
r = post("/api/history/clear", {"id":c3}); ok(pathlib.Path(r["backup"]).exists() and get("/api/conversation?id="+c3)["items"]==[], "clear with backup")
# legacy jsonl without meta
lid = "1fa3f735-e3c8-4abb-8d11-9d17eef579d8"
(tmp/"data"/"conversations"/f"{lid}.jsonl").write_text(json.dumps({"role":"user","content":"옛날 질문","model":"사용자","time":1.0},ensure_ascii=False)+"\n",encoding="utf-8")
ok(any(x["id"]==lid and x["title"]=="옛날 질문" for x in get("/api/conversations")["items"]), "legacy V0.5 file listed")
ok(get("/api/history?conversation_id="+lid)["items"][0]["content"]=="옛날 질문", "compat history endpoint")

# ---- all models fail -> error record, excluded from next context ----
c5 = post("/api/conversations")["id"]
ev = post("/api/chat", {"question":"UNSUPPORTED 질문","conversation_id":c5,"target":"gpt","gpt_model":"gpt-6.1-sol"}, raw=True)
err = [e for e in ev if e["type"]=="error"][0]["text"]
ok("계정 기본값" in err and "Reading prompt" not in err and "ERROR" in err, "friendly hint + trimmed stderr")
its = get("/api/conversation?id="+c5)["items"]; ok([i["role"] for i in its]==["user","error"], "error record saved")
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"다시 질문","conversation_id":c5,"target":"claude"}, raw=True)
log = open(os.environ["FAKE_LOG"]).read(); ok("UNSUPPORTED" not in log and "다시 질문" in log, "failed question excluded from context")
ok(not any(r["speaker"]=="오류" for r in get("/api/search?q="+urllib.parse.quote("모든 모델"))["items"]), "error not searchable")
ok("### 오류 기록" in w.store.to_markdown(c5), "export labels error")

# ---- modes ----
import tempfile as _tf
c6 = post("/api/conversations")["id"]
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"대화 모드","conversation_id":c6,"target":"claude"}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
ok("'--disallowedTools', '*'" in log and "--system-prompt" in log and "ai-council-chat" in log, "chat mode: no tools, empty cwd")
r = post("/api/chat", {"question":"작업","conversation_id":c6,"target":"claude","mode":"work"}); ok(r[0]==400, "work mode requires folder")
r = post("/api/chat", {"question":"작업","conversation_id":c6,"target":"claude","mode":"work","workdir":"/nope/x"}); ok(r[0]==400, "work mode bad folder")
wd = _tf.mkdtemp(dir=str(tmp)); open(os.environ["FAKE_LOG"],"w").close()
ev = post("/api/chat", {"question":"작업 질문","conversation_id":c6,"target":"claude","mode":"work","workdir":wd}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
ok("'--tools', 'Read,Glob,Grep'" in log and "CWD="+os.path.realpath(wd) in log and "Work mode" in log, "work mode: read tools, cwd=workdir")
its = get("/api/conversation?id="+c6)["items"]; ok(its[-2].get("mode")=="work" and its[-2].get("workdir"), "mode saved on message")
os.environ["FAKE_OLD"]="1"
ev = post("/api/chat", {"question":"구버전","conversation_id":c6,"target":"claude"}, raw=True)
ok([e["type"] for e in ev].count("answer")==1, "fallback when CLI lacks flags"); del os.environ["FAKE_OLD"]
shutil.rmtree(wd)
v = get("/api/versions?refresh=1"); ok(v["codex"]["installed"]=="0.154.0" and "update_command" in v["codex"], "versions endpoint")
c7 = post("/api/conversations")["id"]
post("/api/chat", {"question":"모델?","conversation_id":c7,"target":"gpt"}, raw=True)
ok(get("/api/conversation?id="+c7)["items"][-1]["cli_model"]=="gpt-6.1-sol", "actual codex model recorded for account default")
post("/api/chat", {"question":"모델2","conversation_id":c7,"target":"gpt","gpt_model":"gpt-6-sol"}, raw=True)
ok(get("/api/conversation?id="+c7)["items"][-1]["cli_model"]=="gpt-6-sol", "explicit model recorded")

# ---- attachments ----
wf = open(HERE/"fixtures"/"sample_workflow.json", encoding="utf-8").read()
c8 = post("/api/conversations")["id"]
open(os.environ["FAKE_LOG"],"w").close()
ev = post("/api/chat", {"question":"이 워크플로우 분석해줘","conversation_id":c8,"target":"both","attachments":[{"name":"[GenVideo] _ test_v01.json","content":wf}]}, raw=True)
types=[e["type"] for e in ev]; ok(types.count("answer")==3, f"attach both {types}")
log = open(os.environ["FAKE_LOG"]).read()
ok("Parsed summary" in log and "### MUST (2개)" in log and "wan2.1_vace_14B_fp16.safetensors" in log and "Attached file summaries" in log, "attachment summary sent to models")
it = get("/api/conversation?id="+c8)["items"][0]
ok(it["attachments"][0]["kind"]=="workflow" and "MUST" in it["attachments"][0]["summary"] and "content" not in it["attachments"][0], "attachment recorded without raw")
ok(pathlib.Path(it["attachments"][0]["path"]).read_text(encoding="utf-8")==wf, "raw attachment saved in data/attachments")
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"아까 그 워크플로우의 MUST 노드는?","conversation_id":c8,"target":"claude"}, raw=True)
ok("[첨부 요약: [GenVideo] _ test_v01.json]" in open(os.environ["FAKE_LOG"]).read(), "follow-up sees attachment summary")
ev = post("/api/chat", {"question":"","conversation_id":c8,"target":"gpt","attachments":[{"name":"note.txt","content":"메모"}]}, raw=True)
ok(get("/api/conversation?id="+c8)["items"][-2]["content"]=="첨부한 파일을 분석해줘.", "attachment-only question")
ok(post("/api/chat", {"question":"x","conversation_id":c8,"attachments":[{"name":"a.png","content":"x"}]})[0]==400, "reject non-text ext")
ok(post("/api/chat", {"question":"x","conversation_id":c8,"attachments":[{"name":f"{i}.txt","content":"x"} for i in range(6)]})[0]==400, "reject too many files")
ok(len(get("/api/search?q="+urllib.parse.quote("test_v01"))["items"])>=1, "search finds attachment name")
ok("📎 첨부: `[GenVideo] _ test_v01.json`" in w.store.to_markdown(c8), "export lists attachment")
adir = w.store.data_dir/"attachments"/c8
post("/api/conversation/delete", {"id":c8}); ok(adir.exists(), "trash keeps attachments")
post("/api/conversation/purge", {"id":c8}); ok(not adir.exists(), "purge removes attachments")

# ---- stop ----
import threading as _th, time as _t
c9 = post("/api/conversations")["id"]
res = {}
def _run(q, target, key): res[key] = post("/api/chat", {"question":q,"conversation_id":c9,"target":target}, raw=True)
th = _th.Thread(target=_run, args=("SLOWALL 질문","both","a")); t0=_t.time(); th.start(); _t.sleep(1.5)
ok(post("/api/chat/stop", {"conversation_id":c9})["ok"], "stop accepted")
th.join(15); el=_t.time()-t0
types=[e["type"] for e in res["a"]]; ok("stopped" in types and types[-1]=="done" and el < 10, f"stopped quickly {el:.1f}s {types}")
its = get("/api/conversation?id="+c9)["items"]; ok(its[-1]["role"]=="error" and its[-1].get("failed_message_id")==its[-2]["id"], "stop recorded, question excluded")
th = _th.Thread(target=_run, args=("SLOWCLAUDE 질문","both","b")); th.start(); _t.sleep(2.0)
post("/api/chat/stop", {"conversation_id":c9}); th.join(15)
types=[e["type"] for e in res["b"]]; ok(types.count("answer")==1 and "stopped" in types, f"partial kept {types}")
its = get("/api/conversation?id="+c9)["items"]; ok(its[-2]["model"]=="GPT" and its[-1]["role"]=="error" and not its[-1].get("failed_message_id"), "GPT answer kept after stop")
ok(post("/api/chat/stop", {"conversation_id":c9})["ok"] is False, "stop when idle is harmless")
srv.shutdown(); shutil.rmtree(tmp); print("ALL PASS; temp data removed")
