#!/usr/bin/env python3
"""
Phase T3-D7.8：D7 Pipeline 一键 dry-run

- 整合已有脚本：Diff Engine, Review Engine, Validator, State Snapshot, Plot Debt, Rewrite Engine
- 不调用新的 LLM（使用已有 review output）
- 不修改正文，不自动入库
- 只使用 fixture/sample 文件
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class D7PipelineDryrun:
    """D7 Pipeline 整合脚本"""
    
    def __init__(self, scene_path: Path, settings_dir: Path, output_dir: Path, 
                 existing_review_path: Optional[Path] = None):
        self.scene_path = scene_path
        self.settings_dir = settings_dir
        self.output_dir = output_dir
        self.existing_review_path = existing_review_path
        
        self.steps: List[Dict[str, Any]] = []
        self.summary = {
            "candidates": 0,
            "reviews": 0,
            "snapshot_updates": 0,
            "plot_debts": 0,
            "rewrite_suggestions": 0,
        }
        
    def run_step(self, name: str, command: List[str], 
                 output_files: Optional[List[str]] = None,
                 check_func: Optional[callable] = None) -> bool:
        """执行单个 pipeline 步骤"""
        print(f"\n{'='*60}")
        print(f"Step: {name}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True
            )
            
            # 检查输出文件
            found_files = []
            if output_files:
                for f in output_files:
                    file_path = self.output_dir / f
                    if file_path.exists():
                        found_files.append(f)
            
            step_info = {
                "name": name,
                "status": "passed",
                "command": " ".join(str(c) for c in command),
                "outputs": found_files,
            }
            
            # 自定义检查
            if check_func:
                check_result = check_func(self.output_dir)
                step_info["check_result"] = check_result
            
            self.steps.append(step_info)
            print(f"✅ {name} passed")
            return True
            
        except subprocess.CalledProcessError as e:
            step_info = {
                "name": name,
                "status": "failed",
                "command": " ".join(str(c) for c in command),
                "error": e.stderr if e.stderr else str(e),
            }
            self.steps.append(step_info)
            print(f"❌ {name} failed")
            print(f"Error: {e.stderr if e.stderr else e}")
            return False
        except Exception as e:
            step_info = {
                "name": name,
                "status": "failed",
                "error": str(e),
            }
            self.steps.append(step_info)
            print(f"❌ {name} failed: {e}")
            return False
    
    def check_diff_candidates(self, output_dir: Path) -> Dict[str, Any]:
        """检查 Diff Engine 输出"""
        result = {"candidates": 0, "known_diff_noise": []}
        diff_file = output_dir / "diff-candidates.json"
        if diff_file.exists():
            with open(diff_file, encoding="utf-8") as f:
                data = json.load(f)
                # 从 summary.items_found 读取 candidates
                if "summary" in data and "items_found" in data["summary"]:
                    result["candidates"] = data["summary"]["items_found"]
                else:
                    result["candidates"] = len(data.get("items", []))
                self.summary["candidates"] = result["candidates"]
                
                # 记录已知的 diff noise
                noise_entities = ["着昏黄的灯", "李玄推阁"]
                for item in data.get("items", []):
                    entity = item.get("entity", "")
                    if entity in noise_entities:
                        result["known_diff_noise"].append({
                            "entity": entity,
                            "reason": "Diff Engine candidate noise; should be reviewed/ignored downstream"
                        })
        return result
    
    def check_review_output(self, output_dir: Path) -> Dict[str, Any]:
        """检查 Review Engine 输出"""
        result = {"reviews": 0}
        # 使用已有的 review output
        if self.existing_review_path and self.existing_review_path.exists():
            with open(self.existing_review_path, encoding="utf-8") as f:
                data = json.load(f)
                result["reviews"] = len(data.get("reviews", []))
                self.summary["reviews"] = result["reviews"]
        return result
    
    def check_snapshot(self, output_dir: Path) -> Dict[str, Any]:
        """检查 State Snapshot 输出"""
        result = {"updates": 0}
        snapshot_file = output_dir / "state-snapshot.json"
        if snapshot_file.exists():
            with open(snapshot_file, encoding="utf-8") as f:
                data = json.load(f)
                result["updates"] = len(data.get("updates", []))
                self.summary["snapshot_updates"] = result["updates"]
        return result
    
    def check_plot_debt(self, output_dir: Path) -> Dict[str, Any]:
        """检查 Plot Debt 输出"""
        result = {"debts": 0}
        plot_debt_file = output_dir / "plot-debt.json"
        if plot_debt_file.exists():
            with open(plot_debt_file, encoding="utf-8") as f:
                data = json.load(f)
                result["debts"] = len(data.get("debts", []))
                self.summary["plot_debts"] = result["debts"]
        return result
    
    def check_rewrite_suggestions(self, output_dir: Path) -> Dict[str, Any]:
        """检查 Rewrite Engine 输出"""
        result = {"suggestions": 0}
        rewrite_file = output_dir / "rewrite-suggestions.json"
        if rewrite_file.exists():
            with open(rewrite_file, encoding="utf-8") as f:
                data = json.load(f)
                result["suggestions"] = len(data.get("suggestions", []))
                self.summary["rewrite_suggestions"] = result["suggestions"]
        return result
    
    def run(self) -> bool:
        """运行完整 pipeline"""
        print("=" * 60)
        print("Phase T3-D7.8：D7 Pipeline 一键 dry-run")
        print("=" * 60)
        print(f"Scene: {self.scene_path}")
        print(f"Settings Dir: {self.settings_dir}")
        print(f"Output Dir: {self.output_dir}")
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Diff Engine
        diff_command = [
            "python", "tests/prompt_experiments/diff_engine_existence_mvp.py",
            "--scene", str(self.scene_path),
            "--settings-dir", str(self.settings_dir),
            "--output-json", str(self.output_dir / "diff-candidates.json"),
            "--output-md", str(self.output_dir / "diff-candidates.md"),
        ]
        
        if not self.run_step("diff_engine", diff_command, 
                            ["diff-candidates.json", "diff-candidates.md"],
                            self.check_diff_candidates):
            return self.generate_failure_report("Diff Engine failed")
        
        # Step 2: Review Engine (使用已有输出)
        if self.existing_review_path:
            if not self.existing_review_path.exists():
                return self.generate_failure_report(
                    f"Existing review output not found: {self.existing_review_path}"
                )
            # 复制已有的 review output
            import shutil
            shutil.copy(
                self.existing_review_path,
                self.output_dir / "review-output.json"
            )
            self.steps.append({
                "name": "review_engine",
                "status": "passed",
                "note": "Used existing review output (no new LLM call)",
                "source": str(self.existing_review_path),
            })
            self.check_review_output(self.output_dir)
            print("✅ review_engine passed (used existing output)")
        else:
            return self.generate_failure_report(
                "No review output provided. Pipeline requires existing review for dry-run."
            )
        
        # Step 3: Validator
        validator_command = [
            "python", "tests/prompt_experiments/review_engine_validator.py",
            "--candidates-json", str(self.output_dir / "diff-candidates.json"),
            "--reviews-json", str(self.output_dir / "review-output.json"),
            "--output-md", str(self.output_dir / "review-validator.md"),
            "--expect-valid", "true",
        ]
        
        if not self.run_step("review_validator", validator_command,
                            ["review-validator.md"]):
            return self.generate_failure_report("Review Validator failed")
        
        # Step 4: State Snapshot
        snapshot_command = [
            "python", "tests/prompt_experiments/state_snapshot_mvp.py",
            "--scene", str(self.scene_path),
            "--candidates-json", str(self.output_dir / "diff-candidates.json"),
            "--reviews-json", str(self.output_dir / "review-output.json"),
            "--output-json", str(self.output_dir / "state-snapshot.json"),
            "--output-md", str(self.output_dir / "state-snapshot.md"),
        ]
        
        if not self.run_step("state_snapshot", snapshot_command,
                            ["state-snapshot.json", "state-snapshot.md"],
                            self.check_snapshot):
            return self.generate_failure_report("State Snapshot failed")
        
        # Step 5: Plot Debt
        plot_debt_command = [
            "python", "tests/prompt_experiments/plot_debt_mvp.py",
            "--scene", str(self.scene_path),
            "--snapshot-json", str(self.output_dir / "state-snapshot.json"),
            "--reviews-json", str(self.output_dir / "review-output.json"),
            "--output-json", str(self.output_dir / "plot-debt.json"),
            "--output-md", str(self.output_dir / "plot-debt.md"),
        ]
        
        if not self.run_step("plot_debt", plot_debt_command,
                            ["plot-debt.json", "plot-debt.md"],
                            self.check_plot_debt):
            return self.generate_failure_report("Plot Debt failed")
        
        # Step 6: Rewrite Engine
        rewrite_command = [
            "python", "tests/prompt_experiments/rewrite_engine_mvp.py",
            "--scene", str(self.scene_path),
            "--snapshot-json", str(self.output_dir / "state-snapshot.json"),
            "--plot-debt-json", str(self.output_dir / "plot-debt.json"),
            "--reviews-json", str(self.output_dir / "review-output.json"),
            "--output-json", str(self.output_dir / "rewrite-suggestions.json"),
            "--output-md", str(self.output_dir / "rewrite-suggestions.md"),
            "--max-suggestions", "5",
        ]
        
        if not self.run_step("rewrite_engine", rewrite_command,
                            ["rewrite-suggestions.json", "rewrite-suggestions.md"],
                            self.check_rewrite_suggestions):
            return self.generate_failure_report("Rewrite Engine failed")
        
        # Step 7: 生成 Pipeline Summary
        self.generate_pipeline_summary()
        
        return True
    
    def generate_failure_report(self, message: str) -> bool:
        """生成失败报告"""
        failure_report = {
            "phase": "T3-D7.8",
            "pipeline": "d7_quality_engine_dryrun",
            "status": "failed",
            "error": message,
            "steps_completed": len(self.steps),
            "steps": self.steps,
            "timestamp": datetime.now().isoformat(),
        }
        
        failure_file = self.output_dir / "pipeline-failure.json"
        with open(failure_file, "w", encoding="utf-8") as f:
            json.dump(failure_report, f, ensure_ascii=False, indent=2)
        
        print(f"\n❌ Pipeline failed: {message}")
        print(f"Failure report: {failure_file}")
        return False
    
    def generate_pipeline_summary(self):
        """生成 Pipeline Summary"""
        # 收集所有 known_diff_noise
        known_diff_noise = []
        for step in self.steps:
            if "check_result" in step and "known_diff_noise" in step["check_result"]:
                known_diff_noise.extend(step["check_result"]["known_diff_noise"])
        
        summary = {
            "phase": "T3-D7.8",
            "pipeline": "d7_quality_engine_dryrun",
            "llm_called": False,
            "used_existing_review_output": self.existing_review_path is not None,
            "auto_write_scene": False,
            "auto_write_settings": False,
            "steps": self.steps,
            "summary": self.summary,
            "known_diff_noise": known_diff_noise,
            "timestamp": datetime.now().isoformat(),
        }
        
        # 保存 JSON
        summary_file = self.output_dir / "pipeline-summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 生成 Markdown
        md_lines = [
            "# D7 Pipeline Dry-run Summary",
            "",
            f"- **Phase**: {summary['phase']}",
            f"- **Pipeline**: {summary['pipeline']}",
            f"- **LLM Called**: {summary['llm_called']}",
            f"- **Used Existing Review Output**: {summary['used_existing_review_output']}",
            f"- **Auto Write Scene**: {summary['auto_write_scene']}",
            f"- **Auto Write Settings**: {summary['auto_write_settings']}",
            "",
            "## Steps",
            "",
            "| Step | Status |",
            "|------|--------|",
        ]
        
        for step in self.steps:
            status_icon = "✅" if step["status"] == "passed" else "❌"
            md_lines.append(f"| {step['name']} | {status_icon} {step['status']} |")
        
        md_lines.extend([
            "",
            "## Summary",
            "",
            f"- **Candidates**: {self.summary['candidates']}",
            f"- **Reviews**: {self.summary['reviews']}",
            f"- **Snapshot Updates**: {self.summary['snapshot_updates']}",
            f"- **Plot Debts**: {self.summary['plot_debts']}",
            f"- **Rewrite Suggestions**: {self.summary['rewrite_suggestions']}",
            "",
        ])
        
        # 添加 known diff noise
        if known_diff_noise:
            md_lines.extend([
                "## Known Diff Noise",
                "",
                "> **Note**: These are candidate noise, NOT confirmed settings. They will be reviewed/ignored downstream.",
                "",
                "| Entity | Reason |",
                "|--------|--------|",
            ])
            for noise in known_diff_noise:
                md_lines.append(f"| {noise['entity']} | {noise['reason']} |")
            md_lines.append("")
        
        md_lines.extend([
            f"**Timestamp**: {summary['timestamp']}",
        ])
        
        md_file = self.output_dir / "pipeline-summary.md"
        md_file.write_text("\n".join(md_lines), encoding="utf-8")
        
        print(f"\n{'='*60}")
        print("Pipeline Summary")
        print(f"{'='*60}")
        print(f"✅ All steps passed!")
        print(f"📊 Candidates: {self.summary['candidates']}")
        print(f"📊 Reviews: {self.summary['reviews']}")
        print(f"📊 Snapshot Updates: {self.summary['snapshot_updates']}")
        print(f"📊 Plot Debts: {self.summary['plot_debts']}")
        print(f"📊 Rewrite Suggestions: {self.summary['rewrite_suggestions']}")
        print(f"\n📁 Summary: {summary_file}")
        print(f"📁 Markdown: {md_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.8：D7 Pipeline 一键 dry-run"
    )
    parser.add_argument("--scene", type=Path, required=True,
                        help="场景 markdown 文件路径")
    parser.add_argument("--settings-dir", type=Path, required=True,
                        help="设定目录路径")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="输出目录路径")
    parser.add_argument("--use-existing-review", type=Path, default=None,
                        help="使用已有的 review output JSON 路径")
    
    args = parser.parse_args()
    
    # 验证输入
    if not args.scene.exists():
        print(f"❌ Scene file not found: {args.scene}")
        return 1
    
    if not args.settings_dir.exists():
        print(f"❌ Settings directory not found: {args.settings_dir}")
        return 1
    
    if args.use_existing_review and not args.use_existing_review.exists():
        print(f"❌ Existing review file not found: {args.use_existing_review}")
        return 1
    
    # 运行 pipeline
    pipeline = D7PipelineDryrun(
        scene_path=args.scene,
        settings_dir=args.settings_dir,
        output_dir=args.output_dir,
        existing_review_path=args.use_existing_review,
    )
    
    success = pipeline.run()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 D7 Pipeline dry-run 完成!")
    else:
        print("❌ D7 Pipeline dry-run 失败")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
