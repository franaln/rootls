try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='rootutils',
    version='0.1',
    description='',
    url='https://github.com/franaln/rootutils',
    author='Francisco Alonso',
    author_email='franaln@gmail.com',
    license='',
    packages=['rootutils',],
    scripts=['rootls', 'rootdiff', 'rootplot', 'plothists'],
    zip_safe=False,
)
