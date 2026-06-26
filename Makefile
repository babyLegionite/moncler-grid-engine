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

extract: ## Run full extraction pipeline
	python3 tools/extraction/orchestrate.py --all

extract-test: ## Test SSH connection to Windows VM
	python3 tools/extraction/orchestrate.py --test-connection

validate: ## Validate extracted assets
	python3 tools/extraction/orchestrate.py --step validate

setup: ## Install Python deps for extraction
	pip3 install -r tools/extraction/requirements.txt

utool: ## Install UTM (macOS only)
	brew install --cask utm

clean: ## Remove temporary files
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true