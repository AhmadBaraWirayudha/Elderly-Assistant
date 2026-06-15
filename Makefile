# ElderAI — convenience commands
# Usage: make <target>

.PHONY: run test clean rebuild lint

## Start the app
run:
	streamlit run app.py

## Run the test suite (no API key needed)
test:
	python -m pytest tests/ -v --tb=short

## Run tests with coverage report
test-cov:
	python -m pytest tests/ -v --tb=short --cov=. --cov-report=term-missing \
	  --ignore=tests/ --ignore=app.py

## Remove generated files (FAISS index, SQLite DB, pycache)
clean:
	rm -rf kb_index/ chat_history.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

## Force-rebuild the FAISS knowledge index and restart
rebuild: clean
	streamlit run app.py

## Quick syntax check without running tests
lint:
	python -m py_compile app.py config.py router.py \
	  rag/chain.py audio/stt.py audio/tts.py \
	  utils/state.py utils/auth.py utils/errors.py \
	  utils/health.py utils/history.py utils/logger.py utils/validator.py \
	  && echo "✅  All files compile cleanly"

## Install all dependencies
install:
	pip install -r requirements.txt
