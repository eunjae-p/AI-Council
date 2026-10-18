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
types = [e["type"] for e in ev]; ok(types.count("answer")==5 and types[-1]=="done", f"discussion events {types}")
d = get("/api/conversation?id="+c1); its = d["items"]
ok(its[0]["model"]=="사용자" and sorted(i["model"] for i in its[1:3])==["Claude","GPT"] and all(i.get("round")==1 for i in its[1:3])
   and sorted(i["model"] for i in its[3:5])==["Claude","GPT"] and all(i.get("round")==2 for i in its[3:5]) and its[5]["model"]=="Council", "discussion saved: round1 x2, round2 x2, conclusion")
ok(d["meta"]["title"]=="첫 질문입니다 ComfyUI", "auto title")
g1 = next(i for i in its if i["model"]=="GPT" and i.get("round")==1)
ok(g1.get("cli_model")=="gpt-6.1-sol", "cli_model recorded")
log = open(os.environ["FAKE_LOG"]).read(); parts = log.split("=====CLAUDE")
c_r1 = next(x for x in parts if "round 1 (independent opinion)" in x); c_r2 = next(x for x in parts if "round 2 (cross review)" in x)
ok("GPT 답변" not in c_r1 and "GPT 답변: 받은 프롬프트" in c_r2 and "Claude 답변 ✓ 한글" in c_r2, "round1 independent, round2 sees both answers")
ok("No web access" in c_r1 and "--search" not in log, "web search off by default in discussion")
syn = next(x for x in parts if "moderator of a discussion" in x)
ok("모델 A — round 2 review of 모델 B" in syn and "## 의견이 갈린 점" in syn and "GPT — round" not in syn and "Claude — round" not in syn, "synthesis is blind (모델 A/B) and gets reviews")
ok("Council discussion rules" in c_r1 and "Council discussion rules" in c_r2 and "Agreement between you is NOT" in c_r2, "discussion rules in both rounds")
fin = its[5]["content"]; ok("모델 A" not in fin and ("GPT 의견이 더 타당" in fin or "Claude 의견이 더 타당" in fin), f"conclusion unblinded {fin}")
ddir = w.store.data_dir/its[5]["debate_dir"]
ok(sorted(f.name for f in ddir.iterdir())==sorted(["질문.md","1_GPT.md","1_Claude.md","2_GPT_검토.md","2_Claude_검토.md","결론.md"]), f"debate log files {list(ddir.iterdir())}")
ok(ddir.parent.name.endswith("첫 질문입니다 ComfyUI") and "Council 결론입니다" in (ddir/"결론.md").read_text(encoding="utf-8"), "debate folder named by conversation")
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
md = pathlib.Path(e1["path"]).read_text(encoding="utf-8"); ok("# 워크플로우 분석" in md and "### Council 최종 결론" in md and "### GPT · 1차 의견 · gpt-6.1-sol" in md and "### Claude · 교차 검토" in md and "한글" in md, "markdown content")
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
ok("'--tools', 'Read,Glob,Grep,Edit,Write,Bash'" in log and "CWD="+os.path.realpath(wd) in log and "Work mode" in log
   and "acceptEdits" in log and "Bash(mkdir:*)" in log and "bypassPermissions" not in log, "work mode: read/write/command tools, allowlist, cwd=workdir")
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
types=[e["type"] for e in ev]; ok(types.count("answer")==5, f"attach discussion {types}")
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
ok(post("/api/chat/stop", {"conversation_id":c9, "reason":"esc"})["ok"], "stop accepted")
th.join(15); el=_t.time()-t0
types=[e["type"] for e in res["a"]]; ok("stopped" in types and types[-1]=="done" and el < 10, f"stopped quickly {el:.1f}s {types}")
its = get("/api/conversation?id="+c9)["items"]; ok(its[-1]["role"]=="error" and its[-1].get("failed_message_id")==its[-2]["id"], "stop recorded, question excluded")
ok("방법: Esc 키" in its[-1]["content"] and "중지 시점: 1라운드" in its[-1]["content"] and "경과 0분" in its[-1]["content"], f"stop detail recorded {its[-1]['content']}")
th = _th.Thread(target=_run, args=("SLOWCLAUDE 질문","both","b")); th.start(); _t.sleep(2.0)
post("/api/chat/stop", {"conversation_id":c9}); th.join(15)
types=[e["type"] for e in res["b"]]; ok(types.count("answer")==1 and "stopped" in types, f"partial kept {types}")
its = get("/api/conversation?id="+c9)["items"]; ok(its[-2]["model"]=="GPT" and its[-1]["role"]=="error" and not its[-1].get("failed_message_id"), "GPT answer kept after stop")
ok(post("/api/chat/stop", {"conversation_id":c9})["ok"] is False, "stop when idle is harmless")

# ---- images / videos ----
import subprocess as _sp
media_dir = tmp/"media"; media_dir.mkdir()
_sp.run(["ffmpeg","-v","error","-f","lavfi","-i","testsrc=size=320x240:rate=25","-frames:v","1",str(media_dir/"shot.png")], check=True)
_sp.run(["ffmpeg","-v","error","-f","lavfi","-i","testsrc=size=640x360:rate=25","-t","3","-pix_fmt","yuv420p",str(media_dir/"clip.mp4")], check=True)
def upload(conv, path, name=None):
    data = pathlib.Path(path).read_bytes()
    r = urllib.request.Request(B+f"/api/upload?conversation_id={conv}&name="+urllib.parse.quote(name or pathlib.Path(path).name), data=data, headers={"Content-Type":"application/octet-stream"})
    try: return json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
c10 = post("/api/conversations")["id"]
img = upload(c10, media_dir/"shot.png", "캡처 화면.png"); ok(img.get("kind")=="image" and img["id"].endswith("캡처 화면.png"), f"image upload {img}")
open(os.environ["FAKE_LOG"],"w").close()
ev = post("/api/chat", {"question":"이 이미지 설명해줘","conversation_id":c10,"target":"both","attachments":[{"name":"캡처 화면.png","upload":img["id"]}]}, raw=True)
types=[e["type"] for e in ev]; ok(types.count("answer")==5, f"image discussion {types}")
log = open(os.environ["FAKE_LOG"]).read()
ok("'--image'" in log and img["id"] in log, "codex got --image")
ok("'--tools', 'Read'" in log and "Image files to open with the Read tool" in log and ("CWD="+os.path.realpath(str(w.store.data_dir/"attachments"/c10))) in log, "claude reads image in attachment folder only")
it = get("/api/conversation?id="+c10)["items"][0]; att = it["attachments"][0]
ok(att["kind"]=="image" and att["images"] and "320×240" in att["summary"], f"image recorded {att['summary']}")
vid = upload(c10, media_dir/"clip.mp4")
open(os.environ["FAKE_LOG"],"w").close()
ev = post("/api/chat", {"question":"영상 분석해줘","conversation_id":c10,"target":"gpt","attachments":[{"name":"clip.mp4","upload":vid["id"]}]}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
att = get("/api/conversation?id="+c10)["items"][-2]["attachments"][0]
ok(att["kind"]=="video" and len(att["frames"])==12 and "640×360" in att["summary"] and "25.0 fps" in att["summary"], f"video frames {len(att.get('frames',[]))}")
ok(log.count("'--image'")==12, f"12 frames sent to codex ({log.count(chr(39)+'--image'+chr(39))})")
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"방금 영상 3번째 프레임은?","conversation_id":c10,"target":"gpt"}, raw=True)
log = open(os.environ["FAKE_LOG"]).read(); ok(log.count("'--image'")==12, "follow-up re-sends latest media")
rel = pathlib.Path(att["frames"][0]["path"]).relative_to(w.store.data_dir/"attachments"/c10).as_posix()
ok(urllib.request.urlopen(B+f"/api/attachment?conversation_id={c10}&file="+urllib.parse.quote(rel)).headers["Content-Type"]=="image/jpeg", "frame served")
try: urllib.request.urlopen(B+f"/api/attachment?conversation_id={c10}&file="+urllib.parse.quote("../../conversations/x")); ok(False, "traversal")
except urllib.error.HTTPError as e: ok(e.code==404, "path traversal blocked")
r = upload(c10, media_dir/"shot.png", "evil.exe"); ok(isinstance(r, tuple) and r[0]==400, "reject non-media upload")
r = post("/api/chat", {"question":"x","conversation_id":c10,"attachments":[{"name":"a","upload":"../x.png"}]}); ok(r[0]==400, "reject bad upload id")

# ---- ffmpeg 없음 ----
import council_media as _cm
_orig = _cm.find_tool; _cm.find_tool = lambda n: ""
ok(get("/api/status")["ffmpeg"] is False, "status reports missing ffmpeg")
r = upload(c10, media_dir/"clip.mp4"); ok(isinstance(r, tuple) and r[0]==400 and "ffmpeg" in r[1]["error"], "video upload refused without ffmpeg")
ok(upload(c10, media_dir/"shot.png").get("kind")=="image", "images still work without ffmpeg")
open(os.environ["FAKE_LOG"],"w").close()
ev = post("/api/chat", {"question":"영상 분석","conversation_id":c10,"target":"both","attachments":[{"name":"clip.mp4","upload":vid["id"]}]}, raw=True)
types=[e["type"] for e in ev]; log=open(os.environ["FAKE_LOG"]).read()
ok("error" in types and types.count("answer")==0 and log=="", f"no model call when frames fail {types}")
its=get("/api/conversation?id="+c10)["items"]; ok(its[-1]["role"]=="error" and its[-1].get("failed_message_id")==its[-2]["id"], "failure recorded, question excluded")
_cm.find_tool = _orig
ok(get("/api/status")["ffmpeg"] is True, "status reports ffmpeg")
# 대화 목록 아이콘: 사용 모델·모드
L = {x["id"]: x for x in get("/api/conversations?scope=all")["items"]}
ok(L[c1]["models"]==["claude","gpt"] and L[c1]["modes"]==["chat"], f"list tags both/chat {L[c1].get('models')} {L[c1].get('modes')}")
ok("work" in L[c6]["modes"] and L[c6]["models"]==["claude"], f"list tags work/claude {L[c6].get('models')} {L[c6].get('modes')}")
c11 = post("/api/conversations")["id"]
ok(get("/api/conversations")["items"][0]["models"]==[] , "new conversation has no model tag")
post("/api/chat", {"question":"FAILGPT 만","conversation_id":c11,"target":"gpt"}, raw=True)
ok({x["id"]: x for x in get("/api/conversations")["items"]}[c11]["models"]==["gpt"], "failed-only conversation shows asked model")
# 이전 버전 메타(태그 없음)도 원문에서 계산
mp = w.store.data_dir/"conversations"/f"{c1}.meta.json"; m = json.loads(mp.read_text(encoding="utf-8"))
for k in ("models_used","models_asked","modes_used"): m.pop(k, None)
mp.write_text(json.dumps(m), encoding="utf-8")
ok({x["id"]: x for x in get("/api/conversations")["items"]}[c1]["models"]==["claude","gpt"], "old meta backfilled")
# CLI 업데이트·로그인 버튼
open(os.environ["FAKE_LOG"],"w").close()
r = post("/api/cli/update", {"name":"codex"})
ok(r["ok"] and r["after"]=="0.154.0" and "'install', '-g', '@openai/codex@latest'" in open(os.environ["FAKE_LOG"]).read(), f"cli update codex {r}")
r = post("/api/cli/update", {"name":"claude"}); ok(r["ok"] and r["after"]=="2.1.290", f"cli update claude {r}")
os.environ["FAKE_NPM_FAIL"]="1"; r = post("/api/cli/update", {"name":"codex"}); del os.environ["FAKE_NPM_FAIL"]
ok(not r["ok"] and "사용 중" in r["hint"] and "EBUSY" in r["output"], "cli update failure hint")
ok(post("/api/cli/update", {"name":"rm"})[0]==400, "cli update rejects unknown name")
w._busy.add("x"); r = post("/api/cli/update", {"name":"codex"}); w._busy.discard("x"); ok(r[0]==409, "cli update blocked while answering")
w._cli_updating.add("codex"); r = post("/api/chat", {"question":"q","conversation_id":c1,"target":"gpt"}); w._cli_updating.discard("codex")
ok(r[0]==409 and "업데이트" in r[1]["error"], "chat blocked while updating")
r = post("/api/cli/login", {"name":"codex"}); ok(r["opened"] is False and "login" in r["command"], "login returns command off Windows")
# 계정 기본 모델 표시 · 사용 횟수
os.environ["CODEX_HOME"] = str(tmp/"nocodex"); os.environ["CLAUDE_CONFIG_DIR"] = str(tmp/"noclaude")
c12 = post("/api/conversations")["id"]
post("/api/chat", {"question":"기본 모델 확인","conversation_id":c12,"target":"both","gpt_model":"account default","claude_model":"account default"}, raw=True)
d = get("/api/conversation?id="+c12)["items"]
cr = next(i for i in d if i["model"]=="Claude" and i.get("round")==1)
ok(cr["content"]=="Claude 답변 ✓ 한글" and cr.get("cli_model")=="claude-opus-5-5", f"claude json parsed + real model {cr.get('cli_model')}")
s = get("/api/status")
ok(s["default_models"]["gpt"]=={"model":"gpt-6.1-sol","source":"seen"} and s["default_models"]["claude"]=={"model":"claude-opus-5-5","source":"seen"}, f"default models {s['default_models']}")
ok(s["usage"]["today"]["gpt"]>=1 and s["usage"]["today"]["claude"]>=2, f"usage counted {s['usage']}")
(tmp/"noclaude").mkdir(); (tmp/"noclaude"/"settings.json").write_text('{"model":"opus"}')
ok(get("/api/status")["default_models"]["claude"]=={"model":"opus","source":"config"}, "claude default from settings.json")
os.environ["FAKE_PLAIN"]="1"; post("/api/chat", {"question":"구버전 출력","conversation_id":c12,"target":"claude"}, raw=True); del os.environ["FAKE_PLAIN"]
ok(get("/api/conversation?id="+c12)["items"][-1]["content"]=="Claude 답변 ✓ 한글", "plain text output still works")
import council_core as core
try: core._claude_result('{"type":"result","is_error":true,"result":"Usage limit reached"}', {}); ok(False, "json error raises")
except core.CliFailure as e: ok("Usage limit" in e.stdout and "사용량" in e.hint(), "json error raises with hint")
# 웹 검색 옵션
c13 = post("/api/conversations")["id"]
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"최신 정보 확인","conversation_id":c13,"target":"both","web":True}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
ok("=====CODEX ['--search', 'exec'" in log and "'--tools', 'WebSearch,WebFetch'" in log and "'--allowedTools', 'WebSearch,WebFetch'" in log, "web search flags passed")
its = get("/api/conversation?id="+c13)["items"]
ok(its[0].get("web") is True and all(i.get("web") for i in its if i.get("round")), "web flag recorded")
ok("## Web search" in log, "web note in prompt")
os.environ["FAKE_NO_SEARCH"]="1"; ev = post("/api/chat", {"question":"구버전 codex","conversation_id":c13,"target":"gpt","web":True}, raw=True); del os.environ["FAKE_NO_SEARCH"]
types=[e["type"] for e in ev]; ok("warning" in types and types.count("answer")==1 and not get("/api/conversation?id="+c13)["items"][-1].get("web"), f"old codex falls back without search {types}")
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"단독","conversation_id":c13,"target":"claude"}, raw=True)
ok("'--disallowedTools', '*'" in open(os.environ["FAKE_LOG"]).read(), "web off for single chat by default")
ok(post("/api/debate", {"question":"x"})[0]==410, "legacy debate api retired")
r = post("/api/debate/open", {"dir":"debates/../../etc"}); ok(r[0]==400, "debate open rejects outside path")
dd = next(i for i in get("/api/conversation?id="+c1)["items"] if i.get("debate_dir"))["debate_dir"]
ok(post("/api/debate/open", {"dir":dd})["opened"] is False, "debate open returns path off Windows")
# ---- MCP (승인 기반) ----
import time as _t2
t0=_t2.time(); st = post("/api/mcp/refresh", {}); el=_t2.time()-t0
ok(el < 15 and [t["name"] for t in st["tools"]]==["mcp__claude_ai_Higgsfield__balance","mcp__claude_ai_Higgsfield__generate_video"], f"mcp discovery stops after init ({el:.1f}s) {st}")
kinds = {t["tool"]: t["kind"] for t in st["tools"]}; ok(kinds=={"balance":"read","generate_video":"action"} and st["servers"][0]["name"]=="claude.ai Higgsfield", f"mcp tool kinds {kinds}")
ok(get("/api/mcp")["allowed"]==[], "nothing allowed by default")
c14 = post("/api/conversations")["id"]
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"MCP 끄고 질문","conversation_id":c14,"target":"claude"}, raw=True)
log = open(os.environ["FAKE_LOG"]).read(); ok("--strict-mcp-config" in log and "bypassPermissions" not in log, "mcp off: strict mcp config")
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"USE_MCP 영상 만들어줘","conversation_id":c14,"target":"claude","mcp":True}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
ok("--strict-mcp-config" not in log and "bypassPermissions" not in log and "Connected tools (MCP)" in log, "mcp on: servers loaded, no bypass, rule in prompt")
it = get("/api/conversation?id="+c14)["items"][-1]
ok(it.get("mcp") and it.get("mcp_denials") and it["mcp_denials"][0]["tool"]=="mcp__claude_ai_Higgsfield__generate_video" and "고양이" in it["mcp_denials"][0]["input"], f"denied tool recorded {it.get('mcp_denials')}")
post("/api/chat", {"question":"USE_MCP 영상 만들어줘","conversation_id":c14,"target":"claude","mcp":True,"allow_once":["mcp__claude_ai_Higgsfield__generate_video","rm -rf"]}, raw=True)
its = get("/api/conversation?id="+c14)["items"]
ok(its[-1]["content"]=="MCP 실행 결과: 생성 완료" and not its[-1].get("mcp_denials") and its[-2].get("allow_once")==["mcp__claude_ai_Higgsfield__generate_video"], "allow once runs the tool, invalid names dropped")
ok(get("/api/mcp")["allowed"]==[], "allow once is not saved")
ok(post("/api/mcp/allow", {"tool":"mcp__claude_ai_Higgsfield__balance","allowed":True})["allowed"]==["mcp__claude_ai_Higgsfield__balance"], "always allow saved")
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"잔액?","conversation_id":c14,"target":"claude","mcp":True}, raw=True)
ok("'--allowedTools', 'mcp__claude_ai_Higgsfield__balance'" in open(os.environ["FAKE_LOG"]).read(), "always-allowed tool passed")
ok(post("/api/mcp/allow", {"tool":"Bash","allowed":True})[0]==400, "only mcp tools can be allowed")
post("/api/mcp/allow", {"tool":"mcp__claude_ai_Higgsfield__balance","allowed":False}); ok(get("/api/mcp")["allowed"]==[], "allow revoked")
# Codex MCP: config.toml 에 직접 적힌 서버만 끈다 (설정 밖 서버를 끄면 'invalid transport' 로 시작 실패하던 문제)
os.environ["FAKE_CODEX_MCP"]='[{"name":"higgs","enabled":true},{"name":"plugin_srv","enabled":true}]'
(tmp/"nocodex").mkdir(exist_ok=True); (tmp/"nocodex"/"config.toml").write_text('model = "gpt-6.1-sol"\n[mcp_servers.higgs]\ncommand = "x"\n[mcp_servers."bad name"]\nurl = "y"\n', encoding="utf-8")
import council_core as _cc; _cc._codex_mcp_cache[:] = [0.0, []]
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"gpt mcp","conversation_id":c14,"target":"gpt","mcp":True}, raw=True)
lg = open(os.environ["FAKE_LOG"]).read()
ok("'-c', 'mcp_servers.higgs.enabled=false', 'exec'" in lg and "plugin_srv" not in lg and "bad name" not in lg, f"only config.toml servers disabled {lg[:300]}")
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"gpt mcp on","conversation_id":c14,"target":"gpt","mcp_gpt":True}, raw=True)
lg = open(os.environ["FAKE_LOG"]).read()
ok("enabled=false" not in lg and "CODEX" in lg, "GPT MCP on: Codex MCP servers stay enabled")
ok(get("/api/conversation?id="+c14)["items"][-1].get("mcp") is True, "GPT MCP use recorded")
os.environ["FAKE_CONFIG_ERR"]="1"; _cc._codex_mcp_cache[:] = [0.0, []]
ev = post("/api/chat", {"question":"config err","conversation_id":c14,"target":"gpt"}, raw=True); del os.environ["FAKE_CONFIG_ERR"]
ok(get("/api/conversation?id="+c14)["items"][-1]["role"]=="assistant", f"config error retries without mcp override {[e['type'] for e in ev]}")
(tmp/"nocodex"/"config.toml").unlink()
del os.environ["FAKE_CODEX_MCP"]
# Windows: 공백 있는 경로의 .cmd 실행 명령줄 (C:\Program Files\nodejs\npm.cmd)
import council_core as _c3
cl = _c3.win_cmdline(["C:\\Windows\\system32\\cmd.exe","/d","/s","/c","C:\\Program Files\\nodejs\\npm.cmd","install","-g","@openai/codex@latest"])
ok(cl == 'C:\\Windows\\system32\\cmd.exe /d /s /c ""C:\\Program Files\\nodejs\\npm.cmd" install -g @openai/codex@latest"', f"cmd /s quoting {cl}")
ok(_c3.win_cmdline(["/usr/bin/codex","exec"]) == ["/usr/bin/codex","exec"], "non-cmd commands unchanged")
ok(_c3.decode_output("'C:\\Program'은(는) 내부 또는 외부 명령".encode("cp949")).startswith("'C:\\Program'은(는)"), "cp949 error text decoded")
# macOS 실행 파일
import subprocess as _sp2, stat as _st
st = get("/api/status"); ok(st["platform"] in ("windows","mac","linux") and st["setup"], "status reports platform/setup")
for f in ("Setup-mac.command", "AI-Council.command", "Update-mac.command"):
    fp = ROOT/f; ok(fp.exists() and fp.stat().st_mode & _st.S_IXUSR and b"\r\n" not in fp.read_bytes(), f"{f} exists, executable, LF")
    ok(_sp2.run(["bash","-n",str(fp)]).returncode == 0, f"{f} bash syntax")
# ---- 수정 모드 ----
import subprocess as _sp3
ed = tmp/"editrepo"; ed.mkdir()
c15 = post("/api/conversations")["id"]
post("/api/chat", {"question":"EDIT_FILE 고쳐줘","conversation_id":c15,"target":"claude","mode":"edit","workdir":str(ed)}, raw=True)
its = get("/api/conversation?id="+c15)["items"]
ok((ed/"claude_new.txt").exists() and its[-1]["role"]=="assistant" and its[-2].get("mode")=="work", "non-git folder: works without checkpoint, old 'edit' = work")
(ed/"claude_new.txt").unlink()
st = post("/api/edit/checkpoint", {"workdir":str(ed)}); ok(st["repo"] and st["clean"], f"checkpoint creates repo {st}")
(ed/"app.txt").write_text("원본\n", encoding="utf-8")
ok(post("/api/edit/status", {"workdir":str(ed)})["clean"] is False, "dirty folder detected (UI offers checkpoint)")
post("/api/edit/checkpoint", {"workdir":str(ed)})
open(os.environ["FAKE_LOG"],"w").close()
ev = post("/api/chat", {"question":"EDIT_FILE 고쳐줘","conversation_id":c15,"target":"claude","mode":"edit","workdir":str(ed)}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
ok("'--permission-mode', 'acceptEdits'" in log and "Edit,Write,Bash" in log, "claude work permissions: edit + commands, acceptEdits")
its = get("/api/conversation?id="+c15)["items"]; rec = its[-1]
ok(rec["role"]=="edit" and {f["path"]:f["status"] for f in rec["files"]}=={"claude_new.txt":"new","app.txt":"modified"} and "+Claude 수정" in rec["diff"], f"changes recorded {rec.get('files')}")
ok(post("/api/edit/apply", {"conversation_id":c15,"ref":rec["id"],"action":"revert"})["ok"], "revert ok")
ok(not (ed/"claude_new.txt").exists() and (ed/"app.txt").read_text(encoding="utf-8")=="원본\n", "revert restored files")
ok(post("/api/edit/apply", {"conversation_id":c15,"ref":rec["id"],"action":"commit"})[0]==409, "cannot apply twice")
post("/api/chat", {"question":"EDIT_FILE 다시","conversation_id":c15,"target":"claude","mode":"edit","workdir":str(ed)}, raw=True)
rec2 = get("/api/conversation?id="+c15)["items"][-1]
ok(post("/api/edit/apply", {"conversation_id":c15,"ref":rec2["id"],"action":"commit","message":"테스트 커밋"})["ok"], "commit ok")
logtxt = _sp3.run(["git","-C",str(ed),"log","--oneline"],capture_output=True,text=True).stdout
ok("테스트 커밋" in logtxt and (ed/"claude_new.txt").exists(), f"commit recorded {logtxt}")
# GPT 수정: workspace-write 샌드박스
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"EDIT_FILE gpt","conversation_id":c15,"target":"gpt","mode":"edit","workdir":str(ed)}, raw=True)
lg = open(os.environ["FAKE_LOG"]).read()
ok("'--sandbox', 'workspace-write'" in lg and (ed/"gpt_new.txt").exists(), "codex work uses workspace-write")
ok("sandbox_workspace_write.network_access=true" in lg and "danger-full-access" not in lg and "dangerously" not in lg, "GPT work mode: internet allowed, still sandboxed")
recg = get("/api/conversation?id="+c15)["items"][-1]; post("/api/edit/apply", {"conversation_id":c15,"ref":recg["id"],"action":"revert"})
ok(not (ed/"gpt_new.txt").exists(), "gpt changes reverted")
# 토론 + 수정: 1·2라운드는 읽기 전용, 결론 뒤 Claude 한 모델만 구현
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"EDIT_FILE 토론 후 수정","conversation_id":c15,"target":"both","mode":"edit","workdir":str(ed)}, raw=True)
log = open(os.environ["FAKE_LOG"]).read()
items = get("/api/conversation?id="+c15)["items"]
rr = {i.get("round"): i["model"] for i in items[-8:] if i.get("round") in (3, 4, 5)}
ok(rr == {3:"Claude", 4:"GPT", 5:"Claude"} and items[-1]["role"]=="edit", f"discussion+work: Claude runs, GPT reviews, Claude fixes {rr}")
ok(log.count("acceptEdits")==2 and "workspace-write" not in log and "planning round" in log and "'read-only'" in log, "planning/review rounds are read-only")
post("/api/edit/apply", {"conversation_id":c15,"ref":items[-1]["id"],"action":"revert"})
# 실행 모델을 GPT 로: GPT 가 실행(workspace-write + 인터넷), Claude 가 검토(읽기 전용)
open(os.environ["FAKE_LOG"],"w").close()
post("/api/chat", {"question":"EDIT_FILE GPT 실행","conversation_id":c15,"target":"both","mode":"work","workdir":str(ed),"executor":"gpt"}, raw=True)
log = open(os.environ["FAKE_LOG"]).read(); items = get("/api/conversation?id="+c15)["items"]
rr = {i.get("round"): i["model"] for i in items[-8:] if i.get("round") in (3, 4, 5)}
ok(rr.get(3)=="GPT" and rr.get(4)=="Claude" and log.count("workspace-write")>=1 and "acceptEdits" not in log, f"executor GPT, Claude reviews {rr}")
ok([i for i in items if i["role"]=="user"][-1].get("executor")=="gpt", "executor saved")
post("/api/edit/apply", {"conversation_id":c15,"ref":items[-1]["id"],"action":"revert"})
# 작업 모드 명령: 허용 목록에 없으면 막히고 승인 요청, 이번만/항상 허용
cw = tmp/"cmdwork"; cw.mkdir(); c16 = post("/api/conversations")["id"]
post("/api/chat", {"question":"RUN_CMD: npm install express","conversation_id":c16,"target":"claude","mode":"work","workdir":str(cw)}, raw=True)
a = get("/api/conversation?id="+c16)["items"][-1]
ok(a.get("cmd_denials") and a["cmd_denials"][0]["prefixes"]==["npm install"] and not (cw/"cmd_ran.txt").exists(), f"blocked command -> approval card {a.get('cmd_denials')}")
post("/api/chat", {"question":"RUN_CMD: npm install express","conversation_id":c16,"target":"claude","mode":"work","workdir":str(cw),
                   "allow_cmds_once":["npm install", "rm -rf /;x"]}, raw=True)
ok((cw/"cmd_ran.txt").exists(), "allow once runs the command")
u = [i for i in get("/api/conversation?id="+c16)["items"] if i["role"]=="user"][-1]
ok(u.get("allow_cmds_once")==["npm install"], "invalid prefixes dropped")
(cw/"cmd_ran.txt").unlink()
post("/api/chat", {"question":"RUN_CMD: npm install express","conversation_id":c16,"target":"claude","mode":"work","workdir":str(cw)}, raw=True)
ok(not (cw/"cmd_ran.txt").exists(), "allow once is not remembered")
st = post("/api/commands/allow", {"prefix":"npm install","allowed":True}); ok(any(x["prefix"]=="npm install" for x in st["allowed"]), "always allow saved")
post("/api/chat", {"question":"RUN_CMD: npm install express","conversation_id":c16,"target":"claude","mode":"work","workdir":str(cw)}, raw=True)
ok((cw/"cmd_ran.txt").exists(), "always-allowed command runs")
ok(post("/api/commands/allow", {"prefix":"a && b"})[0]==400, "unsafe prefix rejected")
ok(any(x["prefix"]=="python" and x["powerful"] for x in post("/api/commands/allow", {"prefix":"python"})["allowed"]), "powerful command flagged")
ok(not any(x["prefix"]=="npm install" for x in post("/api/commands/reset", {})["allowed"]), "reset to defaults")
import council_commands as cc2
ok(cc2.prefixes_for("cd app && FOO=1 npm run dev | tee log.txt")==["npm run","tee"], f"prefixes {cc2.prefixes_for('cd app && FOO=1 npm run dev | tee log.txt')}")
# 진행 상황: 도구를 쓰는 Claude 실행은 stream-json 으로 받아 실시간 표시 + 답변에 작업 기록 저장
cp_ = post("/api/conversations")["id"]; wdp = tmp/"progwork"; wdp.mkdir()
ev = post("/api/chat", {"question":"블렌더 큐브","conversation_id":cp_,"target":"claude","mode":"work","workdir":str(wdp)}, raw=True)
pr = [dict(e["item"], model=e["model"]) for e in ev if e["type"]=="progress"]
ok(any("blender" in e["text"] and "execute_blender_code" in e["text"] for e in pr) and any(e["kind"]=="init" for e in pr), f"live progress events {pr[:3]}")
last = get("/api/conversation?id="+cp_)["items"][-1]
ok(last["content"] and last.get("activity") and last["activity"][-1]["kind"]=="tool", "answer parsed from stream + activity saved")
ev = post("/api/chat", {"question":"그냥 대화","conversation_id":cp_,"target":"claude"}, raw=True)
ok(not [e for e in ev if e["type"]=="progress"] and get("/api/conversation?id="+cp_)["items"][-1]["content"], "plain chat stays non-streaming")
# 로그인 만료: 오류에 로그인 안내 + 왼쪽 아래 로그인 필요 표시
ca = post("/api/conversations")["id"]
ev = post("/api/chat", {"question":"AUTH_EXPIRED","conversation_id":ca,"target":"claude"}, raw=True)
me = [e for e in ev if e["type"]=="model_error"]
ok(me and "claude auth login" in me[0]["text"] and "만료" in me[0]["text"], "expired login -> sign-in hint")
import council_versions as _cv
ok("claude" in _cv._expired, "expired login marked for versions panel")
post("/api/chat", {"question":"다시","conversation_id":ca,"target":"claude"}, raw=True)
ok("claude" not in _cv._expired, "successful call clears expired mark")
# 한국어/English: 브라우저가 X-Lang: en 을 보내면 서버 안내·오류 문구를 영어로, 기록 원문은 그대로
import re as _re, council_i18n as i18n
def get_en(p): return json.loads(urllib.request.urlopen(urllib.request.Request(B+p, headers={"X-Lang":"en"})).read())
items_en = get_en("/api/conversation?id="+c15)["items"]
ok(any(i["role"]=="edit" and i["content"].startswith("Changes reverted") for i in items_en), "X-Lang en translates records")
ok(any(i["role"]=="edit" and i["content"].startswith("변경을 되돌렸습니다") for i in get("/api/conversation?id="+c15)["items"]), "stored records stay Korean")
try: urllib.request.urlopen(urllib.request.Request(B+"/api/conversation?id=bad!", headers={"X-Lang":"en"})); ok(False, "bad id")
except urllib.error.HTTPError as e: ok(json.loads(e.read())["error"] == "Invalid conversation ID.", "X-Lang en translates errors")
ok(all(sorted(_re.findall(r"\{[a-z]\}", ko)) == sorted(_re.findall(r"\{[a-z]\}", en)) for ko, en in i18n.PAIRS), "i18n placeholders match")
html = (pathlib.Path(w.__file__).parent/"web"/"index.html").read_text(encoding="utf-8")
ok("X-Lang" in html and "applyStaticLang" in html and 'id="langBtn"' in html, "UI language switch present")
srv.shutdown(); shutil.rmtree(tmp); print("ALL PASS; temp data removed")
