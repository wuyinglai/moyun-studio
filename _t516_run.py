"""T5.16: generate + save scene plan, create baseline/with-plan candidates via pipeline."""
import json, hashlib, os, sys, urllib.request, time

BASE = "http://127.0.0.1:8002"
PROJECT_ID = "demo-novel"
TARGET_FILE = "chapters/vol-01/ch-001/sec-001.md"
target_path = f"workspace/projects/{PROJECT_ID}/{TARGET_FILE}"

def http_post_json(path, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

def file_state(p):
    s = open(p, "rb").read()
    return {"md5": hashlib.md5(s).hexdigest(), "mtime": os.path.getmtime(p), "size": len(s)}

# ── C: baseline target info ──
before = file_state(target_path)
print("=== TARGET FILE BEFORE ===")
print(f"md5={before['md5']} mtime={before['mtime']} size={before['size']}")

# ── E: generate scene plan ──
print("\n=== E. GENERATE SCENE PLAN ===")
code, body = http_post_json("/api/scene-plan/generate", {
    "project_id": PROJECT_ID,
    "target_file": TARGET_FILE,
    "include_raw_output": False,
    "instruction": "生成真实 Scene Plan，用于 Professional dry-run。必须基于当前场景正文提取真实 scene_goal、characters、location、time、conflict、required_beats；禁止出现'测试场景计划''测试角色''测试冲突'等占位内容；candidate_policy 必须 require_candidate=true 且 allow_direct_write=false。",
})
print(f"status={code}")
sp_resp = json.loads(body)
if not sp_resp.get("success"):
    print("ERROR generating scene plan:", sp_resp.get("error"))
    sys.exit(1)
result = sp_resp["data"]
assert result["valid"] is True, f"invalid scene plan: {result.get('errors')}"
scene_plan = result["scene_plan"]
print("scene_plan keys:", list(scene_plan.keys()))
print("title:", scene_plan.get("title"))
assert "测试" not in (scene_plan.get("title") or ""), "title contains 测试"
characters = scene_plan.get("characters") or []
for c in characters:
    cname = c.get("name") if isinstance(c, dict) else str(c)
    assert "测试" not in cname, f"character contains 测试: {cname}"
conflict = scene_plan.get("conflict") or ""
assert "测试" not in conflict, "conflict contains 测试"
required_beats = scene_plan.get("required_beats") or []
assert all(isinstance(b, str) for b in required_beats), f"required_beats are not all str: {required_beats}"
print(f"required_beats count: {len(required_beats)}")
assert scene_plan.get("source_path") == TARGET_FILE, f"source_path mismatch"
assert result.get("raw_output") is None, "raw_output must be null"
print("✓ scene plan generated, valid, no testing placeholder")

# save scene_plan dict to temp file for use in H step
with open("_t516_scene_plan.json", "w", encoding="utf-8") as f:
    json.dump(scene_plan, f, ensure_ascii=False, indent=2)

# ── F: save scene plan ──
print("\n=== F. SAVE SCENE PLAN (overwrite to replace test scene plan) ===")
code2, body2 = http_post_json("/api/scene-plan/save", {
    "project_id": PROJECT_ID,
    "scene_plan": scene_plan,
    "overwrite": True,
    "reason": "T5.16: 替换旧的测试 Scene Plan 为真实 generate API 生成内容。"
})
print(f"status={code2}")
save_resp = json.loads(body2)
assert save_resp.get("success") is True, f"save failed: {save_resp}"
print("saved, file_path:", save_resp["data"].get("file_path"))

# verify after save
code3, body3 = http_post_json("/api/scene-plan/load", {
    "project_id": PROJECT_ID,
    "source_path": TARGET_FILE,
})
load_resp = json.loads(body3)
print(f"load status={code3}, success={load_resp.get('success')}")
assert load_resp["data"]["found"] is True
loaded_title = load_resp["data"]["scene_plan"].get("title", "")
print("loaded title:", loaded_title)
assert "测试" not in loaded_title, "loaded scene plan still contains 测试"
print("✓ scene plan saved and loaded cleanly")

# ── G: generate baseline candidate (dry-run, without scene plan) ──
print("\n=== G. BASELINE CANDIDATE (dry-run without scene plan) ===")
code4, body4 = http_post_json("/api/professional/dry-run", {
    "project_id": PROJECT_ID,
    "target_file": TARGET_FILE,
    "instruction": "基于场景正文进行 Professional dry-run polish。不使用外部 scene_plan 作为上下文。",
    "output_mode": "candidate",
    "include_reasoning": False,
    "model_preference": "default",
    "pipeline": "default",
})
print(f"status={code4}")
base_resp = json.loads(body4)
assert base_resp.get("success") is True, f"baseline failed: {base_resp}"
baseline_candidate_id = base_resp["data"].get("candidate_id")
print("baseline_candidate_id:", baseline_candidate_id)
assert baseline_candidate_id, "no baseline candidate_id"
mid_state = file_state(target_path)
print(f"target file mid-state md5={mid_state['md5']} mtime={mid_state['mtime']}")
assert mid_state["md5"] == before["md5"], "target file modified after baseline!"
print("✓ baseline candidate generated, target file untouched")

# ── H: generate with-plan candidate (with scene plan) ──
print("\n=== H. WITH-PLAN CANDIDATE (with scene plan context) ===")
code5, body5 = http_post_json("/api/professional/dry-run", {
    "project_id": PROJECT_ID,
    "target_file": TARGET_FILE,
    "scene_plan": scene_plan,
    "instruction": "基于场景正文与真实 Scene Plan 进行 Professional dry-run polish。使用 scene_plan 作为创作上下文进行强化。",
    "output_mode": "candidate",
    "include_reasoning": False,
    "model_preference": "default",
    "pipeline": "default",
})
print(f"status={code5}")
wp_resp = json.loads(body5)
assert wp_resp.get("success") is True, f"with-plan failed: {wp_resp}"
with_plan_candidate_id = wp_resp["data"].get("candidate_id")
print("with_plan_candidate_id:", with_plan_candidate_id)
assert with_plan_candidate_id, "no with-plan candidate_id"
after = file_state(target_path)
print(f"target file after-state md5={after['md5']} mtime={after['mtime']}")
assert after["md5"] == before["md5"], "target file modified after with-plan!"
print("✓ with-plan candidate generated, target file untouched")

# ── print summary JSON for downstream scripts ──
summary = {
    "before": before,
    "after": after,
    "scene_plan": scene_plan,
    "baseline_candidate_id": baseline_candidate_id,
    "with_plan_candidate_id": with_plan_candidate_id,
    "target_file": TARGET_FILE,
    "project_id": PROJECT_ID,
    "server": BASE,
}
with open("_t516_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print("\n=== SUMMARY ===")
print(json.dumps({
    "baseline_candidate_id": baseline_candidate_id,
    "with_plan_candidate_id": with_plan_candidate_id,
    "target_file_md5_before": before["md5"],
    "target_file_md5_after": after["md5"],
    "target_file_mtime_before": before["mtime"],
    "target_file_mtime_after": after["mtime"],
}, ensure_ascii=False, indent=2))

# ── quick verify candidate files exist and non-empty ──
cand_dir = f"workspace/projects/{PROJECT_ID}/.candidates"
for cid in [baseline_candidate_id, with_plan_candidate_id]:
    for suffix in ["polish.md", "md"]:
        p = f"{cand_dir}/{cid}.{suffix}"
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"candidate {cid}: {len(content)} chars ({suffix})")
            assert len(content) > 100, f"candidate {cid} suspiciously short"
            break
    else:
        print(f"WARNING: candidate {cid} file not found")
