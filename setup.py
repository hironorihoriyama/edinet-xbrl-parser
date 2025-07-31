# setup.py

from setuptools import setup

setup(
    name="edinet_tool",
    version="0.1.0",
    py_modules=["save_xbrl", "generate_fs", "edinet_tools"],
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv",
        "tqdm",
        "pandas",
        "openpyxl",
    ],
    entry_points={
        "console_scripts": [
            "save = save_xbrl:run",
            "generate = generate_fs:main"
        ],
    },
)
