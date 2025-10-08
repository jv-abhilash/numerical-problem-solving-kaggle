# src/main.py
"""
KCET Math Solver — P1 Ingestion entry point (modular, DB-friendly).

Runs: TXT/PDF -> List[Question] (src.shared.schema.Question)
Optional: save to SQLite and write a debug JSON for inspection.
"""

from __future__ import annotations
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from src.p1_ingestion.api import parse_document
from src.shared.schema import Question

# Optional DB: safe to remove if you don't want SQLite persistence yet
try:
    from src.shared.db import init_sqlite, upsert_run, save_questions  # provided earlier
    HAS_DB = True
except Exception:
    HAS_DB = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("kcet.main")


def _default_run_id(paper_path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = Path(paper_path).stem
    return f"{base}-{ts}"


def _save_debug_json(path: str | Path, questions: List[Question]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


def build_cli() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="KCET Math Solver — P1 Ingestion")
    ap.add_argument("--paper", default="data/paper.txt", help="Input paper path (.txt or .pdf)")
    ap.add_argument("--run-id", default=None, help="Run identifier; defaults to <paper>-<timestamp>")
    ap.add_argument("--debug-json", default="data/p1_questions.json", help="Where to write extracted questions JSON")
    ap.add_argument("--save-sqlite", action="store_true", help="Persist questions to SQLite (data/solver.db)")
    ap.add_argument("--db-path", default="data/solver.db", help="SQLite DB path (used only with --save-sqlite)")
    ap.add_argument("--preview", type=int, default=3, help="How many questions to preview in stdout")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging")
    return ap


def main() -> int:
    ap = build_cli()
    args = ap.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 1) Ingest
    paper_path = args.paper
    run_id = args.run_id or _default_run_id(paper_path)
    log.info("P1 Ingestion starting")
    log.info(f"  paper={paper_path}")
    log.info(f"  run_id={run_id}")

    questions = parse_document(paper_path)
    log.info(f"Parsed {len(questions)} questions")

    # Preview
    for q in questions[: max(0, args.preview)]:
        opts = f" | opts={len(q['opts'])}" if q["has_options"] else ""
        snippet = q["stem"].replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:120] + "..."
        log.info(f"  {q['qid']}: {snippet}{opts}")

    # 2) Optional: save to SQLite
    if args.save_sqlite:
        if not HAS_DB:
            log.error("SQLite helpers not available. Add src/shared/db.py or remove --save-sqlite.")
            return 2
        init_sqlite(args.db_path)
        upsert_run(run_id, paper_path, db_path=args.db_path)
        save_questions(run_id, questions, db_path=args.db_path)
        log.info(f"Saved questions to SQLite → {args.db_path} (run_id={run_id})")

    # 3) Debug artifact
    _save_debug_json(args.debug_json, questions)
    log.info(f"Wrote debug JSON → {args.debug_json}")

    # Future: call p2..p7 here when implemented
    log.info("P1 complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



# # src/main.py
# """
# KCET Math Solver - Main Pipeline
# Integrated P1 (Ingestion) with existing router/solver architecture
# """

# import os
# import sys
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple, Any
# import pandas as pd
# import logging
# from dotenv import load_dotenv, find_dotenv

# # Setup logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# # Add project root to path
# ROOT = Path(__file__).parent.parent.resolve()
# if str(ROOT) not in sys.path:
#     sys.path.append(str(ROOT))

# # Import existing pipeline components
# from utils.io import answers_to_csv, normalize_record
# from pipeline.evaluator import evaluate
# from pipeline.router import route_question  
# from pipeline.agent import solve_with_router
# from pipeline.planner import parse_questions

# # Import new P1 components
# from src.pipeline.ingest import ingest_document_to_pipeline_format, generate_question_hashes


# class KCETMathSolver:
#     """
#     Main KCET Math Solver Pipeline
#     Integrates P1 (Ingestion) with existing P2-P7 components
#     """
    
#     def __init__(self, config: Optional[Dict] = None):
#         self.config = config or {}
#         self.setup_environment()
        
#         # Pipeline state
#         self.qtexts = {}
#         self.options = {}
#         self.figures = {}
#         self.question_hashes = {}
#         self.answers = {}
#         self.predictions_path = None
        
#     def setup_environment(self):
#         """Setup environment variables and model configurations"""
#         # Load environment variables
#         load_dotenv(find_dotenv(), override=False)
        
#         # Mirror HF token
#         os.environ["HF_API_KEY"] = os.environ.get("HF_API_KEY", os.environ.get("HF_TOKEN", ""))
        
#         # Model configurations from your existing setup
#         os.environ.setdefault("ROUTER_MODEL_ID", "Qwen/Qwen2.5-Math-7B-Instruct")
#         os.environ.setdefault("FALLBACK_MODEL_ID", "Qwen/Qwen3-235B-A22B-Thinking-2507")
#         os.environ.setdefault("HF_BACKEND", "local")
#         os.environ.setdefault("LOCAL_SOLVER", "0")
        
#         logger.info("Environment setup complete")
#         logger.info(f"Router Model: {os.environ.get('ROUTER_MODEL_ID')}")
#         logger.info(f"Solver Model: {os.environ.get('FALLBACK_MODEL_ID')}")
    
#     def run_p1_ingestion(self, input_file: str, use_enhanced_parser: bool = True) -> Dict[str, Any]:
#         """
#         P1: Ingestion & Normalization
        
#         Args:
#             input_file: Path to PDF or TXT file
#             use_enhanced_parser: Whether to use enhanced parser or existing one
            
#         Returns:
#             Dictionary with ingestion results and statistics
#         """
#         logger.info(f"=== P1: INGESTION & NORMALIZATION ===")
#         logger.info(f"Input file: {input_file}")
        
#         input_path = Path(input_file)
#         if not input_path.exists():
#             raise FileNotFoundError(f"Input file not found: {input_file}")
        
#         try:
#             if use_enhanced_parser and input_path.suffix.lower() in ['.pdf', '.txt']:
#                 # Use new enhanced parser
#                 self.qtexts, self.options, self.figures = ingest_document_to_pipeline_format(input_file)
#                 logger.info("Used enhanced P1 parser")
#             else:
#                 # Use existing parser for compatibility
#                 text = input_path.read_text(encoding='utf-8')
#                 self.qtexts, self.options = parse_questions(text)
#                 self.figures = {q: False for q in self.qtexts.keys()}  # Default no figures
#                 logger.info("Used existing parser")
            
#             # Generate content hashes for idempotency
#             self.question_hashes = generate_question_hashes(self.qtexts, self.options)
            
#             # Statistics
#             stats = {
#                 "total_questions": len(self.qtexts),
#                 "questions_with_4_options": sum(1 for opts in self.options.values() if len(opts) == 4),
#                 "questions_with_figures": sum(self.figures.values()),
#                 "source_file": str(input_path),
#                 "parsing_method": "enhanced" if use_enhanced_parser else "existing"
#             }
            
#             logger.info(f"✓ Parsed {stats['total_questions']} questions")
#             logger.info(f"✓ {stats['questions_with_4_options']} questions have 4 options")
#             logger.info(f"✓ {stats['questions_with_figures']} questions have figures")
            
#             # Validation
#             issues = self._validate_questions()
#             if issues:
#                 logger.warning(f"Found {len(issues)} validation issues")
#                 for issue in issues[:5]:  # Show first 5
#                     logger.warning(f"  - {issue}")
#             else:
#                 logger.info("✓ No validation issues found")
            
#             return {
#                 "status": "success",
#                 "stats": stats,
#                 "issues": issues,
#                 "qtexts": self.qtexts,
#                 "options": self.options,
#                 "figures": self.figures
#             }
            
#         except Exception as e:
#             logger.error(f"P1 ingestion failed: {e}")
#             return {"status": "error", "error": str(e)}
    
#     def run_p2_to_p7_pipeline(self, batch_size: int = 20, **solver_kwargs) -> Dict[str, Any]:
#         """
#         P2-P7: Router → Solver → Evaluator (using existing pipeline)
        
#         Args:
#             batch_size: Batch size for processing
#             **solver_kwargs: Additional arguments for solver
            
#         Returns:
#             Dictionary with solving results
#         """
#         if not self.qtexts:
#             raise ValueError("No questions loaded. Run P1 ingestion first.")
        
#         logger.info(f"=== P2-P7: ROUTER → SOLVER → EVALUATOR ===")
        
#         # Reconstruct full prompt for existing pipeline compatibility
#         full_text = self._reconstruct_prompt_from_questions()
        
#         try:
#             # Run existing solver pipeline
#             solver_config = {
#                 "batch_size": batch_size,
#                 "use_langchain_router": False,
#                 "prefer_regex_on_conflict": True, 
#                 "temperature": 0.0,
#                 "max_tokens": 20000,
#                 "verbose": True,
#                 **solver_kwargs
#             }
            
#             logger.info("Running solver with existing pipeline...")
#             self.answers, qtexts_returned = solve_with_router(full_text, **solver_config)
            
#             # Generate predictions CSV
#             self.predictions_path = answers_to_csv(
#                 self.answers, 
#                 self.qtexts,  # Use our qtexts instead of returned ones
#                 out_path=self.config.get('predictions_path', 'data/model_preds.csv')
#             )
            
#             logger.info(f"✓ Saved predictions to: {self.predictions_path}")
            
#             # Add question types if missing (from your existing code pattern)
#             self._ensure_question_types()
            
#             return {
#                 "status": "success",
#                 "predictions_path": self.predictions_path,
#                 "total_answered": len(self.answers),
#                 "answers": self.answers
#             }
            
#         except Exception as e:
#             logger.error(f"P2-P7 pipeline failed: {e}")
#             return {"status": "error", "error": str(e)}
    
#     def run_evaluation(self, answer_key_path: str = "data/answer_key.csv", 
#                       output_dir: str = "data") -> Dict[str, Any]:
#         """
#         Evaluate predictions against answer key and generate mismatch report
        
#         Args:
#             answer_key_path: Path to answer key CSV
#             output_dir: Output directory for results
            
#         Returns:
#             Evaluation results
#         """
#         if not self.predictions_path:
#             raise ValueError("No predictions available. Run solver pipeline first.")
        
#         logger.info("=== EVALUATION ===")
        
#         try:
#             # Run evaluation using existing evaluator
#             eval_result = evaluate(
#                 key_path=answer_key_path,
#                 pred_path=self.predictions_path,
#                 topic_col="qtype",  # Updated from "class_type"
#                 out_dir=output_dir
#             )
            
#             logger.info("✓ Evaluation complete")
#             logger.info(f"Accuracy: {eval_result.get('summary', {}).get('accuracy', 'N/A')}")
            
#             # Generate mismatches report (from your existing code pattern)
#             self._generate_mismatches_report(answer_key_path, output_dir)
            
#             return {
#                 "status": "success",
#                 "eval_result": eval_result,
#                 "mismatch_file": Path(output_dir) / "model_preds_mismatch.csv"
#             }
            
#         except Exception as e:
#             logger.error(f"Evaluation failed: {e}")
#             return {"status": "error", "error": str(e)}
    
#     def run_full_pipeline(self, input_file: str, answer_key_path: str = "data/answer_key.csv",
#                          output_dir: str = "data", **kwargs) -> Dict[str, Any]:
#         """
#         Run complete P1-P7 pipeline
        
#         Args:
#             input_file: Input document path
#             answer_key_path: Answer key path
#             output_dir: Output directory
#             **kwargs: Additional configuration
            
#         Returns:
#             Complete pipeline results
#         """
#         results = {
#             "pipeline_status": "started",
#             "stages_completed": [],
#             "stages_failed": []
#         }
        
#         try:
#             # P1: Ingestion
#             p1_result = self.run_p1_ingestion(input_file, **kwargs)
#             if p1_result["status"] == "success":
#                 results["stages_completed"].append("P1_ingestion")
#                 results["p1_result"] = p1_result
#             else:
#                 results["stages_failed"].append("P1_ingestion")
#                 results["error"] = p1_result.get("error")
#                 return results
            
#             # P2-P7: Solving
#             p2_p7_result = self.run_p2_to_p7_pipeline(**kwargs)
#             if p2_p7_result["status"] == "success":
#                 results["stages_completed"].append("P2_P7_solving")
#                 results["p2_p7_result"] = p2_p7_result
#             else:
#                 results["stages_failed"].append("P2_P7_solving")
#                 results["error"] = p2_p7_result.get("error")
#                 return results
            
#             # Evaluation
#             eval_result = self.run_evaluation(answer_key_path, output_dir)
#             if eval_result["status"] == "success":
#                 results["stages_completed"].append("evaluation")
#                 results["eval_result"] = eval_result
#             else:
#                 results["stages_failed"].append("evaluation")
#                 results["eval_error"] = eval_result.get("error")
            
#             results["pipeline_status"] = "completed"
#             results["summary"] = self._generate_pipeline_summary(results)
            
#             return results
            
#         except Exception as e:
#             logger.error(f"Full pipeline failed: {e}")
#             results["pipeline_status"] = "failed"
#             results["error"] = str(e)
#             return results
    
#     # Helper methods
    
#     def _validate_questions(self) -> List[str]:
#         """Validate parsed questions and return list of issues"""
#         issues = []
        
#         for qkey, qtext in self.qtexts.items():
#             if not qtext.strip():
#                 issues.append(f"{qkey}: Empty question text")
            
#             if qkey in self.options:
#                 opts = self.options[qkey]
#                 if len(opts) != 4:
#                     issues.append(f"{qkey}: Has {len(opts)} options instead of 4")
                
#                 if any(not opt.strip() for opt in opts):
#                     issues.append(f"{qkey}: Has empty options")
        
#         return issues
    
#     def _reconstruct_prompt_from_questions(self) -> str:
#         """Reconstruct full prompt text from parsed questions (for compatibility)"""
#         lines = []
        
#         for qkey in sorted(self.qtexts.keys(), key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
#             q_num = qkey[1:] if qkey.startswith('q') else qkey
            
#             # Add question
#             lines.append(f"Q{q_num}. {self.qtexts[qkey]}")
            
#             # Add options
#             if qkey in self.options:
#                 for i, option in enumerate(self.options[qkey], 1):
#                     lines.append(f"({i}) {option}")
            
#             lines.append("")  # Empty line between questions
        
#         return "\n".join(lines)
    
#     def _ensure_question_types(self):
#         """Ensure all questions have qtype classification (from your existing pattern)"""
#         if not self.predictions_path:
#             return
        
#         try:
#             preds_df = pd.read_csv(self.predictions_path)
            
#             if "qtype" not in preds_df.columns or preds_df["qtype"].isna().any():
#                 logger.info("Computing missing question types...")
                
#                 # Compute qtype for missing entries
#                 rows = []
#                 for qkey, qtext in self.qtexts.items():
#                     q_num = int(qkey[1:]) if qkey[1:].isdigit() else None
#                     if q_num is not None:
#                         qtype = route_question(
#                             qtext,
#                             use_langchain_router=False,
#                             prefer_regex_on_conflict=True
#                         )
#                         rows.append({"qid": q_num, "qtype": qtype})
                
#                 qtypes_df = pd.DataFrame(rows)
                
#                 # Merge back into predictions
#                 preds_df = preds_df.drop(columns=["qtype"], errors="ignore")
#                 preds_df = preds_df.merge(qtypes_df, on="qid", how="left")
#                 preds_df["qtype"] = preds_df["qtype"].fillna("unknown")
                
#                 # Save updated predictions
#                 preds_df.to_csv(self.predictions_path, index=False)
#                 logger.info("✓ Updated question types in predictions")
                
#         except Exception as e:
#             logger.warning(f"Could not ensure question types: {e}")
    
#     def _generate_mismatches_report(self, answer_key_path: str, output_dir: str):
#         """Generate mismatches report (adapted from your existing code pattern)"""
#         try:
#             # Load data
#             preds_df = pd.read_csv(self.predictions_path)
#             key_df = pd.read_csv(answer_key_path)
            
#             # Normalize qid columns
#             preds_df["qid"] = pd.to_numeric(preds_df["qid"], errors="coerce").astype("Int64")
#             key_df["qid"] = pd.to_numeric(key_df["qid"], errors="coerce").astype("Int64")
            
#             # Merge and compute correctness
#             df = preds_df.merge(
#                 key_df[["qid", "option_index"]].rename(columns={"option_index": "answer"}),
#                 on="qid", how="left", validate="m:1"
#             )
#             df["correct"] = (df["option_index"] == df["answer"])
            
#             # Generate mismatches
#             mism = df[~df["correct"]].sort_values("qid")
#             mism_path = Path(output_dir) / "model_preds_mismatch.csv"
            
#             # Select relevant columns
#             cols = [c for c in ["qid", "qtype", "option_index", "answer", "explanation"] 
#                    if c in mism.columns]
#             mism[cols].to_csv(mism_path, index=False)
            
#             logger.info(f"✓ Generated mismatches report: {mism_path}")
#             logger.info(f"  Total incorrect: {len(mism)} out of {len(df)} questions")
            
#             # Per-type accuracy breakdown
#             if "qtype" in df.columns:
#                 type_acc = df.groupby("qtype", dropna=False)["correct"].mean().sort_values(ascending=False)
#                 logger.info("Per-type accuracy:")
#                 for qtype, acc in type_acc.items():
#                     logger.info(f"  {qtype}: {acc:.3f}")
            
#         except Exception as e:
#             logger.warning(f"Could not generate mismatches report: {e}")
    
#     def _generate_pipeline_summary(self, results: Dict) -> Dict[str, Any]:
#         """Generate summary of pipeline execution"""
#         summary = {
#             "total_stages": len(results.get("stages_completed", [])) + len(results.get("stages_failed", [])),
#             "completed_stages": len(results.get("stages_completed", [])),
#             "failed_stages": len(results.get("stages_failed", [])),
#             "success_rate": 0.0
#         }
        
#         if summary["total_stages"] > 0:
#             summary["success_rate"] = summary["completed_stages"] / summary["total_stages"]
        
#         # Add specific metrics from each stage
#         if "p1_result" in results:
#             p1_stats = results["p1_result"].get("stats", {})
#             summary["questions_parsed"] = p1_stats.get("total_questions", 0)
#             summary["parsing_method"] = p1_stats.get("parsing_method", "unknown")
        
#         if "p2_p7_result" in results:
#             summary["questions_answered"] = results["p2_p7_result"].get("total_answered", 0)
        
#         if "eval_result" in results:
#             eval_summary = results["eval_result"].get("eval_result", {}).get("summary", {})
#             summary["accuracy"] = eval_summary.get("accuracy", 0.0)
        
#         return summary


# def create_cli_interface():
#     """Command line interface for the KCET Math Solver"""
#     import argparse
    
#     parser = argparse.ArgumentParser(description="KCET Math Solver Pipeline")
    
#     # Input/Output arguments
#     parser.add_argument("input_file", help="Input PDF or TXT file path")
#     parser.add_argument("--answer-key", default="data/answer_key.csv", 
#                        help="Path to answer key CSV file")
#     parser.add_argument("--output-dir", default="data", 
#                        help="Output directory for results")
#     parser.add_argument("--predictions-file", default="data/model_preds.csv",
#                        help="Output path for predictions CSV")
    
#     # Pipeline configuration
#     parser.add_argument("--stage", choices=["p1", "p2-p7", "eval", "all"], default="all",
#                        help="Which pipeline stage to run")
#     parser.add_argument("--use-enhanced-parser", action="store_true", default=True,
#                        help="Use enhanced P1 parser (default: True)")
#     parser.add_argument("--batch-size", type=int, default=20,
#                        help="Batch size for processing")
    
#     # Solver configuration  
#     parser.add_argument("--temperature", type=float, default=0.0,
#                        help="LLM temperature")
#     parser.add_argument("--max-tokens", type=int, default=20000,
#                        help="Maximum tokens per request")
#     parser.add_argument("--verbose", action="store_true",
#                        help="Enable verbose logging")
    
#     return parser


# def main():
#     """Main entry point"""
#     parser = create_cli_interface()
#     args = parser.parse_args()
    
#     # Configure logging level
#     if args.verbose:
#         logging.getLogger().setLevel(logging.DEBUG)
    
#     # Initialize solver
#     config = {
#         "predictions_path": args.predictions_file,
#         "output_dir": args.output_dir
#     }
    
#     solver = KCETMathSolver(config)
    
#     # Run requested pipeline stage
#     try:
#         if args.stage == "all":
#             logger.info("Running complete P1-P7 pipeline...")
#             results = solver.run_full_pipeline(
#                 input_file=args.input_file,
#                 answer_key_path=args.answer_key,
#                 output_dir=args.output_dir,
#                 use_enhanced_parser=args.use_enhanced_parser,
#                 batch_size=args.batch_size,
#                 temperature=args.temperature,
#                 max_tokens=args.max_tokens,
#                 verbose=args.verbose
#             )
            
#         elif args.stage == "p1":
#             logger.info("Running P1: Ingestion only...")
#             results = solver.run_p1_ingestion(
#                 args.input_file, 
#                 use_enhanced_parser=args.use_enhanced_parser
#             )
            
#         elif args.stage == "p2-p7":
#             logger.info("Running P2-P7: Solver pipeline...")
#             # First need to load questions
#             p1_result = solver.run_p1_ingestion(args.input_file)
#             if p1_result["status"] != "success":
#                 raise RuntimeError(f"P1 failed: {p1_result.get('error')}")
                
#             results = solver.run_p2_to_p7_pipeline(
#                 batch_size=args.batch_size,
#                 temperature=args.temperature,
#                 max_tokens=args.max_tokens,
#                 verbose=args.verbose
#             )
            
#         elif args.stage == "eval":
#             logger.info("Running evaluation only...")
#             if not Path(args.predictions_file).exists():
#                 raise FileNotFoundError(f"Predictions file not found: {args.predictions_file}")
            
#             solver.predictions_path = args.predictions_file
#             results = solver.run_evaluation(args.answer_key, args.output_dir)
        
#         # Print results
#         print("\n" + "="*60)
#         print("PIPELINE RESULTS")
#         print("="*60)
        
#         if results.get("pipeline_status") == "completed":
#             summary = results.get("summary", {})
#             print(f"✓ Pipeline completed successfully")
#             print(f"  Questions parsed: {summary.get('questions_parsed', 'N/A')}")
#             print(f"  Questions answered: {summary.get('questions_answered', 'N/A')}")
#             print(f"  Accuracy: {summary.get('accuracy', 'N/A')}")
#             print(f"  Stages completed: {summary.get('completed_stages', 0)}/{summary.get('total_stages', 0)}")
        
#         elif results.get("status") == "success":
#             print(f"✓ Stage {args.stage} completed successfully")
#             if "stats" in results:
#                 stats = results["stats"]
#                 for key, value in stats.items():
#                     print(f"  {key}: {value}")
        
#         else:
#             print(f"✗ Pipeline failed: {results.get('error', 'Unknown error')}")
#             if results.get("stages_failed"):
#                 print(f"  Failed stages: {', '.join(results['stages_failed'])}")
#             sys.exit(1)
        
#         print("="*60)
        
#     except Exception as e:
#         logger.error(f"Pipeline execution failed: {e}")
#         sys.exit(1)


# # Jupyter notebook interface functions (for compatibility with your existing notebook)

# def run_notebook_pipeline(input_file: str = "data/paper.txt", 
#                          answer_key: str = "data/answer_key.csv",
#                          **kwargs) -> Dict[str, Any]:
#     """
#     Convenience function for running pipeline in Jupyter notebook
#     Compatible with your existing notebook structure
#     """
#     solver = KCETMathSolver()
    
#     return solver.run_full_pipeline(
#         input_file=input_file,
#         answer_key_path=answer_key,
#         **kwargs
#     )


# def setup_notebook_environment():
#     """Setup function for Jupyter notebook (from your existing pattern)"""
#     from pathlib import Path
#     import sys
#     import os
#     from dotenv import load_dotenv, find_dotenv
    
#     ROOT = Path().resolve()
#     if str(ROOT) not in sys.path:
#         sys.path.append(str(ROOT))
    
#     load_dotenv(find_dotenv(), override=False)
    
#     # Set up model configurations
#     os.environ["HF_API_KEY"] = os.environ.get("HF_API_KEY", os.environ.get("HF_TOKEN", ""))
#     os.environ.setdefault("ROUTER_MODEL_ID", "Qwen/Qwen2.5-Math-7B-Instruct")
#     os.environ.setdefault("FALLBACK_MODEL_ID", "Qwen/Qwen3-235B-A22B-Thinking-2507")
#     os.environ.setdefault("HF_BACKEND", "local")
#     os.environ.setdefault("LOCAL_SOLVER", "0")
    
#     print("Notebook environment setup complete")
#     return ROOT


# if __name__ == "__main__":
#     main()


# # Example usage for testing
# """
# # Command line usage:
# python src/main.py data/paper.txt --answer-key data/answer_key.csv --output-dir data/ --verbose

# # Stage-by-stage usage:
# python src/main.py data/paper.txt --stage p1 --verbose
# python src/main.py data/paper.txt --stage p2-p7 --batch-size 10
# python src/main.py data/paper.txt --stage eval --answer-key data/answer_key.csv

# # Notebook usage:
# from src.main import run_notebook_pipeline, setup_notebook_environment

# ROOT = setup_notebook_environment()
# results = run_notebook_pipeline("data/paper.txt")
# print(results["summary"])
# """