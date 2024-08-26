format:
	@isort . && black . && ruff .

setup:
	@python -m pip install .

