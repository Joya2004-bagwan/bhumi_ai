.PHONY: install dev stop

install:
	@if [ ! -d backend/venv ]; then \
		echo "Creating virtualenv..."; \
		cd backend && python3 -m venv venv; \
	else \
		echo "Virtualenv already exists, skipping creation."; \
	fi
	backend/venv/bin/pip install -r backend/requirements.txt -q
	cd frontend && npm install

dev:
	@echo "Starting BHUMI AI..."
	@source backend/venv/bin/activate && \
		uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload & \
		cd frontend && npm run dev & \
		wait

stop:
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:4000 | xargs kill -9 2>/dev/null || true
	@echo "Stopped."
