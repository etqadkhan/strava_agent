.PHONY: help install dev-install format lint test clean run sync

# Default target
help:
	@echo "🏃‍♂️ Strava Agent - Development Commands"
	@echo "========================================"
	@echo ""
	@echo "📦 Package Management:"
	@echo "  install      - Install production dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  sync         - Sync dependencies with lock file"
	@echo ""
	@echo "🛠️  Development:"
	@echo "  format       - Format code with Black"
	@echo "  lint         - Run linting with Flake8"
	@echo "  test         - Run tests with pytest"
	@echo "  clean        - Clean up generated files"
	@echo ""
	@echo "🚀 Running:"
	@echo "  run          - Run the bot"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  help         - Show this help message"

# Install production dependencies
install:
	@echo "📦 Installing production dependencies..."
	uv sync --no-dev

# Install development dependencies
dev-install:
	@echo "🛠️  Installing development dependencies..."
	uv sync

# Sync dependencies with lock file
sync:
	@echo "🔄 Syncing dependencies..."
	uv sync

# Format code with Black
format:
	@echo "🎨 Formatting code with Black..."
	uv run black .

# Run linting with Flake8
lint:
	@echo "🔍 Running linting with Flake8..."
	uv run flake8 .

# Run tests
test:
	@echo "🧪 Running tests..."
	uv run pytest

# Clean up generated files
clean:
	@echo "🧹 Cleaning up generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name "*.png" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

# Run the bot
run:
	@echo "🚀 Starting Strava Agent..."
	uv run python main.py

# Check code quality
check: format lint
	@echo "✅ Code quality checks completed!"

# Full development setup
setup: dev-install format
	@echo "🎉 Development environment setup complete!"
