from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="text-adventure-tui",  # Changed to desired PyPI name
    version="0.1.1", # Incremented version
    author="The Black Cat Codes",
    author_email="author@example.com", # Please update this with your actual email
    description="A dynamic text adventure game for your terminal, powered by Ollama LLMs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Theblackcat98/Text-Adventure-TUI",
    packages=["text_adventure_tui_lib", "text_adventure_tui_lib.story_parts", "text_adventure_tui_lib.events"], # Define packages
    package_data={
        "text_adventure_tui_lib.story_parts": ["*.txt", "*.yaml"],
        "text_adventure_tui_lib.events": ["*.yaml"], # Include event YAML files
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Role-Playing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: Console", # Added for TUI
    ],
    python_requires=">=3.7",
    install_requires=[
        "ollama>=0.1.0,<0.3.0",
        "rich>=10.0.0,<14.0.0",
        "PyYAML>=5.0,<7.0", # Added PyYAML
    ],
    entry_points={
        "console_scripts": [
            "text-adventure-tui=text_adventure_tui_lib.game:game_loop", # Updated entry point
        ],
    },
    include_package_data=True, # Ensures MANIFEST.in is processed
    license="MIT",
    # data_files is removed as package_data handles it now with package structure
    project_urls={
        "Bug Tracker": "https://github.com/Theblackcat98/Text-Adventure-TUI/issues",
        "Source Code": "https://github.com/Theblackcat98/Text-Adventure-TUI",
    },
)
