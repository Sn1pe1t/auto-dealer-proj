from setuptools import setup, find_packages

setup(
    name='autodealer-core',
    version='0.1.0',
    description='Core business logic for car dealership (orders, reports, top sales)',
    license='MIT',
    author='Sn1pe1t',
    author_email='enderman303040@gmail.com',
    url='https://github.com/Sn1pe1t/auto-dealer-proj',
    packages=find_packages(where='packages'),
    package_dir={'': 'packages'},
    install_requires=[],
    extras_require={
        'test': ['pytest', 'pytest-cov'],
    },
    python_requires='>=3.8',
)