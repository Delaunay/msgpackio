#!/usr/bin/env python
from setuptools import setup


if __name__ == "__main__":
    setup(
        name="msgpackio",
        version="0.0.0",
        description="msgpack server for asyncio",
        author="Pierre Delaunay",
        packages=[
            "msgpackio",
        ],
        setup_requires=["setuptools"],
    )
