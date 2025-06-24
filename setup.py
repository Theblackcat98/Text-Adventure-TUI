from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="terminal-text-adventure",
    version="0.1.0",
    author="Jules Agent",
    author_email="agent@example.com",
    description="A dynamic text adventure game played in the terminal, powered by Ollama LLMs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/user/terminal-text-adventure-project", # Generic project URL
    py_modules=["game"], # Specify 'game' as a top-level module
    # packages=find_packages(exclude=["tests*", "docs*"]), # Not ideal for a single script
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Interactive Fiction",
        "License :: OSI Approved :: MIT License", # Choose your license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "ollama>=0.1.0", # Specify a version range if known, e.g., ollama>=0.1.0,<0.2.0
        "rich>=10.0.0",   # Specify a version range, e.g., rich>=10.0.0,<14.0.0
    ],
    entry_points={
        "console_scripts": [
            "terminal-adventure=game:game_loop",
        ],
    },
    include_package_data=True, # To include non-code files specified in MANIFEST.in
    package_data={
        # If you have data files inside your package (e.g., story_parts if it were inside a package)
        # For example, if 'game' was a package 'mygamepkg' and story_parts was in it:
        # "mygamepkg": ["story_parts/*.txt"],
        # Since story_parts is top-level and used via relative path from game.py,
        # it's handled differently if game.py is treated as a script.
        # For PyPI, we might need to adjust how story_parts is located or packaged.
        # For now, assuming game.py can find story_parts if run from the project root.
        # If 'game.py' is part of a package, 'story_parts' path needs careful handling.
    },
    project_urls={ # Optional
        "Bug Tracker": "https://github.com/your_username/terminal-text-adventure/issues",
        "Source Code": "https://github.com/your_username/terminal-text-adventure",
        # "Documentation": "link_to_your_docs_if_hosted_separately",
    },
)
