from setuptools import setup, find_packages

setup(
    name="two_player_snake",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pygame>=2.5.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A two-player snake game built with Pygame",
    keywords="game, snake, pygame, multiplayer",
    python_requires=">=3.6",
) 