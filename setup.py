from setuptools import find_packages, setup

setup(
    name="piano_roll",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pygame",
        "mido",
        "python-rtmidi",
        "colorama",
    ],
    entry_points={
        "console_scripts": [
            "piano_roll=piano_roll.main:main",
        ],
    },
)
