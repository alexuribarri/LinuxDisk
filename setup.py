from setuptools import setup, find_packages

setup(
    name="linuxdisk",
    version="1.0.0",
    description="CrystalDisk Unified Suite for Ubuntu and Linux Desktop",
    author="Alex Uribarri",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "linuxdisk = src.app:main",
        ],
    },
    install_requires=[],
    python_requires=">=3.8",
)
