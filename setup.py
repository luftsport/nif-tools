import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nif-tools",
    version="0.12.1",
    author="Einar Huseby",
    author_email="einar.huseby@gmail.com",
    description="Tools to programmatically interact with NIF's Min Idrett, Klubbadmin and Sportsadmin",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/luftsport/nif-tools",
    packages=setuptools.find_packages(),
    install_requires=['requests', 'python-dateutil', 'bs4'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
