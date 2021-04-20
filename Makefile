PYTHON       = 	PYTHONPATH=dags:${PYTHONPATH} /usr/bin/env python3
VERSION_FILE = ./dags/_version.py
VERSION      = $(shell cut -d " " -f 3 ${VERSION_FILE})
DOCKER_REPO  = docker.io
DOCKER_OWNER = helxplatform
DOCKER_APP	 = roger
DOCKER_TAG   = ${VERSION}
DOCKER_IMAGE = ${DOCKER_OWNER}/${DOCKER_APP}:$(DOCKER_TAG)

.DEFAULT_GOAL = help

.PHONY: help clean install test build image publish

help:
	@grep -E '^#[a-zA-Z\.\-]+:.*$$' $(MAKEFILE_LIST) | tr -d '#' | awk 'BEGIN {FS = ": "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

mk_dirs:
	mkdir -p {logs,plugins}
	mkdir -p local_storage/elastic

rm_dirs:
	rm -rf logs/*
	rm -rf local_storage/elastic/*
	rm -rf ./dags/roger/data/*

#install: Install application along with required packages to local environment
install: mk_dirs
	${PYTHON} -m pip install --upgrade pip
	${PYTHON} -m pip install -r requirements.txt

	docker-compose up airflow-init

#test.lint: Run flake8 on the source code
test.lint:
	${PYTHON} -m flake8 dags

#test.doc: Run doctests in the source code
test.doc:
	echo "Running doc tests..."
	${PYTHON} -m pytest --doctest-modules dags

#test.unit: Run unit tests
test.unit:
	echo "Running unit tests..."
	${PYTHON} -m pytest tests/unit

#test.integration: Run unit tests
test.integration:
	echo "Running integration tests..."
	${PYTHON} -m pytest tests/integration

#test: Run all tests
test: test.doc test.unit

#build: Build the Docker image
build:
	echo "Building docker image: ${DOCKER_IMAGE}"
	docker build -t ${DOCKER_IMAGE} -f Dockerfile .
	echo "Successfully built: ${DOCKER_IMAGE}"

#publish: Push the Docker image
publish:
	docker tag ${DOCKER_IMAGE} ${DOCKER_REPO}/${DOCKER_IMAGE}
	docker push ${DOCKER_REPO}/${DOCKER_IMAGE}

#clean: Remove old data
clean: rm_dirs mk_dirs

#stack: Bring up Airflow and all backend services
stack:
	docker-compose up
