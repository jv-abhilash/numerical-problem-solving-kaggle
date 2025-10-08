# test_p1_integration.py
"""
Test script for P1 integration with existing pipeline
Run this to verify P1 works with your current setup
"""

import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.resolve()
sys.path.append(str(ROOT))

# Test imports
try:
    from src.main import KCETMathSolver, setup_notebook_environment
    from src.pipeline.ingest import ingest_document_to_pipeline_format
    from src.utils.io import validate_question_structure, generate_parsing_stats
    from src.utils.schema import QuestionFormat
    from src.pipeline.normalize import normalize_question_text, assess_question_difficulty
    print("✓ All P1 imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure to run from project root directory")
    sys.exit(1)


def test_p1_with_existing_data():
    """Test P1 with your existing data files"""
    
    print("\n=== TESTING P1 WITH EXISTING DATA ===")
    
    # Check if data files exist
    data_dir = ROOT / "data"
    paper_file = data_dir / "paper.txt"
    answer_key_file = data_dir / "answer_key.csv"
    
    if not paper_file.exists():
        print(f"✗ Paper file not found: {paper_file}")
        return False
    
    if not answer_key_file.exists():
        print(f"✗ Answer key not found: {answer_key_file}")
        return False
    
    print(f"✓ Found paper file: {paper_file}")
    print(f"✓ Found answer key: {answer_key_file}")
    
    try:
        # Test P1 ingestion
        print(f"\n1. Testing P1 ingestion...")
        qtexts, options, figures = ingest_document_to_pipeline_format(paper_file)
        
        print(f"   ✓ Parsed {len(qtexts)} questions")
        print(f"   ✓ Found {sum(figures.values())} questions with figures")
        
        # Validate structure
        issues = validate_question_structure(qtexts, options)
        if issues:
            print(f"   ⚠ Found {len(issues)} validation issues:")
            for issue in issues[:5]:
                print(f"     - {issue}")
        else:
            print(f"   ✓ No validation issues")
        
        # Generate stats
        stats = generate_parsing_stats(qtexts, options, figures)
        print(f"\n2. Parsing statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Test question format utilities
        print(f"\n3. Testing format utilities...")
        sample_qkey = list(qtexts.keys())[0] if qtexts else "q1"
        qid = QuestionFormat.qkey_to_qid(sample_qkey)
        print(f"   ✓ {sample_qkey} → qid {qid}")
        
        # Test normalization
        if qtexts:
            sample_text = list(qtexts.values())[0]
            normalized = normalize_question_text(sample_text)
            difficulty = assess_question_difficulty(sample_text, options.get(sample_qkey, []))
            print(f"   ✓ Sample question difficulty: {difficulty}")
        
        return True
        
    except Exception as e:
        print(f"✗ P1 testing failed: {e}")
        return False


def test_full_pipeline_integration():
    """Test complete pipeline integration"""
    
    print("\n=== TESTING FULL PIPELINE INTEGRATION ===")
    
    try:
        # Initialize solver
        solver = KCETMathSolver()
        print("✓ KCETMathSolver initialized")
        
        # Test with sample data
        paper_file = ROOT / "data" / "paper.txt"
        
        if not paper_file.exists():
            print(f"✗ Cannot test full pipeline - paper file missing")
            return False
        
        # Test P1 stage only
        print("\n1. Testing P1 stage...")
        p1_result = solver.run_p1_ingestion(str(paper_file))
        
        if p1_result["status"] == "success":
            stats = p1_result["stats"]
            print(f"   ✓ P1 successful - {stats['total_questions']} questions")
            print(f"   ✓ Parsing method: {stats['parsing_method']}")
            print(f"   ✓ Questions with 4 options: {stats['questions_with_4_options']}")
            
            # Show sample questions
            print(f"\n2. Sample parsed questions:")
            for i, (qkey, qtext) in enumerate(list(solver.qtexts.items())[:3]):
                print(f"   {qkey}: {qtext[:80]}...")
                if qkey in solver.options:
                    for j, opt in enumerate(solver.options[qkey]):
                        print(f"     ({j+1}) {opt[:40]}...")
        
        else:
            print(f"✗ P1 failed: {p1_result.get('error')}")
            return False
        
        print(f"\n✓ Pipeline integration test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Pipeline integration test failed: {e}")
        return False


def compare_with_existing_parsing():
    """Compare P1 parsing with existing pipeline parsing"""
    
    print("\n=== COMPARING P1 WITH EXISTING PARSING ===")
    
    paper_file = ROOT / "data" / "paper.txt"
    if not paper_file.exists():
        print("✗ Cannot compare - paper file missing")
        return
    
    try:
        # Get existing parsing results
        from pipeline.planner import parse_questions
        
        text = paper_file.read_text(encoding='utf-8')
        existing_qtexts, existing_options = parse_questions(text)
        
        print(f"Existing parser: {len(existing_qtexts)} questions")
        
        # Get P1 parsing results
        p1_qtexts, p1_options, p1_figures = ingest_document_to_pipeline_format(paper_file)
        
        print(f"P1 parser: {len(p1_qtexts)} questions")
        
        # Compare results
        common_questions = set(existing_qtexts.keys()) & set(p1_qtexts.keys())
        print(f"Common questions: {len(common_questions)}")
        
        if len(existing_qtexts) != len(p1_qtexts):
            print(f"⚠ Different question counts detected")
            existing_only = set(existing_qtexts.keys()) - set(p1_qtexts.keys())
            p1_only = set(p1_qtexts.keys()) - set(existing_qtexts.keys())
            
            if existing_only:
                print(f"   Existing only: {sorted(existing_only)}")
            if p1_only:
                print(f"   P1 only: {sorted(p1_only)}")
        
        # Compare sample questions
        for qkey in list(common_questions)[:3]:
            print(f"\n{qkey}:")
            print(f"  Existing: {existing_qtexts[qkey][:60]}...")
            print(f"  P1:       {p1_qtexts[qkey][:60]}...")
            
            if qkey in existing_options and qkey in p1_options:
                print(f"  Options - Existing: {len(existing_options[qkey])}, P1: {len(p1_options[qkey])}")
        
    except Exception as e:
        print(f"✗ Comparison failed: {e}")


def create_migration_checklist():
    """Create checklist for migrating to P1"""
    
    print("\n=== MIGRATION CHECKLIST ===")
    
    checklist = [
        ("Install dependencies", "pip install PyMuPDF pdfplumber"),
        ("Test P1 parsing", "Run test_p1_with_existing_data()"),
        ("Compare results", "Run compare_with_existing_parsing()"), 
        ("Update imports", "Change imports in your code to use src.pipeline.ingest"),
        ("Update main pipeline", "Replace parse_questions with ingest_document_to_pipeline_format"),
        ("Test full pipeline", "Run complete pipeline end-to-end"),
        ("Validate outputs", "Check model_preds.csv matches expected format"),
        ("Performance test", "Compare processing speed vs existing method")
    ]
    
    for i, (task, description) in enumerate(checklist, 1):
        print(f"{i}. {task}")
        print(f"   → {description}")
    
    print(f"\n✓ After completing checklist, you'll have P1 fully integrated")


def main():
    """Run all P1 integration tests"""
    
    print("KCET Math Solver - P1 Integration Test Suite")
    print("=" * 50)
    
    # Run tests
    results = {
        "p1_basic": test_p1_with_existing_data(),
        "pipeline_integration": test_full_pipeline_integration(),
    }
    
    # Compare with existing if possible
    compare_with_existing_parsing()
    
    # Show migration checklist
    create_migration_checklist()
    
    # Summary
    print(f"\n=== TEST SUMMARY ===")
    passed = sum(results.values())
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! P1 is ready for integration.")
        print("\nNext steps:")
        print("1. Update your main pipeline to use P1 functions")
        print("2. Test with your full dataset") 
        print("3. Proceed to P2: Router enhancements")
    else:
        print("✗ Some tests failed. Please review errors above.")
        failed_tests = [name for name, result in results.items() if not result]
        print(f"Failed tests: {', '.join(failed_tests)}")


if __name__ == "__main__":
    main()


# Quick test functions for Jupyter notebook

def notebook_test_p1():
    """Quick P1 test for Jupyter notebook"""
    try:
        from src.main import setup_notebook_environment
        
        ROOT = setup_notebook_environment()
        
        # Test basic functionality
        paper_file = ROOT / "data" / "paper.txt" 
        if paper_file.exists():
            from src.pipeline.ingest import ingest_document_to_pipeline_format
            qtexts, options, figures = ingest_document_to_pipeline_format(paper_file)
            
            print(f"✓ P1 test successful!")
            print(f"  Questions: {len(qtexts)}")
            print(f"  With figures: {sum(figures.values())}")
            
            return {"qtexts": qtexts, "options": options, "figures": figures}
        else:
            print(f"✗ Paper file not found: {paper_file}")
            return None
            
    except Exception as e:
        print(f"✗ P1 test failed: {e}")
        return None


def notebook_run_pipeline():
    """Quick full pipeline test for Jupyter notebook"""
    try:
        from src.main import run_notebook_pipeline
        
        results = run_notebook_pipeline("data/paper.txt")
        
        if results.get("pipeline_status") == "completed":
            summary = results.get("summary", {})
            print("✓ Full pipeline completed!")
            print(f"  Accuracy: {summary.get('accuracy', 'N/A')}")
            print(f"  Questions: {summary.get('questions_parsed', 'N/A')}")
        else:
            print(f"✗ Pipeline failed: {results.get('error')}")
        
        return results
        
    except Exception as e:
        print(f"✗ Pipeline test failed: {e}")
        return None