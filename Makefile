# 项目常用任务的薄封装。Windows 未安装 make 时，直接用注释里的 python 命令。
# 例如：python scripts/check_project.py

PY ?= python

.PHONY: help check baseline lint fmt env lock clean

help:
	@echo "check     仓库规范检查（stdlib，无需第三方包）"
	@echo "baseline  重建 .check_baseline.json（记录当前 ERROR）"
	@echo "lint      ruff 静态检查（notebook 用 nbqa）"
	@echo "fmt       ruff 格式化（含 notebook）"
	@echo "env       创建 .venv 并安装依赖（pip）"
	@echo "lock      用 uv 生成锁定文件 requirements.lock"
	@echo "clean     清理检查缓存与 notebook 检查点"

check:
	$(PY) scripts/check_project.py

baseline:
	$(PY) scripts/check_project.py --update-baseline

lint:
	$(PY) -m ruff check .
	$(PY) -m nbqa ruff notebooks

fmt:
	$(PY) -m ruff format .
	$(PY) -m nbqa ruff notebooks --fix

env:
	$(PY) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

lock:
	uv lock
	uv export --format requirements-txt --no-hashes -o requirements.lock

clean:
	$(PY) -c "import shutil,pathlib;[shutil.rmtree(p,ignore_errors=True) for p in pathlib.Path('.').rglob('.ipynb_checkpoints')]"
	$(PY) -c "import shutil;[shutil.rmtree(p,ignore_errors=True) for p in ('.ruff_cache','.pytest_cache')]"
