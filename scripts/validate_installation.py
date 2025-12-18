"""Validate PowerCV Cerebras integration installation."""
import sys
from pathlib import Path


def check_files():
    """Check all required files exist."""
    required_files = [
        "app/prompts/cv_analyzer.md",
        "app/prompts/cv_optimizer.md",
        "app/prompts/cover_letter.md",
        "app/prompts/prompt_loader.py",
        "app/services/cerebras_client.py",
        "app/services/cv_analyzer.py",
        "app/services/cv_optimizer.py",
        "app/services/cover_letter_gen.py",
        "app/services/workflow_orchestrator.py",
        ".env"
    ]
    
    missing = []
    for filepath in required_files:
        if not Path(filepath).exists():
            missing.append(filepath)
    
    if missing:
        print("❌ Missing files:")
        for f in missing:
            print(f"   - {f}")
        return False
    
    print("✓ All required files present")
    return True


def check_imports():
    """Check all imports work."""
    try:
        from app.prompts.prompt_loader import PromptLoader
        from app.services.cerebras_client import CerebrasClient
        from app.services.workflow_orchestrator import CVWorkflowOrchestrator
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def check_prompts():
    """Check prompts can be loaded."""
    try:
        from app.prompts.prompt_loader import PromptLoader
        loader = PromptLoader()
        prompts = loader.load_all_prompts()
        print(f"✓ Loaded {len(prompts)} prompts")
        return True
    except Exception as e:
        print(f"❌ Prompt loading error: {e}")
        return False


def check_env():
    """Check environment variables."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key or api_key == "your_api_key_here_REPLACE_THIS":
        print("⚠️  Warning: CEREBRAS_API_KEY not set in .env")
        return False
    
    print("✓ Environment variables configured")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PowerCV Cerebras Integration - Validation")
    print("=" * 60)
    
    all_ok = True
    
    print("\n1. Checking files...")
    all_ok &= check_files()
    
    print("\n2. Checking imports...")
    all_ok &= check_imports()
    
    print("\n3. Checking prompts...")
    all_ok &= check_prompts()
    
    print("\n4. Checking environment...")
    env_ok = check_env()
    
    print("\n" + "=" * 60)
    if all_ok and env_ok:
        print("✅ Installation validated successfully!")
        print("\nNext steps:")
        print("  1. Run: pytest app/tests/test_integration.py")
        print("  2. Start app: uvicorn app.main:app --reload")
        sys.exit(0)
    elif all_ok and not env_ok:
        print("⚠️  Installation OK, but API key needed")
        print("\nSet CEREBRAS_API_KEY in .env file")
        sys.exit(1)
    else:
        print("❌ Installation incomplete")
        print("\nPlease fix the issues above")
        sys.exit(1)
