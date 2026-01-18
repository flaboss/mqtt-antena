IMAGE_NAME=mqtt-antena
DOCKER_USER=flvbssln
VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
PYTHON_VERSION_ARG=$(shell cat .python-version)

.PHONY: build lint format clean publish run venv destroy help

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: $(VENV)/bin/activate ## Create and sync the virtual environment

$(VENV)/bin/activate: requirements.txt
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

build: ## Build the Docker image
	docker build --build-arg PYTHON_VERSION=$(PYTHON_VERSION_ARG) -t $(IMAGE_NAME) .

run: build ## Start the application via Docker Compose
	docker-compose up -d

lint: venv ## Run code linting with Ruff
	$(VENV)/bin/ruff check src --fix

format: venv ## Format code with Ruff
	$(VENV)/bin/ruff format src

clean: ## Clean up caches
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache

publish: build ## Tag and push image to Docker Hub
	@if [ -z "$(TAG)" ]; then echo "Error: TAG is not set. Use 'make publish TAG=v1.0.0'"; exit 1; fi
	docker tag $(IMAGE_NAME) $(DOCKER_USER)/$(IMAGE_NAME):$(TAG)
	docker tag $(IMAGE_NAME) $(DOCKER_USER)/$(IMAGE_NAME):latest
	docker push $(DOCKER_USER)/$(IMAGE_NAME):$(TAG)
	docker push $(DOCKER_USER)/$(IMAGE_NAME):latest

destroy: ## Remove local containers and images
	docker-compose down --rmi local --volumes --remove-orphans
	docker rmi $(IMAGE_NAME) || true
