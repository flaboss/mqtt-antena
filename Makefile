IMAGE_NAME=mqtt-antena
DOCKER_USER=flvbssln
VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
PYTHON_VERSION_ARG=$(shell cat .python-version)

.PHONY: build lint format clean publish run venv destroy


venv: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

build:
	docker build --build-arg PYTHON_VERSION=$(PYTHON_VERSION_ARG) -t $(IMAGE_NAME) .

run: build
	docker-compose up -d

lint: venv
	$(VENV)/bin/ruff check src

format: venv
	$(VENV)/bin/ruff format src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache

publish: build
	@if [ -z "$(TAG)" ]; then echo "Error: TAG is not set. Use 'make publish TAG=v1.0.0'"; exit 1; fi
	docker tag $(IMAGE_NAME) $(DOCKER_USER)/$(IMAGE_NAME):$(TAG)
	docker tag $(IMAGE_NAME) $(DOCKER_USER)/$(IMAGE_NAME):latest
	docker push $(DOCKER_USER)/$(IMAGE_NAME):$(TAG)
	docker push $(DOCKER_USER)/$(IMAGE_NAME):latest

destroy:
	docker-compose down --rmi local --volumes --remove-orphans
	docker rmi $(IMAGE_NAME) || true
