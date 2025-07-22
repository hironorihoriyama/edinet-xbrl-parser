# setup.py

from setuptools import setup

setup(
    name="edinet_tool",
    version="0.1.0",
    # src 配下の単一モジュールとして main_edinet.py を登録
    py_modules=["main_edinet", "outputs", "outputs_xbrl"],
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv",
        "tqdm",
        "pandas",
        "openpyxl",
    ],
    entry_points={
        "console_scripts": [
            # edinet-main コマンドで main_edinet.py の run() を呼び出す
            "edinet-s = main_edinet:run",
            "edinet-g-c = outputs:main",
            "edinet-g-x = outputs_xbrl:main"
        ],
    },
)
