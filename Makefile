.PHONY: help godot extract test validate clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

godot: ## Open project in Godot editor
	godot project.godot

run: ## Run the game
	godot --path .

headless: ## Verify project loads (CI check)
	godot --headless --quit

test: headless ## Run all validation checks
	python3 tools/extraction/scripts/validate_assets.py

extract: ## Run full extraction pipeline (Windows VM)
	python3 tools/extraction/orchestrate.py --all

extract-test: ## Test SSH connection to Windows VM
	python3 tools/extraction/orchestrate.py --test-connection

validate: ## Validate extracted assets
	python3 tools/extraction/orchestrate.py --step validate

# ── AI Pipeline ──────────────────────────────────────────────────────

ai-setup: ## Install AI pipeline deps
	pip3 install -r tools/ai_pipeline/requirements.txt

ai-reconstruct: ## Run AI 3D reconstruction
	python3 tools/ai_pipeline/ai_orchestrate.py --all --skip-capture

ai-enhance: ## Run AI texture enhancement
	python3 tools/ai_pipeline/ai_orchestrate.py --stage enhance

ai-full: ## Full AI pipeline (capture + reconstruct + enhance)
	python3 tools/ai_pipeline/ai_orchestrate.py --all

ai-capture: ## Record reference gameplay
	python3 tools/ai_pipeline/scripts/capture_gameplay.py --mode manual

# ── Setup ────────────────────────────────────────────────────────────

setup: ## Install all Python deps
	pip3 install -r tools/extraction/requirements.txt
	pip3 install -r tools/ai_pipeline/requirements.txt

utool: ## Install UTM (macOS only)
	brew install --cask utm

clean: ## Remove temporary files
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true